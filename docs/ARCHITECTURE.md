# Parallel GC Architecture

**Audience:** CPython core developers reviewing this work for potential merge.
Assumes familiarity with CPython's GC internals (`gc.c`, `gc_free_threading.c`,
`PyGC_Head`, `ob_gc_bits`, mimalloc page layout) but not this project's design.

For build instructions see [GETTING_STARTED.md](GETTING_STARTED.md).
For design rationale and heritage see [DESIGN_POST.md](DESIGN_POST.md).
The canonical proposal is [pep-parallel-gc.rst](pep-parallel-gc.rst).

This document describes the `cpython/` submodule at fork commit `624d4bc8f3`,
based on `python/cpython` commit `333071231d`.

---

## 1. Overview

CPython's cycle collector stops the interpreter while it identifies objects
that are unreachable through reference-count information and graph traversal.
On a small collection, waking helpers and introducing atomic operations costs
more than it saves. On a sufficiently large heap, reference adjustment and
graph traversal can dominate the collection. This project therefore combines
serial fast paths with persistent worker pools: small GIL collections remain
serial, while large GIL collections and enabled free-threaded collections
parallelise the phases for which independent work can be identified safely.

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
Before that call, `gc_collect_main()` resolves an automatic collection to a
generation, merges every younger generation into the selected generation's
linked list, and preserves the upstream trigger and promotion policy. The
parallel threshold therefore applies to the exact combined list that the
serial collector would process; it does not change when or which generations
are selected.

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
  +-- candidates < 16384?
  |     Yes: run subtract_refs() and move_unreachable() on the
  |     collecting thread; do not update the worker controller.
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
        Parallel mark followed by serial list reconstruction.
        Workers scan segments for roots (gc_refs > 0),
        mark subgraphs. The collecting thread sweeps:
        COLLECTING=1 -> unreachable.
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

Current upstream uses bit 0 of `_gc_next` as the temporary unreachable-list
tag. It has no incremental collector's old-space bit; this is why the ported
list reconstruction writes the current bit-0 representation.

### 2.3 Collection Phases

```
  update_refs + exact count                         collecting thread
             |
             +-- fewer than 16,384 candidates --> serial subtract + move
             |
             +-- otherwise
                    |
                    +-- known-root pre-mark         helpers
                    +-- subtract_refs               helpers
                    +-- residual reachability mark  helpers
                    +-- list reconstruction         collecting thread
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

The completed walk also provides the exact candidate count. A collection with
fewer than `_PyGC_MIN_PARALLEL_CANDIDATES` (two 8192-object work slices) runs
the existing serial subtraction and reachability path on the collecting
thread. It does not wake helpers and does not feed a serial timing sample into
the adaptive worker controller. The threshold is deliberately collection-wide:
phase-specific caps would make both measurement and tuning depend on several
interacting policies.

#### Known-root pre-mark -- Parallel queue plus local closure

**Entry:** `_PyGC_ParallelMarkAliveFromQueue()`

The collecting thread enumerates known interpreter roots, marks each root
reachable, expands it by one level, and places the resulting children in a
shared block queue. Expanding one level avoids presenting a small set of
hub-like roots to the workers: the queue normally contains many more
independent starting points than the root set itself.

Workers claim 64-object batches from the shared queue. Descendants discovered
through `tp_traverse` first enter a 1024-entry worker-local buffer; overflow is
flushed to that worker's private deque. This phase does not steal between
private deques. Before a worker reports completion, it must drain both its
local buffer and its entire private deque. This is a lifetime invariant, not
only a load-balancing detail: the deque contains borrowed `PyObject *` values
and is reused by later collections, so no entry may survive the phase.

Objects pre-marked reachable have their COLLECTING bit cleared. The following
subtraction and residual-mark phases can skip those objects and their outgoing
edges. If queue-based pre-mark cannot run, the collecting thread uses the
serial known-root traversal; failure to pre-mark is an optimization failure,
not permission to change reachability semantics.

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

**Parallel traversal callback.** References cross segment boundaries, so the
parallel visitor uses an atomic decrement. The serial visitor retains the
ordinary non-atomic decrement:

```c
int
_PyGC_ParallelVisitDecref(PyObject *op, void *parent)
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

`_PyGC_VisitStackRef()` recognizes both the serial and parallel decrement
visitors and skips borrowed or embedded stack references, whose references are
not represented in `Py_REFCNT`.

#### Phase 2: mark -- Parallel Root Discovery and Local Marking

**Entry:** `_PyGC_ParallelMoveUnreachable()`

Using the same split-vector segments, workers scan for roots (`gc_refs > 0`),
claim them, and traverse each discovered subgraph **locally**. Root scanning is
already partitioned into disjoint list segments. Children are claimed with the
atomic COLLECTING-bit transition so that only the winning worker queues a
shared descendant. The active GIL path does not steal between workers.

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

#### List reconstruction -- Serial

Still inside `_PyGC_ParallelMoveUnreachable()`, the collecting thread walks the
GC list. Objects with COLLECTING still set are linked into `unreachable`;
reachable objects have `_gc_prev` restored as a list pointer. Mutating the
doubly linked list remains serial so that ordering and link repair follow one
owner. Weak-reference handling, finalization, resurrection handling, and
deallocation then continue through the upstream serial machinery.

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

The GIL collector uses serial code when parallel GC is disabled, workers are
not active, the collection has fewer than 16,384 candidates, the split vector
cannot describe usable work, or a phase cannot dispatch. Pre-mark and
subtraction have serial equivalents. Residual marking falls back to
`move_unreachable()`. Initialization and thread-creation errors fail
`gc.enable_parallel()`; they are not collection-time serial fallbacks.

### 2.7 Worker Count

The fixed implementation maximum of 16 is an upper bound. The shared
stochastic controller starts at `min(4, maximum)`. The first valid parallel
collection establishes a cost-per-candidate baseline. Thereafter an accepted
worker count refreshes the baseline on every collection and has a 20% chance
of proposing an unbiased adjacent count. The next valid collection measures
that trial: a lower cost is retained; otherwise the controller returns to the
previous worker count. Bounds are 2 and 16. The accepted count persists across
collections while the pool exists. Sub-threshold GIL collections do not alter
this state.

A GIL build uses that many helper threads while the collecting thread
coordinates them. A free-threaded build counts the collecting thread as worker
zero, so an active count of four means the collector plus three helpers.

---

## 3. Free-Threaded Build Architecture

**Source:** `Python/gc_free_threading_parallel.c`,
`Include/internal/pycore_gc_ft_parallel.h`
**Guard:** `#if defined(Py_GIL_DISABLED) && defined(Py_PARALLEL_GC)`

### 3.1 Integration with gc_free_threading.c

`gc_collect_main()` retains the upstream trigger policy: heap-triggered calls
first consult `gc_should_collect()`, while manual and shutdown calls follow
their existing routes. It then delegates to `gc_collect_internal()`, which owns
the free-threaded stop/resume schedule. Parallel GC changes the implementation
of selected work inside that schedule, not the decision to begin a collection.

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

The parallel calls do not replace the surrounding free-threaded collector.
`gc_collect_internal()` still owns the stop/resume schedule, biased-reference
merging, delayed frees, weak references, finalizers, resurrection, free-list
clearing, and `tp_clear` deletion. Known-root propagation and every operation
inside `deduce_unreachable_heap()` occur while the world is stopped;
callbacks/finalizers and final deletion retain their upstream placement.

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

The design follows the free-threaded heap representation rather than imposing
the GIL collector's linked-list split vector. A page is the natural stable unit
of ownership while the world is stopped. Keeping all objects on one page with
one worker avoids two workers concurrently iterating the same mimalloc page,
while huge pages are spread because one huge page may dominate a bucket.

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

Known-root propagation uses a deliberately different operation. While the
world is stopped, `_PyGC_TryMarkAlive()` performs a relaxed byte load followed
by a relaxed byte store that sets ALIVE and clears UNREACHABLE. Two workers may
therefore both believe that they first marked an object and may both traverse
it. That duplicate traversal is safe and cheaper than an atomic read-modify-
write in this optimization pass. Authoritative `MARK_HEAP` cannot tolerate
duplicate ownership, so it uses the atomic fetch-and operation shown above.
The distinction is intentional; substituting one protocol for the other would
be a design change, not a mechanical cleanup.

### 3.6 Phases of deduce_unreachable_heap

#### Known-root propagation (parallel with serial fallback)

The collector first enqueues known interpreter roots into its normal mark
buffer and object stack. If `gc.freeze()` is inactive and parallel GC is
enabled, those roots are flattened into an array and dispatched to
`_PyGC_ParallelPropagateAliveWithPool()`. Workers use local buffers and deques
to set the ALIVE bit throughout the transitive closure. ALIVE is an
optimization hint: roots can be missed by this pass (for example, extension
globals), so later reference-difference marking remains authoritative. The
unchanged `gc_propagate_alive()` path is used when parallel collection is
unavailable.

#### UPDATE_REFS (parallel with serial fallback)

`_PyGC_ParallelUpdateRefsWithPool()` performs two barrier-separated passes over
the assigned mimalloc page buckets:

1. set UNREACHABLE and initialize `ob_tid` to zero for each relevant object;
2. add the adjusted object reference count and atomically subtract references
   discovered by `tp_traverse`.

The barrier is required because an edge may point into another worker's page;
no worker may subtract from an `ob_tid` that its owner has not initialized.
Objects already marked ALIVE are skipped. Bucket-assignment failure occurs
before either pass and can therefore fall back to the unchanged
`gc_visit_heaps(... update_refs ...)` path. A failure after parallel mutation
has begun aborts the collection instead of mixing structurally different
partial walks.

#### Deferred-reference stack scan (serial)

`gc_visit_thread_stacks(interp, state)` accounts for deferred stack references
after reference initialization and before marking begins. This remains serial
because frame ownership, tagged stack references, and the
`skip_deferred_objects` safety fallback are part of the upstream
free-threaded collector's stack protocol rather than page-local heap work.

#### MARK_HEAP (roots + transitive marking)

Workers scan their pages for objects whose adjusted `gc_refs` is positive (or
which must be retained because deferred references could not be inspected).
The worker that atomically clears UNREACHABLE queues the object and traverses
its referents. Workers drain their own Chase-Lev deque LIFO for locality and
steal FIFO from other workers for balance. An empty worker may finish before
another worker, but this cannot lose reachability: discovered work is owned by
the worker that queued it and every owner drains its deque before completing.
A shared error flag propagates traversal/allocation failure.

#### SCAN_HEAP (parallel with serial/shutdown fallback)

`_PyGC_ParallelScanHeapWithPool()` revisits the pages. Reachable objects have
their `ob_tid` ownership representation restored and ALIVE cleared. Unreachable
objects have deferred reference counting disabled, are linked into per-worker
unreachable or legacy-finalizer lists, and contribute to a per-worker live
count. Unlike `update_refs` and `MARK_HEAP`, this phase independently gathers
the current pages into an array and workers claim pages through an atomic
index. The collecting thread merges the private lists and counts after
dispatch. Unique IDs are accumulated per worker and released in a batch after
the page walk, avoiding a lock acquisition per object. Shutdown collections
retain the serial visitor because their deferred-reference handling has
different locking requirements.

#### Serial work around the parallel heap phases

Parallel reachability does not make the complete collection parallel. After
the first stopped-world section, the collector resumes application threads to
run weak-reference callbacks and finalizers. It stops the world again to
handle resurrection, clear weak references and free lists, resumes it, and
then calls `tp_clear`/deletes garbage through the upstream serial path. This
boundary matters when interpreting performance: a finalizer-heavy workload can
spend most of its full callback interval in finalization and deallocation even
when update/mark/scan are faster.

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

The adaptive controller selects the active participant count; there is no GIL
split-size threshold or phase-specific cap in this collector. If page
assignment fails, the collector uses the serial `update_refs` path. A partial
parallel `update_refs` failure aborts the cycle because it cannot safely resume
with the structurally different serial walk. Parallel marking errors restore
reference state before aborting.

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
- Standalone initial capacity of 4096 pointers (32 KiB on 64-bit builds)
- Each collector worker normally supplies a preallocated 256K-entry backing
  region (about 2 MiB on a 64-bit build), avoiding hot-path allocation and
  allowing growth beyond the standalone initial size
- Growth allocation failure is reported to the collector; the collector never
  silently continues with an incomplete graph

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
targeted dispatch and a separate completion condition. The barrier is used for
the GIL pool's startup handshake and resized to the selected participant count
for the free-threaded `update_refs` phase boundary.

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

The active GIL phases drain each worker's local buffer and private deque
without stealing. Queue-based pre-mark also consumes a shared producer queue.
All three sources must be empty at phase completion; otherwise borrowed object
pointers could survive into a later collection.

Free-threaded `MARK_HEAP` uses work stealing and repeated idle rounds before a
worker leaves the phase. A shared error flag terminates unsuccessful work.

### 4.5 Timing and Adaptation Boundaries

Two timing systems have different responsibilities:

- upstream collection timing supplies the duration reported through normal GC
  statistics and stop callbacks, for both serial and parallel mode;
- private parallel-GC timestamps split the most recent eligible collection
  into implementation phases and provide the adaptive controller's elapsed
  cost.

The GIL collector resets its private timestamps at the common
`gc_collect_main()` entry. A qualifying large `deduce_unreachable()` pass
starts the private elapsed interval immediately before its serial
`update_refs_with_splits()` walk, records the phase boundaries, and updates the
controller once at the post-cleanup point. A sub-threshold collection takes the
serial path without manufacturing a parallel sample. The free-threaded
collector records from the start of `gc_collect_internal()` through
`delete_garbage()` and then updates the controller, before legacy-finalizer
bookkeeping.

Both collectors know the exact candidate count during reference
initialization, before parallel reachability begins. The number ultimately
collected is known only after reachability, finalization, and resurrection
handling. Candidate count is the normalization input because every candidate
can contribute scanning or traversal work; dividing by collected objects would
be undefined for a collection that examines a live heap and reclaims nothing.

A `gc.callbacks` start-to-stop interval is a useful same-binary measure of the
complete collection call, but it is not synonymous with one stopped-world
pause. In the free-threaded collector application threads run during queued
decrefs, callbacks, finalizers, and final deletion between its stopped-world
sections.

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
also report the adaptive worker count. The free-threaded build currently emits
a `parallel_cleanup` capability key inherited from the prototype, although
finalization and `tp_clear` deletion remain serial; the name and usefulness of
that field require API review. Before initialization, `num_workers` is zero.
After disabling, the GIL build continues to report 16 because it retains the
stopped pool; the free-threaded build reports zero because it destroys it.

### gc.get_parallel_stats()

Returns build-specific diagnostic counters and the most recently recorded
private phase timings. These timestamps support analysis and the adaptive
controller; they do not replace upstream `gc.get_stats()` duration reporting.

### gc.collect_async()

Schedules the ordinary collector and returns without waiting. It neither
enables parallel collection nor selects a worker count, so its inclusion in a
parallel-GC proposal is an independent API decision.

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

Failure handling is phase-specific. Failures before parallel mutation may use
the serial equivalent. Once a structurally different parallel phase has
partially mutated reference state, the collector restores state where that is
defined or aborts the collection rather than combine two half-completed
algorithms. Work queues and deques must never silently drop an object.

### Why pre-mark known roots?

Reference subtraction and residual marking are required for correctness, but
most tracked objects in ordinary programs are reachable. Proving a large
reachable subgraph early lets later phases skip both those objects and their
outgoing edges. The GIL level-one queue exists because assigning a handful of
interpreter roots directly produces severe load imbalance; the expanded
children provide enough independent subtrees for useful parallel work.

### Why is GIL list reconstruction serial?

The GC list is a mutable doubly linked list whose `_gc_prev` word was also used
as temporary reference metadata. A single owner can restore links and splice
unreachable objects in one ordered pass without locks or a second merge
protocol. Current measurements show useful gains without parallelizing this
mutation-heavy tail.

### Why are FT finalization and deletion serial?

They preserve the upstream free-threaded collector's weak-reference,
resurrection, and `tp_clear` ordering. These phases can execute arbitrary
object behavior and are not page-local. The consequence is explicit Amdahl's
law: finalizer-heavy collections may show a smaller gain or a regression even
when the parallel heap phases improve.

---

## 7. File Map

### Implementation Files

| File | Description |
|------|-------------|
| `Python/gc_parallel.c` | GIL build: helper threads, root marking, subtract/mark support, split vector, and adaptive dispatch |
| `Python/gc_free_threading_parallel.c` | Free-threaded build: page enumeration/assignment, parallel root/update/mark/scan phases, and adaptive thread pool |
| `Python/gc.c` | GIL base GC: `update_refs_with_splits()` and parallel calls in `deduce_unreachable()` |
| `Python/gc_free_threading.c` | Free-threaded base GC: parallel root propagation and parallel heap-phase dispatch with serial fallbacks |
| `Modules/gcmodule.c` | Python API: parallel control/configuration/statistics and asynchronous collection scheduling |

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
   has signalled completion. The free-threaded `update_refs` barrier also
   prevents any cross-page decrement before every selected worker has
   initialized its pages.

6. **No borrowed pointer survives a GIL phase.** Every pre-mark local buffer
   and private deque is empty before completion; these worklists may be reused
   by a later collection.

7. **Adaptive measurements include serial cleanup.** The controller uses
   elapsed time through its post-delete cleanup boundary, not only helper
   execution. Both implementations call the same normalization function with
   elapsed nanoseconds and their exact candidate count. GIL collections below
   the serial threshold do not update the controller.

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
  |  (2) candidates < 16384?
  |       Yes: serial subtract_refs + move_unreachable; return
  |
  |  (3) _PyGC_ParallelMarkAliveFromQueue(interp, base)
  |       Workers: expand and mark from interpreter roots
  |       or serial known-root fallback
  |
  |  (4) _PyGC_ParallelSubtractRefs(interp, base)
  |       Workers: tp_traverse + atomic decref on gc_refs
  |       or serial subtraction fallback
  |
  |  (5) _PyGC_ParallelMoveUnreachable(interp, base, unr)
  |       Workers: find gc_refs>0 roots, mark locally
  |       Collector: reconstruct lists, move COLLECTING to unreachable
  |
  handle weakrefs / finalize / resurrection / delete         [gc.c]
  record cleanup end and update adaptive controller
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
  |  (3) gc_visit_thread_stacks()              deferred refs, serial
  |  (4) _PyGC_ParallelMarkHeapWithPool()     roots + work-stealing
  |      or mark_heap_visitor                  serial fallback
  |  (5) _PyGC_ParallelScanHeapWithPool()
  |      or scan_heap_visitor                  serial/shutdown fallback
  |
  find weakrefs, resume world
  decref merged objects / callbacks / finalizers
  stop world, resurrection / weakrefs / free lists, resume
  delete_garbage
  update adaptive controller                                [gc_free_threading.c]
```

## Appendix C: Heritage

Ported from [CinderX](https://github.com/facebookincubator/cinder).
Key divergences: CPython atomic wrappers, multi-phase architecture,
split-vector work distribution, thread-local work buffers, and the free-threaded
integration. Provenance and licensing still need an upstream-readiness review.
