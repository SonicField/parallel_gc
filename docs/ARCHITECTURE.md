# Parallel GC Architecture

**Audience:** CPython core developers reviewing this work for potential merge.
Assumes familiarity with CPython's GC internals (`gc.c`, `gc_free_threading.c`,
`PyGC_Head`, `ob_gc_bits`, mimalloc page layout) but not this project's design.

For build instructions see [GETTING_STARTED.md](GETTING_STARTED.md).
For design rationale and heritage see [DESIGN_POST.md](DESIGN_POST.md).
The canonical proposal is [pep-parallel-gc.rst](pep-parallel-gc.rst).

This document describes the `cpython/` submodule at fork commit `323d3cc90a`,
based on `python/cpython` commit `333071231d`.

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

Both implementations use the Chase-Lev deque in `pycore_ws_deque.h`; the GIL
path also uses its local-buffer helpers. Their dispatch and termination
strategies differ. Idle workers are selected and woken through per-worker
condition variables. The GIL pool also uses a startup barrier; the
free-threaded pool resizes an internal phase barrier for each active dispatch.

**Important:** The two implementations are mutually exclusive. GIL builds guard
on `Py_PARALLEL_GC` alone; free-threaded builds guard on both `Py_GIL_DISABLED`
and `Py_PARALLEL_GC`.

Parallel GC is **opt-in at build time** via `--with-parallel-gc` and **opt-in
at runtime** via `gc.enable_parallel()`. There is no environment-variable,
`-X`, or `PyConfig` startup control. Without the configure flag, the collector
implementation is not compiled. It is intended to preserve reachability,
finalization, and weak-reference semantics; traversal and worklist order are
not guaranteed.

```
                    gc.collect()
                        |
            +-----------+-----------+
            |                       |
     GIL Build (gc.c)      Free-threaded Build (gc_free_threading.c)
            |                       |
     gc_parallel.c          gc_free_threading_parallel.c
            |                       |
     +------+------+        +------+------+
     | Deque + local|        | Shared deque |
     | buffer       |        | primitives   |
     | primitives  |        |              |
     +--------------+        +--------------+
```

---

## 2. GIL Build Architecture

**Source:** `Python/gc_parallel.c`, `Include/internal/pycore_gc_parallel.h`
**Guard:** `#ifdef Py_PARALLEL_GC` (defined when `--with-parallel-gc` is passed to configure)
**Requirement:** 64-bit platform (`SIZEOF_VOID_P >= 8`) -- enforced at
compile time in `pycore_gc_parallel.h`.

### 2.1 Integration with gc.c

The parallel collector hooks into `deduce_unreachable()` in `Python/gc.c`.
The serial `update_refs` is replaced by `update_refs_with_splits()`, followed by
parallel interpreter-root marking and two parallel collector phases. Each
parallel phase retains its baseline fallback behavior.

```
deduce_unreachable()
  |
  +-- update_refs_with_splits()
  |     Serial. Walks the GC list, sets gc_refs = Py_REFCNT,
  |     and records split-vector waypoints every 8192 objects.
  |
  +-- _PyGC_ParallelMarkAliveFromQueue()
  |     Parallel. Expands interpreter roots into a shared queue,
  |     then traverses their reachable subgraphs.
  |
  +-- _PyGC_ParallelSubtractRefs()
  |     Parallel. Decrements gc_refs via tp_traverse with
  |     atomic decref visitor. Split-vector work distribution.
  |
  +-- _PyGC_ParallelMoveUnreachable()
        Parallel mark + serial sweep.
        Workers scan segments for roots (gc_refs > 0),
        mark subgraphs. Main thread sweeps: COLLECTING=1 -> unreachable.
```

**Fallback:** In `deduce_unreachable()`:

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

### 2.3 Collection Phases

```
  +-------------+     +----------------+     +-----------+     +-------+
  | update_refs | --> | subtract_refs  | --> |   mark    | --> | sweep |
  |  (serial)   |     |   (parallel)   |     | (parallel)|     |(serial)|
  +-------------+     +----------------+     +-----------+     +-------+
   Record split       Split-vector           Split-vector      Main thread
   waypoints           segments               segments          moves unreachable
```

#### update_refs (Serial, with split recording)

**Entry:** `update_refs_with_splits()` in `Python/gc.c`

Walks the GC list and sets `gc_refs = ob_refcnt` for every object.
Simultaneously records **split points** -- pointers into the GC list at
`_PyGC_SPLIT_INTERVAL` (8192) object intervals -- into a growable
`_PyGCSplitVector`:

```c
if (candidates % _PyGC_SPLIT_INTERVAL == 0) {
    _PyGCSplitVector_Push(splits, gc);
}
/* Append containers as the exclusive end marker. */
_PyGCSplitVector_Push(splits, containers);
```

The split vector enables O(1) parallel partitioning without an extra list
traversal. A sentinel entry (the list head) is pushed at the end as an
exclusive end marker.

#### Phase 1: subtract_refs -- Parallel Reference Count Decrement

**Entry:** `_PyGC_ParallelSubtractRefs()`

**Purpose:** Call `tp_traverse` with a visitor that atomically decrements
`gc_refs` of referenced objects. After this phase, objects with `gc_refs > 0`
are roots.

**Distribution: Split vector segments.** Workers get contiguous ranges:

```c
size_t entries_per_worker = splits->count / par_gc->num_workers;
par_gc->workers[i].slice_start = splits->entries[start_idx];
par_gc->workers[i].slice_end   = splits->entries[end_idx];
par_gc->workers[i].phase = _PyGC_PHASE_SUBTRACT_REFS;
```

**Shared traversal callback.** References cross segment boundaries, so a
parallel-GC build uses an atomic decrement in the same callback used by the
serial path:

```c
int
_PyGC_VisitDecref(PyObject *op, void *parent)
{
    if (_PyObject_IS_GC(op)) {
        PyGC_Head *gc = AS_GC(op);
        if (gc_is_collecting(gc)) {
            _Py_atomic_add_uintptr(
                &gc->_gc_prev,
                -((uintptr_t)1 << _PyGC_PREV_SHIFT));
        }
    }
    return 0;
}
```

Using one callback identity is semantically important: `_PyGC_VisitStackRef()`
recognizes it and skips borrowed or embedded stack references, whose reference
counts are not represented in `Py_REFCNT`. The callback is exported only to
the core and `_testinternalcapi` when parallel GC is compiled.

#### Phase 2: mark -- Parallel Root Discovery and Local Marking

**Entry:** `_PyGC_ParallelMoveUnreachable()`

Using the same split-vector segments, workers scan for roots (`gc_refs > 0`),
claim them atomically, and traverse each discovered subgraph **locally**. The
active GIL path does not use work stealing.

Worker dispatch:

```c
// Scan segment for roots
while (gc != end) {
    if (!gc_is_collecting(gc)) { gc = next; continue; }
    if (gc_get_refs(gc) > 0) {
        if (gc_try_mark_reachable_atomic(gc)) {
            _PyGCLocalBuffer_Push(&worker->local_buffer, _Py_FROM_GC(gc));
        }
    }
    gc = next;
}
// Drain local buffer and own deque until both empty
```

#### Phase 3: sweep -- Serial

The main thread sweeps the GC list. Objects with
COLLECTING still set are moved to unreachable; reachable objects have
`_gc_prev` restored. Weak-reference handling, finalization, and deallocation
then continue on the existing serial paths.

### 2.4 Atomic Marking via Fetch-And

```c
static inline int
gc_try_mark_reachable_atomic(PyGC_Head *gc)
{
    // Fast path: avoid an RMW when the object is already marked
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
gc.enable_parallel()
  |
  _PyGC_ParallelInit()
  _PyGC_ParallelStart()
  |
  [... GC collections ...]
  |
gc.disable_parallel()
  |
  _PyGC_ParallelStop()
```

Workers are persistent while parallel GC is enabled and sleep on their own
`wake_cond`. `dispatch_and_wait()` signals the count selected by the adaptive
controller and waits for completion on `done_cond`. Each has a growing
`_PyWSDeque` and a 1024-item `_PyGCLocalBuffer`.

GIL helper threads create and bind persistent `PyThreadState` objects so debug
reference-count accounting and traversal callbacks have valid thread state.

`gc.disable_parallel()` stops the GIL helpers but retains the pool. Re-enabling
restarts it with the same fixed maximum.

### 2.6 Serial Fallback Conditions

The GIL collector uses serial code when parallel GC is disabled, workers are not
active, the split vector contains fewer than two ranges, or a phase cannot
dispatch. Initialization and thread-creation errors fail
`gc.enable_parallel()`; they are not serial fallback.

### 2.7 Worker Count

The fixed implementation maximum of 16 is an upper bound. A shared stochastic
hill-climbing controller starts at 4, randomly tries an adjacent count, and
keeps that trial only when the next collection's measured cost per candidate
improves. A GIL build uses helper workers while the collecting thread
coordinates them. A free-threaded build includes the collecting thread as
worker zero.

---

## 3. Free-Threaded Build Architecture

**Source:** `Python/gc_free_threading_parallel.c`,
`Include/internal/pycore_gc_ft_parallel.h`
**Guard:** `#if defined(Py_GIL_DISABLED) && defined(Py_PARALLEL_GC)`

### 3.1 Integration with gc_free_threading.c

```
gc_mark_alive_from_roots()
  +-- _PyGC_ParallelPropagateAliveWithPool()
      or gc_propagate_alive()               serial fallback

deduce_unreachable_heap()
  +-- _PyGC_AssignPagesToBuckets()          page-bucket preparation
  +-- _PyGC_ParallelUpdateRefsWithPool()
      or gc_visit_heaps(... update_refs ...) serial fallback
  +-- gc_visit_thread_stacks()               serial deferred-ref scan
  +-- _PyGC_ParallelMarkHeapWithPool()
      or mark_heap_visitor                   serial fallback
  +-- _PyGC_ParallelScanHeapWithPool()
      or scan_heap_visitor                   serial/shutdown fallback
```

### 3.2 Object Layout

- `ob_gc_bits` -- `uint8_t` with flag bits (ALIVE=0x20 i.e. 1<<5, UNREACHABLE=0x04 i.e. 1<<2)
- `ob_tid` -- repurposed during STW to store `gc_refs`

### 3.3 Architectural Differences from GIL Build

| Aspect | GIL Build | Free-threaded Build |
|--------|-----------|-----------|
| Marking bit | `_gc_prev` COLLECTING flag | `ob_gc_bits` ALIVE/UNREACHABLE |
| gc_refs storage | Upper bits of `_gc_prev` | `ob_tid` (repurposed during STW) |
| Marking op | Fetch-And on `uintptr_t` | Fetch-And clears `UNREACHABLE` |
| Work distribution | Split vector (GC list) | Page-based (mimalloc buckets) |
| Phases parallelised | root marking, subtract_refs, mark | root propagation, update_refs, mark_heap, scan_heap |

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

### 3.5 Atomic Marking on ob_gc_bits

```c
static inline int
_PyGC_TryMarkReachable(PyObject *op)
{
    if (!(_Py_atomic_load_uint8_relaxed(&op->ob_gc_bits)
          & _PyGC_BITS_UNREACHABLE)) {
        return 0;
    }
    return _PyGC_TryClearBit(op, _PyGC_BITS_UNREACHABLE);
}
```

The old value gives exactly one worker ownership of a newly reachable object.
Only that worker queues the object for transitive traversal.

### 3.6 Phases of deduce_unreachable_heap

#### Root propagation (parallel with serial fallback)

The root stack and prefetch buffer are flattened and dispatched to
`_PyGC_ParallelPropagateAliveWithPool()`. The unchanged
`gc_propagate_alive()` path is used when parallel collection is unavailable.

#### UPDATE_REFS (parallel with serial fallback)

`_PyGC_ParallelUpdateRefsWithPool()` initializes reference state across the
assigned mimalloc page buckets. Bucket-assignment failure falls back to the
unchanged `gc_visit_heaps(... update_refs ...)` path.

#### Deferred-reference stack scan (serial)

`gc_visit_thread_stacks(interp, state)` accounts for deferred references after
page assignment and before marking begins.

#### MARK_HEAP (roots + transitive marking)

Workers scan pages for roots and then drain or steal reachable-object work.
After exhausting available work, a worker performs repeated idle rounds before
exiting the phase; a shared error flag terminates unsuccessful work.

#### SCAN_HEAP (parallel with serial/shutdown fallback)

`_PyGC_ParallelScanHeapWithPool()` identifies remaining unreachable objects,
merges worker results, and performs the baseline unique-ID batch release.
Shutdown collections retain the serial visitor path.

### 3.7 Thread Pool (_PyGCThreadPool)

```
  _PyGCThreadPool
  +------------------------------------------------+
  | workers[0..N-1]  deque, wake condition        |
  | done_cond         helper completion signal     |
  | current_work      type + parameters            |
  +------------------------------------------------+
```

Worker 0 is the collecting thread; `N-1` persistent helper threads represent
workers 1 through N-1. `dispatch_and_wait()` signals only the active helpers,
runs worker zero's phase directly, and waits for the signalled helpers on
`done_cond`. Work descriptors cover `PROPAGATE`, `UPDATE_REFS`, `MARK_HEAP`,
and `SCAN_HEAP`.

The helpers create persistent Python thread states and install their state and
interpreter pointers in thread-local storage while running, without a full
bind. This supplies debug-build reference-count accounting for traversal
callbacks.
`gc.disable_parallel()` joins the helpers and destroys the complete
free-threaded pool; a later enable always creates a new pool.

The adaptive controller selects the active participant count; it is not capped
by an 8192-object heuristic. If page assignment fails, the collector uses the
serial `update_refs` path. A partial parallel `update_refs` failure aborts the
cycle because it cannot safely resume with the structurally different serial
walk. Parallel marking errors restore reference state before aborting.

The pool belongs to the interpreter. The baseline worker-argument array is a
file-static allocation shared by the FT pool lifecycle.

### 3.8 Fork Lifecycle

The restored baseline does not install special parallel-GC fork hooks. Fork
lifecycle behavior remains a required validation item and is not currently a
claimed property.

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
- top/bot initialised to 1
- Initial capacity of 4096 pointers (32 KiB on 64-bit builds)
- Growth allocation failure is reported to the collector; it never drops an
  item and continues with a partially marked graph

### 4.2 Synchronisation

**File:** `Include/internal/pycore_gc_barrier.h`

```c
typedef struct {
    unsigned int num_left;
    unsigned int capacity;
    unsigned int epoch;       // Prevents spurious wakeup bugs
    PyMUTEX_T lock;
    PyCOND_T cond;
} _PyGCBarrier;
```

The barrier is portable across the POSIX and Windows implementations of the
underlying mutex and condition-variable primitives. It is not the general
dispatch mechanism. Both collectors use per-worker condition variables for
targeted dispatch and a separate completion condition. The barrier is currently
used for the GIL pool's startup handshake.

### 4.3 GIL Local Work Buffers

**Defined in:** `pycore_ws_deque.h`

```
  tp_traverse --> LocalBuffer (1024, zero fences)
                     | overflow: half-flush to deque
                     | refill: batch-pull from deque
                     | steal: batch-steal from victim
```

- `_PyGC_OverflowFlush()`: half-flush to reduce deque traffic
- `_PyGC_RefillLocalFromDeque()`: refill with up to 512 items
- `_PyGC_BatchSteal()`: available shared helper; not used by the active paths

### 4.4 Work Termination

The active GIL mark phases drain each worker's local buffer and deque without
stealing.

Free-threaded `MARK_HEAP` uses work stealing and repeated idle rounds before a
worker leaves the phase. A shared error flag terminates unsuccessful work.

---

## 5. Python API

All in `Modules/gcmodule.c`.

### gc.enable_parallel()

- **GIL:** `_PyGC_ParallelInit()` plus `_PyGC_ParallelStart()` create the fixed
  16-worker pool; the collecting thread only coordinates.
- **Free-threaded:** `_PyGC_ThreadPoolInit()`; the collecting thread is one of
  the 16 participants, so the pool creates 15 helpers.
- The adaptive controller may activate fewer participants for a collection.
- There is no startup configuration or caller-supplied worker count.
- Calling the function while already enabled is a no-op.

### gc.disable_parallel()

- A GIL build stops its helpers but retains the allocated pool so it can be
  restarted. A free-threaded build joins its helpers and destroys the pool.

### gc.get_parallel_config()

Returns availability, enabled state, and the fixed worker limit. Enabled builds
also report the adaptive worker count; the free-threaded build reports that
parallel cleanup is available. Disabled configurations report zero even when
the GIL build retains an inactive pool.

---

## 6. Key Design Decisions

### Why Fetch-And over CAS?

Monotonic bit (1->0 only). Fetch-And always succeeds in one instruction.
Old value gives ownership. No ABA. Check-first relaxed load handles shared
objects cheaply. See Section 2.4.

### Why persistent thread pool?

Thread creation and joining are avoided between collections. Deque storage is
retained and reused. Dispatch uses targeted condition-variable signals rather
than a barrier broadcast.

### Why the split vector?

GC list has no random access. Split vector piggybacks on `update_refs`
(zero extra traversals, zero atomics for partitioning). 8K resolution for
fine-grained balancing.

### Why Fetch-And in free-threaded MARK_HEAP?

Clearing `UNREACHABLE` is monotonic. Fetch-And returns the old bit value, so one
worker owns traversal without a CAS retry loop. See Section 3.5.

### How is deque allocation failure handled?

Every worklist producer propagates allocation failure. The GIL collector
restores its list state and uses the serial path; the free-threaded collector
restores reference counts and aborts the collection. Queues are reset after a
free-threaded dispatch so borrowed object pointers cannot survive an error.

---

## 7. File Map

### Implementation Files

| File | Description |
|------|-------------|
| `Python/gc_parallel.c` | GIL build: helper threads, root marking, subtract/mark support, split vector, and adaptive dispatch |
| `Python/gc_free_threading_parallel.c` | Free-threaded build: page enumeration/assignment, parallel root/update/mark/scan phases, and adaptive thread pool |
| `Python/gc.c` | GIL base GC: `update_refs_with_splits()` and parallel calls in `deduce_unreachable()` |
| `Python/gc_free_threading.c` | Free-threaded base GC: parallel root propagation and parallel heap-phase dispatch with serial fallbacks |
| `Modules/gcmodule.c` | Python API: `enable_parallel()`, `disable_parallel()`, and `get_parallel_config()` |

### Header Files

| File | Description |
|------|-------------|
| `Include/internal/pycore_gc_parallel.h` | GIL: worker/global state, split vector, prefetch primitives, phase enum, API |
| `Include/internal/pycore_gc_ft_parallel.h` | Free-threaded: atomic bit ops, thread pool, mark work descriptor, worker state, page buckets |
| `Include/internal/pycore_ws_deque.h` | Chase-Lev deque, local buffer, shared batch operations |
| `Include/internal/pycore_gc_barrier.h` | Barrier with epoch protection, portable mutex/condvar macros |

### Documentation

| File | Description |
|------|-------------|
| `docs/ARCHITECTURE.md` | This file |
| `docs/DESIGN_POST.md` | Design rationale, CinderX heritage, optimisations |
| `docs/GETTING_STARTED.md` | Reviewer quick start: build, test, evaluate |
| `docs/pep-parallel-gc.rst` | Canonical proposal |

---

## 8. Required Invariants

1. **Every reachable object must be marked.** Atomic marking, deque/buffer
   draining, and termination detection are intended to establish this property;
   the concurrency audit must validate that argument for every active path.

2. **Marking is monotonic.** COLLECTING/UNREACHABLE bits only transition in one
   direction during a collection. No re-set after clear.

3. **Semantic equivalence is the target.** Parallel GC must identify the same
   reachable and unreachable objects as serial GC. Traversal and worklist order
   are not guaranteed. Finalizers and weak-reference callbacks remain serial.

4. **Controlled sharing.** Each helper has its own deque and wake state; GIL
   helpers also have local work buffers. Shared marking bits, counters, work
   descriptors, and synchronization state use their documented atomic or
   lock-based protocols.

5. **Phase completion.** A dispatch does not return until every selected worker
   has signalled completion.

---

## Appendix A: Full Collection Flow (GIL Build)

```
gc.collect()
  |
  deduce_unreachable(base, unreachable)                      [gc.c]
  |
  |  (1) _PyGC_ParallelMarkAliveFromQueue(interp, base)
  |       Workers: mark from interpreter roots
  |
  |  (2) update_refs_with_splits(base, split_vector)
  |       Serial: gc_refs = Py_REFCNT(op), record waypoints
  |
  |  (3) _PyGC_ParallelSubtractRefs(interp)
  |       Workers: tp_traverse + atomic decref on gc_refs
  |
  |  (4) _PyGC_ParallelMoveUnreachable(interp, base, unr)
  |       Workers: find gc_refs>0 roots, mark locally
  |       Main: serial sweep, move COLLECTING to unreachable
  |
  finalize_garbage(unreachable)                              [gc.c]
```

## Appendix B: Full Collection Flow (Free-threaded Build)

```
  gc_collect_internal()
  |
  gc_mark_alive_from_roots(interp, state)                    [gc_free_threading.c]
  |  _PyGC_ParallelPropagateAliveWithPool()
  |  or serial root propagation fallback
  |
  deduce_unreachable_heap(interp, state)                     [gc_free_threading.c]
  |
  |  (1) _PyGC_AssignPagesToBuckets()        parallel-phase preparation
  |  (2) _PyGC_ParallelUpdateRefsWithPool()
  |      or gc_visit_heaps(... update_refs ...) serial fallback
  |  (3) _PyGC_ParallelMarkHeapWithPool()     roots + work-stealing
  |      or mark_heap_visitor                  serial fallback
  |  (4) _PyGC_ParallelScanHeapWithPool()
  |      or scan_heap_visitor                  serial/shutdown fallback
  |
  handle_weakrefs / delete_garbage                           [gc_free_threading.c]
```

## Appendix C: Heritage

Ported from [CinderX](https://github.com/facebookincubator/cinder).
Key divergences: CPython atomic wrappers, multi-phase architecture,
split-vector work distribution, thread-local work buffers, and the free-threaded
integration. Provenance and licensing still need an upstream-readiness review.
