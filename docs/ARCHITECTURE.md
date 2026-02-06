# Parallel GC Architecture

**Audience:** CPython core developers reviewing this work for potential merge.
Assumes familiarity with CPython's GC internals (`gc.c`, `gc_free_threading.c`,
`PyGC_Head`, `ob_gc_bits`, mimalloc page layout) but not this project's design.

For build instructions see [GETTING_STARTED.md](GETTING_STARTED.md).
For design rationale and heritage see [DESIGN_POST.md](DESIGN_POST.md).

---

## 1. Overview

CPython's garbage collector uses a generational, stop-the-world mark-sweep
algorithm. On heaps with millions of objects, the mark phase dominates pause
time. This project parallelises the mark phase (and supporting phases) across
multiple worker threads to reduce those pauses.

There are two independent implementations, selected at compile time:

| Build | Guard macro | Source files | GC it extends |
|-------|-------------|--------------|---------------|
| GIL (`./configure --with-parallel-gc`) | `Py_PARALLEL_GC` | `gc_parallel.c`, `pycore_gc_parallel.h` | `Python/gc.c` |
| Free-threaded (`--with-parallel-gc --disable-gil`) | `Py_GIL_DISABLED && Py_PARALLEL_GC` | `gc_free_threading_parallel.c`, `pycore_gc_ft_parallel.h` | `Python/gc_free_threading.c` |

Both implementations share the Chase-Lev work-stealing deque
(`pycore_ws_deque.h`), barrier synchronisation (`pycore_gc_barrier.h`), and
local work buffer.

**Important:** The two implementations are mutually exclusive. GIL builds guard
on `Py_PARALLEL_GC` alone; free-threaded builds guard on both `Py_GIL_DISABLED`
and `Py_PARALLEL_GC`.

Parallel GC is **opt-in at build time** via `--with-parallel-gc` and **opt-in
at runtime** via `gc.enable_parallel(N)`. Without the configure flag, the
parallel GC code is not compiled. The parallel GC does not change *what* is
collected -- only *how fast* the mark phase runs.

```
                    gc.collect()
                        |
            +-----------+-----------+
            |                       |
     GIL Build (gc.c)      FTP Build (gc_free_threading.c)
            |                       |
     gc_parallel.c          gc_free_threading_parallel.c
            |                       |
     +------+------+        +------+------+
     | Shared infra |        | Shared infra |
     | ws_deque.h   |        | ws_deque.h   |
     | barrier.h    |        | barrier.h    |
     +--------------+        +--------------+
```

---

## 2. GIL Build Architecture

**Source:** `Python/gc_parallel.c`, `Include/internal/pycore_gc_parallel.h`
**Guard:** `#ifdef Py_PARALLEL_GC` (defined when `--with-parallel-gc` is passed to configure)
**Requirement:** 64-bit platform (`SIZEOF_VOID_P >= 8`) -- enforced at
compile time (`pycore_gc_parallel.h:37`).

### 2.1 Integration with gc.c

The parallel collector hooks into `deduce_unreachable()` in `Python/gc.c` at
three call sites. The serial `update_refs` is replaced by
`update_refs_with_splits()`, and three parallel entry points are called in
sequence. If any returns 0, `deduce_unreachable()` falls through to the serial
code path.

```
deduce_unreachable()                         [gc.c:~1540]
  |
  +-- update_refs_with_splits()              [gc.c:541]
  |     Serial. Walks the GC list, sets gc_refs = Py_REFCNT,
  |     and records split-vector waypoints every 8192 objects.
  |
  +-- _PyGC_ParallelMarkAliveFromQueue()     [gc_parallel.c:2192]
  |     Parallel. Pre-marks interpreter roots (sysdict, builtins,
  |     thread stacks, type dicts). Pipelined producer-consumer.
  |
  +-- _PyGC_ParallelSubtractRefs()           [gc_parallel.c:1792]
  |     Parallel. Decrements gc_refs via tp_traverse with
  |     atomic decref visitor. Split-vector work distribution.
  |
  +-- _PyGC_ParallelMoveUnreachable()        [gc_parallel.c:1489]
        Parallel mark + serial sweep.
        Workers scan segments for roots (gc_refs > 0),
        mark subgraphs. Main thread sweeps: COLLECTING=1 -> unreachable.
```

**Fallback:** At `gc.c:1683`:

```c
if (!_PyGC_ParallelMoveUnreachable(interp, base, unreachable)) {
    move_unreachable(base, unreachable);  // Serial fallback
}
```

### 2.2 Object Layout

GC-tracked objects have a `PyGC_Head` prefix with `_gc_next` and `_gc_prev`.
The `_gc_prev` field stores both the previous-list pointer and GC metadata:

```
_gc_prev layout (uintptr_t):
  [63:2]  gc_refs count (shifted by _PyGC_PREV_SHIFT=2)
  [1]     COLLECTING flag (_PyGC_PREV_MASK_COLLECTING=2)
  [0]     FINALIZED flag (_PyGC_PREV_MASK_FINALIZED=1)
```

During parallel marking, the COLLECTING flag is the marking bit:
- `COLLECTING = 1` -- object not yet proven reachable
- `COLLECTING = 0` -- object marked reachable by a worker

### 2.3 The Four Phases

```
  +-----------+     +----------------+     +-----------+     +-------+
  | mark_alive| --> | subtract_refs  | --> |   mark    | --> | sweep |
  | (parallel)|     |   (parallel)   |     | (parallel)|     |(serial)|
  +-----------+     +----------------+     +-----------+     +-------+
   Pipelined         Split-vector           Split-vector      Main thread
   producer-         segments               segments          walks list,
   consumer                                                   moves COLLECTING
                                                              objects to
                                                              unreachable
```

#### update_refs (Serial, with split recording)

**Entry:** `update_refs_with_splits()` (`gc.c:541`)

Walks the GC list and sets `gc_refs = ob_refcnt` for every object.
Simultaneously records **split points** -- pointers into the GC list at
`_PyGC_SPLIT_INTERVAL` (8192) object intervals -- into a growable
`_PyGCSplitVector` (`pycore_gc_parallel.h:117`):

```c
// gc.c:572
if (candidates % _PyGC_SPLIT_INTERVAL == 0 && next != containers) {
    _PyGCSplitVector_Push(splits, next);
}
```

The split vector enables O(1) parallel partitioning without an extra list
traversal. A sentinel entry (the list head) is pushed at the end as an
exclusive end marker.

#### Phase 1: mark_alive -- Interpreter Root Pre-Marking

**Entry:** `_PyGC_ParallelMarkAliveFromQueue()` (`gc_parallel.c:2192`)

**Purpose:** Pre-mark objects reachable from interpreter roots before the
subtract_refs/mark cycle. Objects marked here are skipped by subsequent
phases, substantially reducing parallel work.

**Distribution: Pipelined producer-consumer.**

The main thread calls `gc_expand_roots_to_queue()` which traverses each
interpreter root by one level via `tp_traverse`, pushing level-1 children to
a shared `_PyGCWorkQueue` (`pycore_gc_parallel.h:161`). Workers claim batches
of `_PyGC_QUEUE_BATCH_SIZE` (64) objects using atomic CAS on the queue's
`read_index` and traverse subtrees locally.

```
  Main thread (producer)               Workers (consumers)
  +--------------------------+         +------------------------+
  | For each interp root:    |         | loop:                  |
  |   mark root reachable    |         |   batch = ClaimBatch() |
  |   tp_traverse(root) -->  |-------->|   for obj in batch:    |
  |     push children to     |         |     tp_traverse(obj)   |
  |     work queue           |         |     push children to   |
  +--------------------------+         |     local buffer/deque  |
  | ProducerDone()           |         |   drain local buffer   |
  +--------------------------+         +------------------------+
```

**Why not simple work-stealing?** Interpreter roots form a hub: ~100 roots
reference most of the heap. With naive work-stealing, the first worker to
process the hub marks most objects before others can steal (99% imbalance
measured empirically). Level-1 expansion produces thousands of distributed
starting points.

The queue is block-based (`_PyGCQueueBlock`, 4096 pointers per block), with
`_PyGC_QUEUE_INITIAL_BLOCKS` (8) pre-allocated blocks for zero-allocation
operation. `write_index` and `read_index` are cache-line padded:

```c
// pycore_gc_parallel.h:169
Py_ssize_t write_index;
char _pad1[64 - sizeof(Py_ssize_t)];
Py_ssize_t read_index;
char _pad2[64 - sizeof(Py_ssize_t)];
```

Workers consume in the `_PyGC_PHASE_MARK_ALIVE_QUEUE` dispatch case
(`gc_parallel.c:272`).

**Alternative:** `_PyGC_ParallelMarkAliveFromRoots` (`gc_parallel.c:2130`)
distributes roots round-robin with coordinator-based termination, but is not
used by default due to the hub imbalance.

#### Phase 2: subtract_refs -- Parallel Reference Count Decrement

**Entry:** `_PyGC_ParallelSubtractRefs()` (`gc_parallel.c:1792`)

**Purpose:** Call `tp_traverse` with a visitor that atomically decrements
`gc_refs` of referenced objects. After this phase, objects with `gc_refs > 0`
are roots.

**Distribution: Split vector segments.** Workers get contiguous ranges:

```c
// gc_parallel.c:1819
size_t entries_per_worker = splits->count / par_gc->num_workers;
par_gc->workers[i].slice_start = splits->entries[start_idx];
par_gc->workers[i].slice_end   = splits->entries[end_idx];
par_gc->workers[i].phase = _PyGC_PHASE_SUBTRACT_REFS;
```

**Atomic decrement** -- references cross segment boundaries:

```c
// gc_parallel.c:1695
static inline void
gc_decref_atomic(PyGC_Head *gc)
{
    _Py_atomic_add_uintptr(&gc->_gc_prev,
                           -((uintptr_t)1 << _PyGC_PREV_SHIFT));
}
```

The visitor (`visit_decref_atomic`, `gc_parallel.c:1703`) checks COLLECTING
with a relaxed load -- objects marked alive in Phase 1 are skipped.

#### Phase 3: mark -- Parallel Root Discovery and Local Marking

**Entry:** `_PyGC_ParallelMoveUnreachable()` (`gc_parallel.c:1489`)

Same split-vector segments. Workers scan for roots (`gc_refs > 0`), mark
them, traverse subgraphs **locally** -- no work-stealing. Safe because
Phase 1 already marked most reachable objects.

Worker dispatch (`gc_parallel.c:327`):

```c
// Scan segment for roots
while (gc != end) {
    if (!gc_is_collecting(gc)) { gc = next; continue; }
    if (gc_get_refs(gc) > 0) {
        gc->_gc_prev &= ~_PyGC_PREV_MASK_COLLECTING;
        _PyGCLocalBuffer_Push(&worker->local_buffer, _Py_FROM_GC(gc));
    }
    gc = next;
}
// Drain local buffer and own deque until both empty
```

#### Phase 4: sweep -- Serial

Main thread sweeps the GC list (`gc_parallel.c:1606`). Objects with
COLLECTING still set are moved to unreachable; reachable objects have
`_gc_prev` restored.

### 2.4 Atomic Marking via Fetch-And

```c
// gc_parallel.c:76
static inline int
gc_try_mark_reachable_atomic(PyGC_Head *gc)
{
    // Fast path: relaxed load (~1 cycle, ~10x cheaper than RMW)
    uintptr_t prev = _Py_atomic_load_uintptr_relaxed(&gc->_gc_prev);
    if (!(prev & _PyGC_PREV_MASK_COLLECTING)) {
        return 0;
    }
    // Slow path: fetch-and always succeeds (no retry loop)
    uintptr_t old_prev = _Py_atomic_and_uintptr(
        &gc->_gc_prev, ~_PyGC_PREV_MASK_COLLECTING);
    int marked = (old_prev & _PyGC_PREV_MASK_COLLECTING) != 0;
    if (marked) {
        _Py_atomic_fence_acquire();  // ARM: consistent fields
    }
    return marked;
}
```

**Why Fetch-And over CAS:** Always succeeds in one instruction; old value
gives ownership; monotonic bit (no ABA); check-first relaxed load handles
shared objects cheaply.

### 2.5 Worker Thread Lifecycle

```
gc.enable_parallel(N)
  |
  _PyGC_ParallelInit()   [gc_parallel.c:405]
  _PyGC_ParallelStart()  [gc_parallel.c:576]
  |
  [... GC collections ...]
  |
gc.disable_parallel()
  |
  _PyGC_ParallelStop()   [gc_parallel.c:623]
```

Workers are persistent, sleeping on `mark_barrier`. Each has:
- `_PyWSDeque` with 2 MB pre-allocated buffer
- `_PyGCLocalBuffer` (1024 items, zero fences)
- `PyThreadState` (for `Py_REF_DEBUG`)
- Per-worker statistics and timing

**Thread state cleanup:** Done by **main thread** after join
(`gc_parallel.c:655`) -- clears `bound_gilstate` before `PyThreadState_Delete`
to avoid assertion failure (`gc_parallel.c:661`).

### 2.6 Serial Fallback Conditions

Falls back to serial when: parallel GC not enabled, split vector < 2 entries,
or workers not active. All entry points return 0 to trigger fallback.

---

## 3. Free-Threaded Build Architecture

**Source:** `Python/gc_free_threading_parallel.c`,
`Include/internal/pycore_gc_ft_parallel.h`
**Guard:** `#ifdef Py_GIL_DISABLED`

### 3.1 Integration with gc_free_threading.c

```
gc_mark_alive_from_roots()                   [gc_free_threading.c:1524]
  +-- _PyGC_ParallelPropagateAliveWithPool() [gc_free_threading_parallel.c:1936]

deduce_unreachable_heap()                    [gc_free_threading.c:1588]
  +-- _PyGC_AssignPagesToBuckets()           [gc_free_threading_parallel.c:391]
  +-- _PyGC_ParallelUpdateRefsWithPool()
  +-- _PyGC_ParallelMarkHeapWithPool()
  +-- _PyGC_ParallelScanHeapWithPool()
```

### 3.2 Object Layout

- `ob_gc_bits` -- `uint8_t` with flag bits (ALIVE=0x20 i.e. 1<<5, UNREACHABLE=0x04 i.e. 1<<2)
- `ob_tid` -- repurposed during STW to store `gc_refs`

### 3.3 Architectural Differences from GIL Build

| Aspect | GIL Build | FTP Build |
|--------|-----------|-----------|
| Marking bit | `_gc_prev` COLLECTING flag | `ob_gc_bits` ALIVE/UNREACHABLE |
| gc_refs storage | Upper bits of `_gc_prev` | `ob_tid` (repurposed during STW) |
| Marking op | Fetch-And on `uintptr_t` | Relaxed load/store on `uint8_t` |
| Work distribution | Split vector (GC list) | Page-based (mimalloc buckets) |
| Phases parallelised | mark_alive, subtract_refs, mark | update_refs, mark_alive, mark_heap, scan_heap |

### 3.4 Page-Based Work Distribution

```
  Thread 0 heaps            Thread 1 heaps          Abandoned pool
  +--+--+--+--+--+         +--+--+--+--+           +--+--+--+
  |p0|p1|p2|p3|p4|         |p5|p6|p7|p8|           |p9|pA|pB|
  +--+--+--+--+--+         +--+--+--+--+           +--+--+--+
         |                        |                       |
         v                        v                       v
  +--------------+  +--------------+  +--------------+  +--------------+
  | Bucket 0     |  | Bucket 1     |  | Bucket 2     |  | Bucket 3     |
  +--------------+  +--------------+  +--------------+  +--------------+
```

**Normal pages:** Sequential filling preserving locality.
**Huge pages:** Round-robin to spread expensive traversals.
**Abandoned pool pages:** Included via `_mi_abandoned_pool_enumerate_pages()`.

Page counting: O(threads) via `heap->page_count`.
Page enumeration: O(pages) through mimalloc bin queues.

### 3.5 Relaxed-Atomic Marking on ob_gc_bits

```c
// pycore_gc_ft_parallel.h:174
static inline int
_PyGC_TryMarkAlive(PyObject *op)
{
    if (_Py_atomic_load_uint8_relaxed(&op->ob_gc_bits) & _PyGC_BITS_ALIVE) {
        return 0;
    }
    uint8_t new_bits = (op->ob_gc_bits | _PyGC_BITS_ALIVE)
                     & ~_PyGC_BITS_UNREACHABLE;
    _Py_atomic_store_uint8_relaxed(&op->ob_gc_bits, new_bits);
    _Py_atomic_fence_acquire();
    return 1;
}
```

If two workers race: both write ALIVE (idempotent), both traverse referents,
duplicate traversal stops at next level. Eliminates ~20-40 cycles per object
vs atomic RMW.

For MARK_HEAP, `_PyGC_TryMarkReachable()` (`pycore_gc_ft_parallel.h:215`)
uses Fetch-And on UNREACHABLE bit for strict ownership.

### 3.6 The Three Phases of deduce_unreachable_heap

#### UPDATE_REFS (2-phase with barrier)

```
Phase 1: init_refs              Phase 2: compute_refs
+---------------------+        +---------------------+
| Set UNREACHABLE     | barrier| Add Py_REFCNT to    |
| Zero ob_tid         |------->| ob_tid (gc_refs)    |
| Count candidates    |        | tp_traverse +decref |
+---------------------+        +---------------------+
```

Atomic gc_refs ops (`pycore_gc_ft_parallel.h:448`):

```c
static inline void gc_decref_atomic(PyObject *op) {
    _Py_atomic_add_uintptr(&op->ob_tid, (uintptr_t)-1);
}
```

#### MARK_HEAP (roots + transitive marking)

Workers scan pages for roots, work-stealing loop with `MAX_IDLE_ROUNDS = 3`.

#### SCAN_HEAP (collect unreachable)

Dynamic page distribution via atomic counter:

```c
// gc_free_threading_parallel.c:1584
int page_idx = atomic_fetch_add(&work->page_counter, 1);
```

Thread-local worklists merged after barrier.

### 3.7 Thread Pool (_PyGCThreadPool)

```
  _PyGCThreadPool
  +-------------------------------------------+
  | mark_barrier     Workers wait for work     |
  | done_barrier     All wait when done        |
  | phase_barrier    Multi-phase sync          |
  | workers[0..N-1]  deque, local, pool, tstate|
  | current_work     type + parameters         |
  +-------------------------------------------+
```

Worker 0 = main thread. Dispatch via `thread_pool_do_work`
(`gc_free_threading_parallel.c:1596`).

---

## 4. Shared Infrastructure

### 4.1 Chase-Lev Work-Stealing Deque

**File:** `Include/internal/pycore_ws_deque.h`

Based on Chase & Lev 2005 and Le et al. 2013.

```
  _PyWSDeque
  +--------------------------------------------------+
  | top (cache-line padded) -- steal end              |
  | bot (cache-line padded) -- owner end              |
  | arr -> _PyWSArray (circular buffer, power-of-2)   |
  +--------------------------------------------------+
```

- Push/Take: owner, lock-free, LIFO for cache locality
- Steal: any worker, lock-free CAS, FIFO for fairness
- top/bot initialised to 1 (bug fix from paper, `ws_deque.h:206`)
- Pre-allocated 2MB buffers via `_PyWSDeque_InitWithBuffer()` (`ws_deque.h:217`)
- `_PyWSDeque_FiniExternal(deque, buffer)` for buffer-backed cleanup
- OOM: `Py_FatalError` at Init (`ws_deque.h:194`) and Push/Grow (`ws_deque.h:329`)

### 4.2 Barrier Synchronisation

**File:** `Include/internal/pycore_gc_barrier.h`

```c
// pycore_gc_barrier.h:64
typedef struct {
    unsigned int num_left;
    unsigned int capacity;
    unsigned int epoch;       // Prevents spurious wakeup bugs
    PyMUTEX_T lock;
    PyCOND_T cond;
} _PyGCBarrier;
```

Portable: POSIX pthread or Windows SRWLOCK/CONDITION_VARIABLE.

### 4.3 Local Work Buffers

**Defined in:** `pycore_ws_deque.h:420`

```
  tp_traverse --> LocalBuffer (1024, zero fences)
                     | overflow: half-flush to deque
                     | refill: batch-pull from deque
                     | steal: batch-steal from victim
```

- `_PyGC_OverflowFlush` (`ws_deque.h:532`): half-flush, 38% faster than full
- `_PyGC_RefillLocalFromDeque` (`ws_deque.h:476`): up to 512 items
- `_PyGC_BatchSteal` (`ws_deque.h:496`): up to 512, lazy size check first

### 4.4 Coordinator-Based Termination (GIL build)

For mark_alive work-stealing (`pycore_gc_parallel.h:327`):
1. Worker exhausts work, tries to become coordinator (mutex election)
2. Coordinator polls all deques, wakes idle workers via `_PyGCSemaphore`
3. Termination: coordinator is last active + all deques empty

FTP uses simpler `idle_rounds` counter (`MAX_IDLE_ROUNDS = 3`).

---

## 5. Python API

All in `Modules/gcmodule.c`.

### gc.enable_parallel(num_workers)

- **GIL** (`gcmodule.c:549`): `_PyGC_ParallelInit()` + `_PyGC_ParallelStart()`
- **FTP** (`gcmodule.c:513`): `_PyGC_ThreadPoolInit()`
- num_workers >= 2 required

### gc.disable_parallel()

- **GIL** (`gcmodule.c:634`): `_PyGC_ParallelStop()` + disable
- **FTP** (`gcmodule.c:621`): `_PyGC_ThreadPoolFini()`

### gc.get_parallel_config()

Returns `{'available': bool, 'enabled': bool, 'num_workers': int}`.
FTP adds `'parallel_cleanup': True`.

### gc.get_parallel_stats()

Returns per-worker stats and phase timing (ns). Phase timing includes
abstract names (`scan_mark_ns`, `stw_pause_ns`) for cross-build comparison.

GIL build example:

```python
{
    'enabled': True, 'num_workers': 8,
    'roots_found': 142, 'roots_distributed': 3847,
    'gc_roots_found': 3,
    'collections_attempted': 15, 'collections_succeeded': 15,
    'workers': [{'objects_marked': 131072, 'steal_attempts': 42, ...}, ...],
    'phase_timing': {
        'update_refs_ns': ..., 'mark_alive_ns': ...,
        'subtract_refs_ns': ..., 'mark_ns': ...,
        'scan_mark_ns': ..., 'stw_pause_ns': ...,
    }
}
```

---

## 6. Key Design Decisions

### Why Fetch-And over CAS?

Monotonic bit (1->0 only). Fetch-And always succeeds in one instruction.
Old value gives ownership. No ABA. Check-first relaxed load handles shared
objects cheaply. See Section 2.4.

### Why persistent thread pool?

Thread create/join: ~100us/collection. Barrier signal: ~1-5us. 2MB pools
allocated once and reused.

### Why the split vector?

GC list has no random access. Split vector piggybacks on `update_refs`
(zero extra traversals, zero atomics for partitioning). 8K resolution for
fine-grained balancing.

### Why pipelined producer-consumer for mark_alive?

~100 interpreter roots form a hub. Naive work-stealing: 99% imbalance.
Level-1 expansion creates thousands of starting points.

### Why relaxed atomics in FTP TryMarkAlive?

During STW, all threads cooperate. Duplicate marking is idempotent.
Saves ~20-40 cycles/object vs atomic RMW. See Section 3.5.

### Why Py_FatalError for deque OOM?

Dropping objects = missed marks = use-after-free. Error propagation would
require 12+ call site changes. Consistent with CPython practice.

---

## 7. File Map

### Implementation Files

| File | Description |
|------|-------------|
| `Python/gc_parallel.c` | GIL build: all 4 phases, worker thread, split vector, work queue, semaphore, coordinator, stats |
| `Python/gc_free_threading_parallel.c` | FTP build: page enumeration/assignment, update_refs/mark_heap/scan_heap, thread pool, propagate, test APIs |
| `Python/gc.c` | GIL base GC: `update_refs_with_splits()` (line 541), parallel calls in `deduce_unreachable()` (lines 1543-1697) |
| `Python/gc_free_threading.c` | FTP base GC: parallel calls in `gc_mark_alive_from_roots()` (line 1524), `deduce_unreachable_heap()` (line 1588) |
| `Modules/gcmodule.c` | Python API: `enable_parallel()` (510), `disable_parallel()` (618), `get_parallel_config()` (681), `get_parallel_stats()` (772) |

### Header Files

| File | Description |
|------|-------------|
| `Include/internal/pycore_gc_parallel.h` | GIL: worker/global state, split vector, work queue, semaphore, CPU/prefetch primitives, phase enum, API |
| `Include/internal/pycore_gc_ft_parallel.h` | FTP: atomic bit ops, thread pool, work descriptor, worker state, page buckets, gc_refs ops, scan structs |
| `Include/internal/pycore_ws_deque.h` | Chase-Lev deque, local buffer, shared batch operations |
| `Include/internal/pycore_gc_barrier.h` | Barrier with epoch protection, portable mutex/condvar macros |

### Documentation

| File | Description |
|------|-------------|
| `docs/ARCHITECTURE.md` | This file |
| `docs/DESIGN_POST.md` | Design rationale, CinderX heritage, optimisations |
| `docs/GETTING_STARTED.md` | Reviewer quick start: build, test, evaluate |
| `docs/PEP_OUTLINE.md` | PEP draft outline |

---

## 8. Invariants

1. **Every reachable object is marked.** Atomic marking + deque/buffer drain +
   termination detection guarantee no missed marks.

2. **Marking is monotonic.** COLLECTING/UNREACHABLE bits only transition in one
   direction during a collection. No re-set after clear.

3. **Serial equivalence.** Parallel GC collects exactly the same objects as
   serial. Finalizers/weakrefs run in serial cleanup phase.

4. **Worker isolation.** No shared mutable state beyond marking bits and deque
   indices. Each worker has independent buffer, stats, deque storage, tstate.

5. **Barrier completeness.** All workers arrive before any proceed. Epoch-based
   barrier prevents spurious passage.

---

## Appendix A: Full Collection Flow (GIL Build)

```
gc.collect()
  |
  deduce_unreachable(base, unreachable)                      [gc.c]
  |
  |  (1) update_refs_with_splits(base, split_vector)         [gc.c:541]
  |       Serial: gc_refs = Py_REFCNT(op), record waypoints
  |
  |  (2) _PyGC_ParallelMarkAliveFromQueue(interp, base)      [gc_parallel.c:2192]
  |       Producer-consumer: expand roots -> queue -> workers
  |       Atomic: Fetch-And on _gc_prev COLLECTING bit
  |
  |  (3) _PyGC_ParallelSubtractRefs(interp, base)            [gc_parallel.c:1792]
  |       Workers: tp_traverse + atomic decref on gc_refs
  |
  |  (4) _PyGC_ParallelMoveUnreachable(interp, base, unr)    [gc_parallel.c:1489]
  |       Workers: find gc_refs>0 roots, mark locally
  |       Main: serial sweep, move COLLECTING to unreachable
  |
  finalize_garbage(unreachable)                              [gc.c]
```

## Appendix B: Full Collection Flow (FTP Build)

```
gc_collect_internal()
  |
  gc_mark_alive_from_roots(interp, state)                    [gc_free_threading.c]
  |  _PyGC_ParallelPropagateAliveWithPool()
  |  Relaxed atomic marking on ob_gc_bits
  |
  deduce_unreachable_heap(interp, state)                     [gc_free_threading.c]
  |
  |  (1) _PyGC_AssignPagesToBuckets()      Page distribution
  |  (2) _PyGC_ParallelUpdateRefsWithPool() init+barrier+compute
  |  (3) _PyGC_ParallelMarkHeapWithPool()   roots + work-stealing
  |  (4) _PyGC_ParallelScanHeapWithPool()   atomic counter distribution
  |
  handle_weakrefs / delete_garbage                           [gc_free_threading.c]
```

## Appendix C: Heritage

Ported from [CinderX](https://github.com/facebookincubator/cinder).
Key divergences: CPython atomic wrappers, multi-phase architecture,
pipelined producer-consumer, split vector, thread-local pools, FTP build
(entirely new). `pycore_ws_deque.h` and `pycore_gc_barrier.h` carry Meta
copyright headers.
