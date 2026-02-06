PEP: XXXX
Title: Parallel Garbage Collection for CPython
Author: Alex Turner
Status: Draft
Type: Standards Track
Requires: 703 (for free-threaded variant)
Python-Version: 3.15
Created: 2026-03-26
Post-History:


Abstract
========

This PEP proposes adding optional parallel garbage collection to
CPython's cyclic garbage collector.  Two implementations are provided:
one for GIL-enabled builds (``gc_parallel.c``) and one for free-threaded
builds (``gc_free_threading_parallel.c``).  Both parallelise the mark
phase using persistent worker thread pools, Chase-Lev work-stealing
deques, and atomic marking operations.

Parallel GC is opt-in at build time via ``--with-parallel-gc`` and at
runtime via ``gc.enable_parallel(num_workers=N)``.  Serial collection
remains the default.

On heaps with 500K+ tracked objects, collection speedups of 1.2--2.3x
are achieved with 8 workers (FTP build, PGO+LTO).  Stop-the-world pause
reductions of 54--67% are measured on realistic workloads.

No changes are made to the public ``gc`` module API semantics.  No
changes are made to reference counting behaviour.


Motivation
==========

GC pause times scale linearly with heap size
--------------------------------------------

CPython's cyclic GC is single-threaded.  At 1M+ tracked objects,
full-generation collections take hundreds of milliseconds.  The mark
phase dominates: ``update_refs``, ``subtract_refs``, and
``move_unreachable`` all walk the entire object graph serially.

AI/ML workloads are disproportionately affected
------------------------------------------------

Training loops create millions of tensor wrappers, autograd graph nodes,
and intermediate objects.  Users call ``gc.collect()`` manually at GPU
synchronisation points.  All CPU cores sit idle during GC while the GPU
computes.

Free-threaded Python amplifies the problem
------------------------------------------

Without the GIL (PEP 703), applications create more objects across more
threads.  GC pauses during stop-the-world become a scaling bottleneck.

Modern hardware has idle cores during GC
-----------------------------------------

Single-threaded GC wastes available parallelism on machines with 8--128
cores.

Existing mitigations are insufficient
--------------------------------------

- ``gc.disable()`` risks unbounded memory growth from reference cycles.
- Generational collection reduces frequency but not worst-case pause
  duration for full collections.
- Incremental GC (3.12+) reduces pause latency but does not reduce total
  GC work for manual ``gc.collect()`` calls.


Rationale
=========

Why parallel marking?
---------------------

The mark phase dominates GC cost for large heaps.  Marking is
embarrassingly parallel on wide/layered object graphs: independent
subtrees can be traversed by different workers without coordination.

Finalisation and deallocation are inherently serial in CPython (weak
reference callbacks, ``__del__`` methods, ``tp_clear``).  Attempts to
parallelise cleanup were investigated and rejected (see
`Rejected Alternatives`_).

Why this approach?
------------------

**Persistent thread pool.**  Workers are created once at
``gc.enable_parallel()`` and reused across collections.  Avoids
per-collection thread creation overhead (~50--200 us per thread on
Linux).

**Work-stealing deques (Chase-Lev).**  Each worker has a local deque for
discovered objects.  When a worker's deque empties, it steals from
others.  This provides automatic load balancing with low contention.
Based on Chase & Lev 2005 [1]_ with Le et al. 2013 [2]_ weak-memory
corrections.

**Atomic marking.**  In the GIL build, a single Fetch-And instruction
claims an object for traversal (no CAS retry loops).  In the FTP build,
relaxed load/store is sufficient during stop-the-world.  A preceding
relaxed-load check filters already-marked objects cheaply (~10x cheaper
than an atomic read-modify-write).

**Local work buffers.**  1024-item thread-local buffer between
``tp_traverse`` callbacks and the deque.  Push/pop with zero memory
fences; the deque is only touched on overflow/underflow, amortising
atomic operation costs.

**Barrier synchronisation.**  Workers synchronise via barriers between GC
phases, not fine-grained locking.  Epoch-based counting barrier built on
``PyMUTEX_T`` / ``PyCOND_T``, portable to POSIX and Windows.

**Serial fallback.**  If parallel GC is not enabled, or the heap is too
small, the existing serial collector runs unchanged.

Why two implementations?
------------------------

The GIL and free-threaded builds have fundamentally different object
layouts and memory subsystems, requiring different marking strategies and
work distribution mechanisms.

**GIL build** (``gc_parallel.c``): Uses the ``_gc_prev`` COLLECTING bit
for marking via Fetch-And.  Split vector recorded during serial
``update_refs`` for work distribution.  Phases: ``update_refs`` (serial)
-> ``mark_alive`` (parallel) -> ``subtract_refs`` (parallel) -> ``mark``
(parallel) -> sweep (serial).

**Free-threaded build** (``gc_free_threading_parallel.c``): Uses
``ob_gc_bits`` for marking via relaxed load/store.  Page-based
distribution via mimalloc internals.  Phases: ``mark_alive`` (parallel)
-> ``UPDATE_REFS`` (parallel) -> ``MARK_HEAP`` (parallel) ->
``SCAN_HEAP`` (parallel).


Specification
=============

Build Configuration
-------------------

Parallel GC is opt-in at build time via the ``--with-parallel-gc``
configure flag.  This flag defines the ``Py_PARALLEL_GC`` preprocessor
macro.  Without it, no parallel GC code is compiled and the serial
collector is used exclusively.

Both GIL and free-threaded builds use the same flag::

    # GIL build with parallel GC
    ./configure --with-parallel-gc

    # Free-threaded build with parallel GC
    ./configure --with-parallel-gc --disable-gil

    # Without the flag: serial GC only (no parallel code compiled)
    ./configure
    ./configure --disable-gil

The compile guards are:

- GIL build: ``#ifdef Py_PARALLEL_GC``
- Free-threaded build: ``#if defined(Py_GIL_DISABLED) && defined(Py_PARALLEL_GC)``

The two implementations are mutually exclusive.

Python API
----------

Four new functions are added to the ``gc`` module::

    import gc

    # Enable parallel GC with N worker threads (N >= 2)
    gc.enable_parallel(num_workers=4)

    # Disable parallel GC (destroys worker threads, reverts to serial)
    gc.disable_parallel()

    # Query configuration
    config = gc.get_parallel_config()
    # Returns: {'available': True, 'enabled': True, 'num_workers': 4}
    # FTP build also includes: 'parallel_cleanup': True

    # Query statistics (for profiling/debugging)
    stats = gc.get_parallel_stats()
    # Returns dict with per-worker and per-phase timing data (ns)

``gc.enable_parallel(num_workers)`` requires ``num_workers >= 2``.
Maximum is 64 for free-threaded builds, 1024 for GIL builds.  If called
when parallel GC is already enabled with the same worker count, it is a
no-op.  If called with a different worker count, the existing pool is
torn down and a new one created.

If parallel GC was not compiled (``--with-parallel-gc`` not passed),
``gc.enable_parallel()`` raises ``RuntimeError``.
``gc.get_parallel_config()`` returns ``{'available': False, ...}``.

``gc.get_parallel_stats()`` returns build-mode-specific keys:

GIL build::

    {'enabled': True, 'num_workers': 4,
     'roots_found': 142, 'roots_distributed': 8703,
     'gc_roots_found': 0,
     'collections_attempted': 5, 'collections_succeeded': 5,
     'workers': [{'objects_marked': 131072, ...}, ...],
     'phase_timing': {
         'update_refs_ns': ..., 'mark_alive_ns': ...,
         'subtract_refs_ns': ..., 'mark_ns': ...,
         'scan_mark_ns': ..., 'stw_pause_ns': ...,
     }}

FTP build::

    {'enabled': True, 'num_workers': 4,
     'phase_timing': {
         'mark_alive_ns': ..., 'update_refs_ns': ...,
         'mark_heap_ns': ..., 'scan_heap_ns': ...,
         'total_ns': ..., ...
     }}

Command-Line and Environment Variable
--------------------------------------

::

    # -X flag (N = number of workers)
    python -X parallel_gc=N script.py

    # Environment variable
    PYTHONPARALLELGC=N python script.py

Both activate parallel GC at interpreter startup.  The ``gc`` module API
allows enabling and disabling at any time during execution.

C API (Internal)
----------------

All C API functions are underscore-prefixed and not part of the public
API.  They are subject to change without notice.

GIL build::

    _PyGC_ParallelInit(interp, num_workers)
    _PyGC_ParallelStart(interp)
    _PyGC_ParallelStop(interp)
    _PyGC_ParallelFini(interp)
    _PyGC_ParallelIsEnabled(interp)
    _PyGC_ParallelMoveUnreachable(interp, young, unreachable)
    _PyGC_ParallelSubtractRefs(interp, base)
    _PyGC_ParallelMarkAliveFromQueue(interp, containers)

FTP build::

    _PyGC_ThreadPoolInit(interp, num_workers)
    _PyGC_ThreadPoolFini(interp)
    _PyGC_AssignPagesToBuckets(state)
    _PyGC_ParallelUpdateRefsWithPool(interp, state)
    _PyGC_ParallelMarkHeapWithPool(interp, state)
    _PyGC_ParallelScanHeapWithPool(interp, state)
    _PyGC_ParallelPropagateAliveWithPool(interp, state)

GIL Build: Multi-Phase Architecture
------------------------------------

The parallel collector hooks into ``deduce_unreachable()`` in
``Python/gc.c``.  The serial ``update_refs`` is replaced by
``update_refs_with_splits()``, and three parallel entry points are called
in sequence.  If any returns 0 (insufficient work), the collector falls
through to the serial code path.

**Phase 0: update_refs (serial, with split recording).**  Walks the GC
list and sets ``gc_refs = ob_refcnt`` for every object.  Simultaneously
records split points -- pointers into the GC list at
``_PyGC_SPLIT_INTERVAL`` (8192) object intervals -- into a growable
``_PyGCSplitVector``.  The split vector enables O(1) parallel
partitioning without an extra list traversal.

**Phase 1: mark_alive (parallel).**  Pre-marks objects reachable from
interpreter roots (sysdict, builtins, thread stacks, type dicts) before
the main GC cycle.  Uses a pipelined producer-consumer design: the main
thread expands roots by one level via ``tp_traverse``, pushing level-1
children to a shared work queue.  Workers claim batches of 64 objects
using atomic CAS and traverse subtrees locally.

This design addresses a distribution problem: ~100 interpreter roots
form a hub, and naive work-stealing causes 99% imbalance (one worker
marks most of the heap before others can steal).  Level-1 expansion
provides thousands of distributed starting points.

**Phase 2: subtract_refs (parallel).**  Decrements ``gc_refs`` for
internal references.  Each worker is assigned a contiguous range of
split-vector entries.  The decrement visitor uses atomic operations
because references cross segment boundaries::

    static inline void
    gc_decref_atomic(PyGC_Head *gc)
    {
        _Py_atomic_add_uintptr(&gc->_gc_prev,
                               -((uintptr_t)1 << _PyGC_PREV_SHIFT));
    }

Objects marked alive in Phase 1 are skipped via relaxed-load check.

**Phase 3: mark (parallel).**  Workers scan their split-vector segments
for roots (objects with ``gc_refs > 0``), mark them, and traverse
subgraphs locally -- no work-stealing.  This is safe because Phase 1
already marked the vast majority of reachable objects from interpreter
roots; residual GC roots are typically few.

**Phase 4: sweep (serial).**  Main thread sweeps the GC list.  Objects
with the COLLECTING flag still set are moved to the unreachable list.
Reachable objects have ``_gc_prev`` restored as doubly-linked list
pointers.

Atomic Marking: Fetch-And
~~~~~~~~~~~~~~~~~~~~~~~~~~

Objects are marked reachable by atomically clearing the COLLECTING bit in
``_gc_prev``.  Fetch-And is used rather than CAS::

    static inline int
    gc_try_mark_reachable_atomic(PyGC_Head *gc)
    {
        // Fast path: relaxed load (~1 cycle vs ~10 for RMW)
        uintptr_t prev = _Py_atomic_load_uintptr_relaxed(&gc->_gc_prev);
        if (!(prev & _PyGC_PREV_MASK_COLLECTING)) {
            return 0;  // Already marked
        }

        // Fetch-And: always succeeds in one operation (no retry loop)
        uintptr_t old_prev = _Py_atomic_and_uintptr(
            &gc->_gc_prev, ~_PyGC_PREV_MASK_COLLECTING);
        int marked = (old_prev & _PyGC_PREV_MASK_COLLECTING) != 0;

        if (marked) {
            _Py_atomic_fence_acquire();  // ARM: consistent field reads
        }
        return marked;
    }

Fetch-And is superior to CAS here because it always succeeds in one
atomic operation -- the old value tells us whether we won the race.
Combined with the check-first relaxed load, shared objects (types,
builtins, modules) that are already marked are handled with a cheap
relaxed load instead of an atomic read-modify-write.

Free-Threaded Build: Page-Based Architecture
---------------------------------------------

The FTP parallel GC uses ``ob_gc_bits`` (a ``uint8_t`` on ``PyObject``)
for marking and ``ob_tid`` (repurposed during stop-the-world) for
``gc_refs`` storage.

**Page-based work distribution.**  FTP Python uses mimalloc for memory
allocation.  Objects live on mimalloc pages, which are natural units of
work distribution.  Pages are enumerated in O(pages) time (not
O(objects)) and assigned to worker buckets: normal pages use sequential
filling for locality; huge pages use round-robin to spread expensive
traversals.

**Relaxed-atomic marking.**  During stop-the-world, all threads are
cooperating GC workers.  Marking uses relaxed read + relaxed store
instead of atomic read-modify-write::

    static inline int
    _PyGC_TryMarkAlive(PyObject *op)
    {
        if (_Py_atomic_load_uint8_relaxed(&op->ob_gc_bits)
                & _PyGC_BITS_ALIVE) {
            return 0;
        }
        uint8_t new_bits = (op->ob_gc_bits | _PyGC_BITS_ALIVE)
                         & ~_PyGC_BITS_UNREACHABLE;
        _Py_atomic_store_uint8_relaxed(&op->ob_gc_bits, new_bits);
        _Py_atomic_fence_acquire();
        return 1;
    }

If two workers race to mark the same object, both write ALIVE
(idempotent), both traverse referents.  Duplicate traversal terminates
at the next level's relaxed-read check.  This eliminates ~20--40 cycles
per object compared to atomic read-modify-write.

**Phases:**

1. ``mark_alive`` -- Pre-marks objects reachable from interpreter roots
   (runs before ``deduce_unreachable_heap``).
2. ``UPDATE_REFS`` -- Initialises ``gc_refs`` from reference counts over
   page buckets.  Two sub-phases separated by a barrier: ``init_refs``
   (zero ``ob_tid``, set UNREACHABLE) then ``compute_refs`` (add
   ``Py_REFCNT`` to ``ob_tid``, subtract internal refs).
3. ``MARK_HEAP`` -- Finds roots (``gc_refs > 0``) and marks reachable
   objects using work-stealing for transitive closure.
4. ``SCAN_HEAP`` -- Collects unreachable objects into per-worker
   worklists using dynamic page distribution (atomic counter), then
   merges.

Shared Infrastructure
---------------------

**Chase-Lev work-stealing deque** (``pycore_ws_deque.h``).  Each worker
has a local deque.  Owner operations (push/take from bottom) are
lock-free LIFO for cache locality.  Steal operations (take from top) use
lock-free CAS for fairness.  Pre-allocated 2 MB backing buffers (256K
pointer entries) avoid allocation during GC.

**Local work buffer** (``_PyGCLocalBuffer``, 1024 entries).  Staging
area between ``tp_traverse`` callbacks and the deque.  Zero memory
fences for push/pop.  Half-flushed to the deque on overflow (38% faster
than full flush).  Batch-refilled from deque or stolen from other
workers.

**Barrier synchronisation** (``pycore_gc_barrier.h``).  Epoch-based
counting barrier using ``PyMUTEX_T`` / ``PyCOND_T``.  Prevents spurious
wakeup bugs.  Shared by both builds.

**Coordinator-based termination** (GIL build, ``mark_alive`` phase).
When a worker exhausts local work and fails to steal, it attempts to
become the coordinator via mutex election.  The coordinator polls all
deques, wakes idle workers via counting semaphore if work exists, or
signals termination if all deques are empty.  This avoids false
termination (exiting while work remains) and wasted spins.

Worker Thread Lifecycle
-----------------------

Workers are OS threads created via ``PyThread_start_joinable_thread``.
Each worker is provisioned with a ``PyThreadState`` -- required because
``tp_traverse`` implementations (e.g., ctypes) may call ``Py_INCREF``,
which needs ``_PyThreadState_GET()`` in debug builds.

Worker ``PyThreadState`` objects are pre-created before stop-the-world
and bound to TLS only (without ``_PyThreadState_Bind``) to avoid
``gilstate`` assertion failures.  Cleanup is performed by the main
thread after join.

Workers park on a barrier between collections (no spinning, no polling).
The persistent pool avoids per-collection thread creation overhead.

Thresholds and Fallback
-----------------------

When parallel GC is enabled, the collector falls back to serial if:

- The split vector has fewer than 2 entries (heap too small for
  meaningful partitioning).
- Workers are not active (not yet started or creation failed).

There is no hardcoded object-count threshold; the split-vector size
naturally reflects heap size.

Recommended minimum heap size for benefit: **500,000 tracked objects**
(based on empirical benchmarks).

Memory Overhead
---------------

- Per-worker: 2 MB pre-allocated deque buffer (256K pointer entries).
- Per-collection: split vector grows dynamically (8 bytes per 8192
  objects, approximately 1 KB per million objects).
- Work queue (GIL build, producer-consumer): 8 pre-allocated blocks of
  4096 pointers (256 KB), growable.


Backwards Compatibility
=======================

**No public API breakage.**  ``gc.collect()``, ``gc.get_stats()``,
``gc.callbacks``, ``gc.freeze()``, ``gc.unfreeze()`` -- all unchanged.

**Serial fallback is always available.**  If ``gc.enable_parallel()`` is
never called, behaviour is identical to upstream CPython.  If
``--with-parallel-gc`` is not passed at build time, the parallel code is
not compiled at all.

**No change to collection semantics.**  The same objects are collected.
Weak reference callbacks and ``__del__`` methods are called from the main
thread in the same serial phase.

**No change to generational thresholds.**  Parallel GC only affects how
the mark phase executes within a collection, not when collections are
triggered.

**tp_traverse contract unchanged.**  Extension modules' ``tp_traverse``
callbacks are called by worker threads, but the GIL prevents other
Python threads from running (GIL build) or the world is stopped (FTP
build), so existing callbacks remain safe.

**No new required environment variables.**  ``PYTHONPARALLELGC`` and
``-X parallel_gc`` are optional convenience mechanisms.


Security Implications
=====================

Thread Safety
-------------

**Atomic operations for marking.**  GIL build marking uses atomic
Fetch-And (single instruction, no retry loops).  FTP build marking uses
relaxed load/store (sufficient during stop-the-world).  Race conditions
on marking are benign: worst case is duplicate traversal, never missed
traversal.  Marking bits transition monotonically (set once, never
re-set).

**ARM memory ordering.**  Acquire fences after successful mark
operations ensure workers see consistent object field values before
traversal.

**Worker thread states** are managed by the main thread to avoid race
conditions during creation and cleanup.

**No new lock ordering constraints.**  Workers do not acquire the GIL or
any interpreter locks.  Barriers are the sole synchronisation mechanism
between workers.

Memory Safety
-------------

**Pre-allocated buffers** reduce allocation during GC, avoiding
allocator re-entrancy.

**Bounds checking** on worker indices, split vector access, and deque
operations.

**Debug-build postconditions** verify list linkage integrity after
parallel operations.

**OOM during deque growth** calls ``Py_FatalError``.  Dropping objects
from the marking worklist would mean missed marks, leading to
use-after-free.  Error propagation would require changes to 12+ call
sites.

Resource Consumption
--------------------

``gc.enable_parallel(num_workers=1024)`` (GIL build maximum) allocates
~2 GB of deque buffers.  This is no worse than equivalent
``threading.Thread`` creation.  The FTP build caps at 64 workers (~128
MB).


Performance Impact
==================

When Parallel GC Helps
----------------------

.. list-table::
   :header-rows: 1
   :widths: 25 15 20 40

   * - Heap Size
     - Workers
     - Typical Speedup
     - Notes
   * - 1M objects
     - 8
     - 1.2--2.3x
     - FTP build, PGO+LTO, collection time
   * - Realistic workload
     - 8
     - -54% to -67% STW
     - Throughput neutral, major pause reduction
   * - Synthetic throughput
     - 8
     - +31% geomean
     - Sustained workload improvement

When Parallel GC Does Not Help
------------------------------

- **Heaps < 100K objects**: Overhead exceeds benefit (0.5--0.9x).
  Thread coordination, atomics, and barrier synchronisation dominate.
- **Linear chain or binary tree topologies**: Limited parallelism in
  graph structure.
- **Automatic gen-0/gen-1 collections**: Overhead of barrier
  synchronisation dominates on very short-lived collections.
- **Break-even region**: ~300K--500K objects (0.9--1.1x, within noise).

Overhead of Enabled-but-Idle Parallel GC
-----------------------------------------

1-worker parallel vs serial: plus or minus 3% (within noise).
Infrastructure overhead is negligible when workers are parked on
barriers.

Collection Speedup by Heap Topology (FTP Build)
------------------------------------------------

Measured on an optimised (PGO+LTO) free-threaded build, 8 workers,
1M objects, Intel Xeon Platinum 8339HC.  Fixed seed (42), 5 iterations
per run, conservative (worst-of-two-runs) numbers.

.. list-table::
   :header-rows: 1
   :widths: 30 15 30

   * - Heap Type
     - Speedup
     - Notes
   * - Chain (linked list)
     - 1.89x
     - Pointer-chasing limits parallelism
   * - Tree (binary)
     - 1.33x
     - Independent subtrees
   * - Wide tree (high fan-out)
     - 1.37x
     - Many independent branches
   * - Graph (random)
     - 2.33x
     - Best case -- varied connectivity
   * - Layered
     - 1.45x
     - Layer dependencies limit scaling
   * - Independent (disconnected)
     - 1.23x
     - No cross-references
   * - AI workload (tensor clusters)
     - 1.43x
     - Realistic mixed structure
   * - Web server (sessions)
     - 1.32x
     - Realistic session-based

Run-to-run variance is significant on some heap types (CV 14--23%) due
to cache and NUMA effects.

AI/ML Workload Simulation
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 15 20 20 20 15

   * - Tensors
     - Total Objects
     - Serial (ms)
     - Parallel (ms)
     - Speedup
   * - 50K
     - 300K
     - 96.92
     - 76.03
     - 1.27x
   * - 200K
     - 1.2M
     - 518.82
     - 391.08
     - 1.33x


Rejected Alternatives
=====================

1. Parallel Cleanup / Deallocation Workers (FTP)
-------------------------------------------------

Parallelise the deallocation phase using ``cleanup_workers=N``.

**Result**: 13x slowdown due to contention on biased reference counting
(BRC) bucket mutexes.  When multiple workers decref objects owned by a
concentrated set of threads, BRC queues serialise.  Atomic CAS loops on
``ob_ref_shared`` exhibit severe cache-line contention (80.73% of time
on ``lock xaddq``).

**Conclusion**: Deallocation in FTP is fundamentally serial due to BRC
ownership semantics.

2. BRC Sharding to Reduce Cleanup Contention
----------------------------------------------

Shard BRC buckets by decrefing thread ID.

**Result**: Reduces queueing contention but the deeper bottleneck
(atomic CAS on ``ob_ref_shared``) remains.  Abandoned as an incomplete
solution.

3. Fast Decref Optimisation (Py_BRC_FAST_DECREF)
--------------------------------------------------

Use atomic ADD instead of CAS loop for non-queued decrefs.

**Result**: No measurable benefit in realistic workloads.  Cache-line
contention remains the bottleneck regardless of instruction choice.
Code removed.

4. Work-Stealing for Root Propagation (GIL Build)
---------------------------------------------------

Distribute ~100 interpreter roots to worker deques and use
work-stealing.

**Result**: Hub-structured root graph causes severe imbalance: the first
worker marks most of the heap before others can steal (99% measured
empirically).  Replaced with pipelined producer-consumer: main thread
expands roots by one level (thousands of level-1 children) and workers
claim batches from a shared queue.

5. Multi-Threaded Delete Phase (FTP)
-------------------------------------

Run ``tp_clear`` / deallocation across multiple workers.

**Result**: Mimalloc inter-thread communication cost too high.  Objects
must be returned to their owning thread's heap, causing cross-thread
traffic that negates parallelism gains.

6. CAS-Based Atomic Marking
-----------------------------

Use compare-and-swap loops for object marking.

**Result**: Under contention, CAS retry loops waste cycles.  Replaced
with single-instruction Fetch-And (GIL build) and relaxed load/store
(FTP build, sufficient during stop-the-world).  No retry loop needed.

7. Ad-Hoc Thread Creation per Collection
------------------------------------------

Spawn fresh threads for each GC collection.

**Result**: Thread creation overhead (50--200 us per thread on Linux) is
significant relative to collection time for moderate heaps.  Replaced
with persistent thread pool: threads created once, parked on barriers
between collections.


Reference Implementation
=========================

The reference implementation is available at:

- **CPython fork**: https://github.com/SonicField/cpython
  (branch: ``parallel-gc-dev``)
- **Project repository**: https://github.com/SonicField/parallel_gc

Key files (GIL build):

- ``Python/gc_parallel.c`` -- parallel mark, subtract_refs, mark_alive
- ``Include/internal/pycore_gc_parallel.h`` -- data structures, API
- ``Python/gc.c`` -- integration points (``update_refs_with_splits``,
  parallel calls in ``deduce_unreachable``)

Key files (FTP build):

- ``Python/gc_free_threading_parallel.c`` -- page-based parallel GC
- ``Include/internal/pycore_gc_ft_parallel.h`` -- data structures, API

Key files (shared):

- ``Include/internal/pycore_ws_deque.h`` -- Chase-Lev work-stealing deque
- ``Include/internal/pycore_gc_barrier.h`` -- barrier synchronisation
- ``Modules/gcmodule.c`` -- Python API

Test suites:

- ``Lib/test/test_gc_parallel.py`` -- FTP end-to-end (35 tests)
- ``Lib/test/test_gc_ft_parallel.py`` -- FTP internals
- ``Lib/test/test_gc_parallel_mark_alive.py`` -- GIL root marking
  (22 tests)
- ``Lib/test/test_gc_ws_deque.py`` -- Chase-Lev deque (11 tests)
- ``Lib/test/test_gc_parallel_properties.py`` -- property-based
  invariant tests (16 tests)

Design heritage: the Chase-Lev deque and barrier implementations are
ported from CinderX [3]_, Meta's performance-oriented fork of CPython.
The algorithm has evolved substantially: multi-phase architecture,
pipelined producer-consumer root expansion, split-vector work
distribution, and the full FTP implementation are new.
``pycore_ws_deque.h`` and ``pycore_gc_barrier.h`` carry Meta copyright
headers.


Open Issues
===========

- **Default activation policy**: Should parallel GC auto-enable above a
  certain heap size, or remain strictly opt-in?

- **Worker count default**: Should ``num_workers`` default to
  ``os.cpu_count() // 2`` or require explicit specification?

- **Interaction with subinterpreters**: Each interpreter has its own
  parallel GC state.  No cross-interpreter sharing of workers.  Shutdown
  ordering has been validated but edge cases may remain.

- **Platform support**: Development and testing has been on Linux
  x86_64 only.  ARM, macOS, and Windows builds have not been tested.
  The implementation uses CPython's portable atomic wrappers and
  ``PyThread_start_joinable_thread`` (available since 3.12), but
  platform-specific issues with memory ordering or thread primitives
  may exist.

- **Meta copyright**: ``pycore_ws_deque.h`` and ``pycore_gc_barrier.h``
  carry Meta copyright from the CinderX port.  This requires resolution
  before upstream submission.

- **Sweep parallelisation**: The sweep phase is serial in both builds.
  It could be parallelised for large heaps as a follow-on.


References
==========

.. [1] Chase, D. and Lev, Y., "Dynamic Circular Work-Stealing Deque",
   SPAA 2005. https://dl.acm.org/doi/10.1145/1073970.1073974

.. [2] Le, N.M., Pop, A., Cohen, A., and Zappa Nardelli, F., "Correct
   and Efficient Work-Stealing for Weak Memory Models", PPoPP 2013.
   https://dl.acm.org/doi/10.1145/2442516.2442524

.. [3] CinderX, Meta's performance-oriented CPython fork.
   https://github.com/facebookincubator/cinder


Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal licence, at the option of the reader.
