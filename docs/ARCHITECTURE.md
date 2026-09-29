# Parallel GC Architecture

**Audience:** CPython core developers reviewing this work for potential merge.
Assumes familiarity with CPython's GC internals (`gc.c`, `gc_free_threading.c`,
`PyGC_Head`, `ob_gc_bits`, mimalloc page layout) but not this project's design.

For build instructions see [GETTING_STARTED.md](GETTING_STARTED.md).
For design rationale and heritage see [DESIGN_POST.md](DESIGN_POST.md).
The canonical proposal is [pep-parallel-gc.rst](pep-parallel-gc.rst).

This document describes the `cpython/` submodule at fork commit `9da963f754`,
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
condition variables; barriers are limited to the GIL pool's startup handshake.

**Important:** The two implementations are mutually exclusive. GIL builds guard
on `Py_PARALLEL_GC` alone; free-threaded builds guard on both `Py_GIL_DISABLED`
and `Py_PARALLEL_GC`.

Parallel GC is **opt-in at build time** via `--with-parallel-gc` and **opt-in
at runtime** via `gc.enable_parallel(N)`, `-X parallel_gc=N`, or
`PYTHON_PARALLEL_GC=N`. Without the configure flag, the collector implementation
is not compiled. It is intended to preserve reachability, finalization, and
weak-reference semantics; traversal and worklist order are not guaranteed.

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
two parallel entry points. Each parallel phase has its own fallback; a failure
to dispatch one phase does not retroactively make the other phase serial.

```
deduce_unreachable()
  |
  +-- update_refs_with_splits()
  |     Serial. Walks the GC list, sets gc_refs = Py_REFCNT,
  |     and records split-vector waypoints every 8192 objects.
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
`_PyGC_PARALLEL_WORK_CHUNK` (8192) object intervals -- into a growable
`_PyGCSplitVector`:

```c
if (candidates % _PyGC_PARALLEL_WORK_CHUNK == 0) {
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
gc.enable_parallel(N)
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
`wake_cond`. `dispatch_and_wait()` signals at most one worker per available
8192-object slice and waits for completion on `done_cond`. Each has a growing
`_PyWSDeque` and a 1024-item `_PyGCLocalBuffer`.

GIL helper threads do not create or bind persistent `PyThreadState` objects.
This keeps collector helpers out of interpreter thread-state enumeration. The
active helpers invoke `tp_traverse` under the current C-API contract, which
allows traversal from any thread and specifies that only one thread state is
attached while traversal handlers run during garbage collection. The
collecting thread remains that attached thread.

`gc.disable_parallel()` stops the GIL helpers and releases the pool. Re-enabling
creates a new pool. Calling `gc.enable_parallel()` with a different count while
enabled replaces the existing pool.

### 2.6 Serial Fallback Conditions

The GIL collector uses serial code when parallel GC is disabled, workers are not
active, fewer than two 8192-object slices are available, or a phase cannot
assign work. Initialization and thread-creation errors fail
`gc.enable_parallel()` or interpreter startup; they are not serial fallback.

### 2.7 Worker Count

The configured count is an upper bound on threads executing collector work.
Active participation is capped at one worker per 8192 candidate objects. A GIL
build uses helpers while the collecting thread coordinates them. In a
free-threaded build the collecting thread participates as worker zero. The
grain is provisional pending benchmark evidence.

---

## 3. Free-Threaded Build Architecture

**Source:** `Python/gc_free_threading_parallel.c`,
`Include/internal/pycore_gc_ft_parallel.h`
**Guard:** `#if defined(Py_GIL_DISABLED) && defined(Py_PARALLEL_GC)`

### 3.1 Integration with gc_free_threading.c

```
gc_mark_alive_from_roots()                 serial upstream path

deduce_unreachable_heap()
  +-- gc_visit_heaps(... update_refs ...)   serial upstream path
  +-- _PyGC_AssignPagesToBuckets()          parallel-mark preparation
  +-- gc_visit_thread_stacks()               serial deferred-ref scan
  +-- _PyGC_ParallelMarkHeapWithPool()      only parallel FT phase
  +-- gc_visit_heaps(... scan_heap ...)     serial upstream path
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
| Phases parallelised | subtract_refs, mark | mark_heap only |

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
**Abandoned pool pages:** Included via `_mi_abandoned_pool_visit_pages()`.

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
Only that worker queues the object for transitive traversal. Root propagation
that sets the `ALIVE` bit remains in the upstream serial path.

### 3.6 Phases of deduce_unreachable_heap

#### UPDATE_REFS (serial)

`gc_visit_heaps(interp, &update_refs, &state->base)` performs the complete
upstream pass. It remains serial because `visit_decref()` may lazily initialise
referents not found by the heap-page walk.

#### Deferred-reference stack scan (serial)

`gc_visit_thread_stacks(interp, state)` accounts for deferred references after
page assignment and before marking begins.

#### MARK_HEAP (roots + transitive marking)

Workers scan pages for roots and then drain or steal reachable-object work. An
atomic outstanding-work count covers root scanners plus queued and in-flight
objects, so workers stop only when no scanner can publish more work and every
published object has been traversed.

#### SCAN_HEAP (serial)

`gc_visit_heaps(interp, &scan_heap_visitor, &state->base)` identifies the
remaining unreachable objects. It remains serial because it merges reference
counts and rewrites deferred frame references.

### 3.7 Thread Pool (_PyGCThreadPool)

```
  _PyGCThreadPool
  +------------------------------------------------+
  | workers[0..N-1]  deque, wake condition        |
  | done_cond         helper completion signal     |
  | current_work      type + parameters            |
  | worker_args       arguments owned by this pool |
  +------------------------------------------------+
```

Worker 0 is the collecting thread; `N-1` persistent helper threads represent
workers 1 through N-1. `dispatch_and_wait()` signals only the active helpers,
runs `mark_heap_pool_work(pool, 0)` directly, and waits for the
signalled helpers on `done_cond`. The only current free-threaded work descriptor
is `_PyGC_WORK_MARK_HEAP`.

The mark-only helpers do not create Python thread states, so they are not
reported as Python execution threads by external-inspection tools.
`gc.disable_parallel()` joins the helpers and destroys the complete
free-threaded pool; a later enable always creates a new pool.

The configured count is capped at one participant per 8192 candidate objects;
fewer than two work units use the serial path. If page assignment fails,
`mark_heap` uses the upstream serial
visitor. If parallel marking reports an error, reference counts are restored and
the collection aborts, matching the serial error path. Root propagation,
`update_refs`, and `scan_heap` are always serial.

The pool and its worker-argument allocation are both owned by the interpreter's
`_PyGCThreadPool`; there is no process-global worker-argument pointer.

### 3.8 Fork Lifecycle

Before `fork()`, CPython quiesces the enabled helper pool. In the parent, the
after-fork hook makes a best-effort attempt to restart those helpers. A restart
failure is cleared and parallel GC is disabled, leaving the successful parent
process on the serial collector. The child does not create threads in the
post-fork hook: parallel GC is disabled and remains serial until an explicit
`gc.enable_parallel()` creates a fresh active pool. The GIL pool follows the
same externally visible policy.

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

The GIL mark phase drains each worker's local buffer and deque without stealing.

Free-threaded `MARK_HEAP` uses work stealing. An atomic outstanding-work count
covers active root scanners plus queued and in-flight objects, providing a
global termination condition.

---

## 5. Python API

All in `Modules/gcmodule.c`.

### gc.enable_parallel(num_workers)

- **GIL:** `_PyGC_ParallelInit()` plus `_PyGC_ParallelStart()`; `num_workers`
  is the concurrency limit and the collecting thread only coordinates.
- **Free-threaded:** `_PyGC_ThreadPoolInit()`; the collecting thread is one of
  the `num_workers` participants, so the pool creates `num_workers - 1`
  helpers. A
  collection may activate fewer participants when it has fewer work units.
- The runtime API accepts 2--64 workers in both builds.
- Startup configuration applies the same range. Zero leaves parallel GC
  disabled; one is rejected.
- In a build without `--with-parallel-gc`, a nonzero startup request fails
  interpreter initialization. Zero remains valid.
- When already enabled, the same count is a no-op and a different count
  replaces the pool in both builds.

### gc.disable_parallel()

- Both implementations join their helper threads and destroy the complete
  worker pool.

### gc.get_parallel_config()

Returns `{'available': bool, 'enabled': bool, 'num_workers': int}`.
After disable, both report zero workers because their pools have been
destroyed.

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
| `Python/gc_parallel.c` | GIL build: helper threads, subtract/mark/sweep support, split vector, and fork hooks |
| `Python/gc_free_threading_parallel.c` | Free-threaded build: page enumeration/assignment, parallel mark_heap, thread pool, and fork hooks |
| `Python/gc.c` | GIL base GC: `update_refs_with_splits()` and parallel calls in `deduce_unreachable()` |
| `Python/gc_free_threading.c` | Free-threaded base GC: serial root/update/scan paths and optional parallel mark in `deduce_unreachable_heap()` |
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
  |  (1) update_refs_with_splits(base, split_vector)
  |       Serial: gc_refs = Py_REFCNT(op), record waypoints
  |
  |  (2) _PyGC_ParallelSubtractRefs(interp)
  |       Workers: tp_traverse + atomic decref on gc_refs
  |
  |  (3) _PyGC_ParallelMoveUnreachable(interp, base, unr)
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
  |  Serial upstream root propagation
  |
  deduce_unreachable_heap(interp, state)                     [gc_free_threading.c]
  |
  |  (1) gc_visit_heaps(... update_refs ...) serial upstream pass
  |  (2) _PyGC_AssignPagesToBuckets()        parallel-mark preparation
  |  (3) _PyGC_ParallelMarkHeapWithPool()     roots + work-stealing
  |      or mark_heap_visitor                  serial fallback
  |  (4) gc_visit_heaps(... scan_heap ...)    serial upstream pass
  |
  handle_weakrefs / delete_garbage                           [gc_free_threading.c]
```

## Appendix C: Heritage

Ported from [CinderX](https://github.com/facebookincubator/cinder).
Key divergences: CPython atomic wrappers, multi-phase architecture,
split-vector work distribution, thread-local work buffers, and the free-threaded
integration. Provenance and licensing still need an upstream-readiness review.
