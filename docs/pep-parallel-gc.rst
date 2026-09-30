PEP: XXXX
Title: Parallel Garbage Collection for CPython
Author: Alex Turner
Status: Draft
Type: Standards Track
Requires: 703 (for free-threaded variant)
Python-Version: 3.16
Created: 2026-03-26
Post-History:


Abstract
========

This PEP proposes adding optional parallel garbage collection to
CPython's cyclic garbage collector.  Two implementations are provided:
one for GIL-enabled builds (``gc_parallel.c``) and one for free-threaded
builds (``gc_free_threading_parallel.c``).  Both use persistent worker pools
and shared deque and synchronization primitives; only the GIL implementation
uses the local buffer. Their work distribution and termination strategies
differ.

Parallel GC is opt-in at build time via ``--with-parallel-gc`` and at
runtime via ``gc.enable_parallel()``.  Serial collection
remains the default. The current implementation requires a 64-bit target and
POSIX or Windows threads.

No performance result is claimed for the current main-based port. Controlled
measurements of both build modes are a prerequisite for submission.

Three opt-in functions are added to the public ``gc`` module. Existing ``gc``
APIs and reference-counting behaviour are intended to remain unchanged.


Motivation
==========

GC pause times scale linearly with heap size
--------------------------------------------

CPython's cyclic GC is single-threaded.  At 1M+ tracked objects,
full-generation collections take hundreds of milliseconds.  The mark
phase dominates: ``update_refs``, ``subtract_refs``, and
``move_unreachable`` all walk the entire object graph serially.

Potential large-heap workloads
------------------------------

Some AI/ML, graph-processing, and server workloads create large cyclic object
graphs or call ``gc.collect()`` at synchronization points. Such workloads are
a motivation for evaluation, not evidence of a production benefit.

Free-threaded Python changes the trade-off
------------------------------------------

Without the GIL (PEP 703), application threads can allocate concurrently, but
cyclic collection still includes stop-the-world work.  Whether parallel GC
improves a given free-threaded workload depends on its heap and collection
behavior.

Modern hardware has idle cores during GC
-----------------------------------------

During a serial stop-the-world collection, other available CPU cores do not
assist with the collector's graph work.

Existing mitigations are insufficient
--------------------------------------

- ``gc.disable()`` risks unbounded memory growth from reference cycles.
- Generational collection reduces frequency but not worst-case pause
  duration for full collections.
- Incremental GC (3.14+) reduces pause latency but does not reduce total
  GC work for manual ``gc.collect()`` calls.


Rationale
=========

Why parallel marking?
---------------------

The mark and supporting whole-heap phases can dominate collection cost for
large heaps.  Some graph topologies expose independent traversal work that can
be divided among workers, although shared objects and uneven subgraphs still
require coordination and load balancing.

This proposal leaves finalisation and deallocation serial (weak-reference
callbacks, ``__del__`` methods, and ``tp_clear``).  Development attempts to
parallelise cleanup were rejected for this implementation (see
`Rejected Alternatives`_).

Why this approach?
------------------

**Persistent thread pool.**  Workers are created once at
``gc.enable_parallel()`` and reused across collections. This avoids
per-collection thread creation overhead.

**Chase-Lev deques.** Each worker has a local deque for discovered objects.
Free-threaded ``MARK_HEAP`` uses stealing for load balancing; the active GIL
paths use the same deque primitive for local work but do not steal.
The implementation is based on Chase & Lev 2005 [1]_ with Le et al. 2013 [2]_
weak-memory corrections.

**Atomic marking.**  In both builds, Fetch-And claims an object for traversal
without a CAS retry loop. The GIL build clears COLLECTING; free-threaded
``MARK_HEAP`` clears UNREACHABLE.

**GIL local work buffers.**  The GIL path uses a 1024-item local buffer between
``tp_traverse`` callbacks and the deque. Push/pop requires no atomic operation;
the deque is touched on overflow and underflow. The free-threaded path pushes
directly to its deque so work is available for stealing.

**Targeted dispatch.**  Idle helpers park on per-worker condition variables.
Each dispatch wakes only the selected active helpers and waits on a shared
completion condition. An epoch barrier is used for GIL worker startup.

**Serial paths.**  If parallel GC is not enabled, the normal serial collector
runs. Per-phase fallback behavior differs by build and is specified below;
there is currently no effective benefit-based heap-size gate.

Why two implementations?
------------------------

The GIL and free-threaded builds have fundamentally different object
layouts and memory subsystems, requiring different marking strategies and
work distribution mechanisms.

**GIL build** (``gc_parallel.c``): Uses the ``_gc_prev`` COLLECTING bit
for marking via Fetch-And.  Split vector recorded during serial
``update_refs`` for work distribution.  Phases: interpreter-root marking
(parallel) -> ``update_refs`` (serial) -> ``subtract_refs`` (parallel) ->
reachability marking (parallel) -> sweep, finalisation, and deallocation
(serial).

**Free-threaded build** (``gc_free_threading_parallel.c``): Uses
``ob_gc_bits`` for marking via Fetch-And. Page-based distribution via mimalloc
internals. Root propagation, ``update_refs``, ``MARK_HEAP``, and ``scan_heap``
run through the persistent pool, with serial fallbacks where provided by the
original design.


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

Three new functions are added to the ``gc`` module::

    import gc

    # Enable parallel GC with adaptive worker selection
    gc.enable_parallel()

    # Disable parallel GC (stops worker threads and reverts to serial)
    gc.disable_parallel()

    # Query configuration
    config = gc.get_parallel_config()
    # Returns: {'available': True, 'enabled': True, 'num_workers': 16, ...}

``gc.enable_parallel()`` creates a pool with an implementation maximum of 16
workers. A GIL build uses helpers while the collecting thread coordinates
them. In a free-threaded build, the collecting thread is worker 0 and the pool
creates 15 helpers. The controller selects the active count for each
collection.

Calling ``gc.enable_parallel()`` while already enabled is a no-op.

``gc.disable_parallel()`` stops the GIL helpers but retains that pool; the
free-threaded implementation joins helpers and destroys its pool.
``gc.get_parallel_config()`` reports zero configured workers while disabled.

If parallel GC was not compiled (``--with-parallel-gc`` not passed),
``gc.enable_parallel()`` and ``gc.disable_parallel()`` raise ``RuntimeError``.
``gc.get_parallel_config()`` returns ``{'available': False, ...}``.

Startup Configuration
---------------------

There is no environment-variable, ``-X``, or ``PyConfig`` startup interface.
Parallel collection is enabled explicitly through the ``gc`` module API.

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
    _PyGC_ParallelSubtractRefs(interp)
    _PyGC_ParallelMarkAliveFromRoots(interp, containers)
    _PyGC_ParallelMarkAliveFromQueue(interp, containers)

Free-threaded build::

    _PyGC_ThreadPoolInit(interp, num_workers)
    _PyGC_ThreadPoolFini(interp)
    _PyGC_AssignPagesToBuckets(interp, state)
    _PyGC_FreeBuckets(state)
    _PyGC_ParallelPropagateAliveWithPool(interp, roots, num_roots, num_workers)
    _PyGC_ParallelUpdateRefsWithPool(interp, state)
    _PyGC_ParallelMarkHeapWithPool(interp, state, skip_deferred_objects)
    _PyGC_ParallelScanHeapWithPool(interp, state, result)

GIL Build: Multi-Phase Architecture
------------------------------------

The parallel collector hooks into ``deduce_unreachable()`` in
``Python/gc.c``.  After parallel interpreter-root marking, the serial
``update_refs`` is replaced by ``update_refs_with_splits()``, followed by
parallel subtraction and reachability marking. Serial fallbacks remain for
dispatches that cannot use the pool.

**Phase 0: interpreter-root marking (parallel).** Expands known interpreter
roots into a shared queue and dispatches the active worker set to mark their
reachable subgraphs. Allocation or dispatch failure uses the serial root-mark
path.

**Phase 1: update_refs (serial, with split recording).**  Walks the GC
list and sets ``gc_refs = ob_refcnt`` for every object.  Simultaneously
records split points -- pointers into the GC list at
``_PyGC_SPLIT_INTERVAL`` (8192) object intervals -- into a growable
``_PyGCSplitVector``.  The split vector enables O(1) parallel
partitioning without an extra list traversal.

**Phase 2: subtract_refs (parallel).**  Decrements ``gc_refs`` for
internal references.  Each worker is assigned a contiguous range of
split-vector entries.  Serial and parallel traversal use the same callback;
in a parallel-GC build it uses atomic operations because references cross
segment boundaries::

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

The shared callback identity also lets ``_PyGC_VisitStackRef()`` skip borrowed
or embedded stack references, whose counts are not represented in
``Py_REFCNT``.

**Phase 3: mark (parallel).**  Workers scan their split-vector segments
for roots (objects with nonzero ``gc_refs``), mark them, and traverse each
discovered subgraph locally -- no work-stealing.  This affects load balance,
not the requirement that every discovered root be fully traversed.

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
        // Fast path: avoid an RMW when the object is already marked
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

The free-threaded parallel GC uses ``ob_gc_bits`` (a ``uint8_t`` on ``PyObject``)
for marking and ``ob_tid`` (repurposed during stop-the-world) for ``gc_refs``
storage. The restored design parallelises root propagation and all three heap
phases before serial finalization and deletion.

**Page-based work distribution.**  Free-threaded Python uses mimalloc for memory
allocation.  Objects live on mimalloc pages, which are natural units of
work distribution.  Pages are enumerated in O(pages) time (not
O(objects)) and assigned to worker buckets: normal pages use sequential
filling for locality; huge pages use round-robin to spread expensive
traversals.

**Atomic marking.** During stop-the-world, mutator threads are paused while the
selected GC participants cooperate. A relaxed load avoids an RMW when the
object is already reachable; Fetch-And gives one worker ownership when clearing
UNREACHABLE::

    static inline int
    _PyGC_TryMarkReachable(PyObject *op)
    {
        if (!(_Py_atomic_load_uint8_relaxed(&op->ob_gc_bits)
              & _PyGC_BITS_UNREACHABLE)) {
            return 0;
        }
        return _PyGC_TryClearBit(op, _PyGC_BITS_UNREACHABLE);
    }

Only the worker that observes the bit set before the atomic clear queues the
object for traversal. The ``ALIVE`` root-propagation pass also uses the
persistent pool when parallel collection is active.

**Phases:**

1. ``mark_alive`` pre-marks objects reachable from interpreter roots using the
   persistent pool, with a serial fallback.
2. ``update_refs`` computes reference-count differences in parallel. A barrier
   separates page initialization from reference subtraction so referents can
   be initialized safely before the compute phase.
3. Pages are assigned to worker buckets, then thread stacks are scanned
   serially to account for deferred references. ``MARK_HEAP`` then finds roots
   (nonzero ``gc_refs``) and marks reachable objects in parallel, using work
   stealing for transitive closure. If page assignment fails, the upstream
   serial ``mark_heap_visitor`` runs instead.
4. ``scan_heap`` uses an atomic page counter for dynamic distribution. Each
   worker restores object state and accumulates private results, which the
   collecting thread merges. Shutdown collection retains the serial path.

Shared Infrastructure
---------------------

**Chase-Lev work-stealing deque** (``pycore_ws_deque.h``).  Each worker
has a local deque.  Owner operations (push/take from bottom) are
lock-free LIFO for cache locality.  Steal operations (take from top) use
lock-free CAS for fairness. Each deque starts with 4096 pointer entries and
grows as required. Allocation failure is propagated to the collector.

**GIL local work buffer** (``_PyGCLocalBuffer``, 1024 entries). Staging area
between ``tp_traverse`` callbacks and the deque. Push/pop requires no atomic
operation. It is half-flushed to the deque on overflow and batch-refilled from
the same worker's deque. The active free-threaded path uses its deques directly.

**Synchronization**. Idle helpers park on per-worker condition variables;
the collecting thread waits for helper completion on a separate condition.
The epoch-based barrier in ``pycore_gc_barrier.h`` is used for the GIL startup
handshake and for multi-stage free-threaded work such as ``update_refs``. It is
resized to the active participant count for each dispatch.

**Termination.** The active GIL marking paths drain each worker's local work
without stealing. Free-threaded ``MARK_HEAP`` drains local deques, steals from
other active workers, and requires repeated idle rounds before a worker exits.
A shared error flag ends unsuccessful work.

Worker Thread Lifecycle
-----------------------

Helpers are OS threads created via ``PyThread_start_joinable_thread``. In the
free-threaded build, worker 0 is the existing collecting thread rather than a
new helper. GIL helpers create and fully bind persistent ``PyThreadState``
objects. Free-threaded helpers also create persistent states, then install the
state and interpreter pointers in thread-local storage while running, without
a full bind. Both arrangements support debug-build reference accounting in
``tp_traverse`` implementations.

Between collections helpers park on per-worker condition variables, without
spinning or polling. The persistent pool avoids per-collection thread creation
overhead.

The restored design does not install special parallel-GC fork hooks. Fork
behavior remains a validation item and no restart or child-disable behavior is
claimed here. The free-threaded pool's helper-argument allocation is currently
file-static, matching the original implementation.

Thresholds and Fallback
-----------------------

The GIL implementation records a split-vector waypoint every 8192 candidate
objects. That interval controls list partitioning only; it does not select or
cap the active worker count. The free-threaded implementation has no matching
8192-object threshold.

The GIL build uses serial code when the feature is disabled, workers are not
active, or a phase has fewer than two work slices. In the
free-threaded build, page-assignment failure uses the serial heap path. A
parallel update or mark error aborts the collection through its documented
cleanup path. Shutdown uses serial ``scan_heap``. Worker allocation or creation
failure fails ``gc.enable_parallel()`` rather than silently changing the
configured design.

Worker Selection
----------------

The fixed count of 16 is an upper bound. Both implementations use the same
stochastic hill-climbing controller. It occasionally tries an adjacent worker
count, measures the next collection's cost per candidate, keeps an improvement,
and otherwise restores the previous count. The active count starts at 4 and is
bounded to the inclusive range 2 through 16.

Memory Overhead
---------------

- Per-worker: an initial 4096-pointer deque (32 KiB on 64-bit builds), growing
  with the reachable frontier.
- Per-collection: split vector grows dynamically (8 bytes per 8192
  objects, approximately 1 KB per million objects).


Backwards Compatibility
=======================

**Existing API compatibility.** ``gc.collect()``, ``gc.get_stats()``,
``gc.callbacks``, ``gc.freeze()``, and ``gc.unfreeze()`` retain their existing
interfaces. This proposal nevertheless adds three public ``gc`` functions.

**Serial fallback is always available.**  If ``gc.enable_parallel()`` is
never called, behaviour is identical to upstream CPython.  If
``--with-parallel-gc`` is not passed at build time, the parallel code is
not compiled at all.

**Semantic equivalence is required.** Parallel GC must identify the same
reachable and unreachable objects as serial GC. Traversal and worklist order
are not guaranteed. Weak-reference callbacks and ``__del__`` methods remain on
the collecting thread in serial phases.

**No change to generational thresholds.** Parallel GC changes which threads
execute selected collector phases; it does not change when collections are
triggered.

**``tp_traverse`` execution context.** Extension callbacks are invoked by GC
helper threads while mutators are excluded by the GIL or stop-the-world
mechanism. GIL helpers use fully bound persistent thread states. Free-threaded
helpers install pre-created states in TLS without full binding. This distinction
is a central correctness and lifecycle invariant and should be reviewed
explicitly.

**No startup controls.** Parallel GC adds no environment variable, ``-X``
option, or ``PyConfig`` field.


Security Implications
=====================

Thread Safety
-------------

**Atomic operations for marking.** Both builds use atomic Fetch-And (single
instruction, no retry loop) to claim traversal ownership. The free-threaded
operation clears the UNREACHABLE bit during ``MARK_HEAP``. This monotonic bit
transition and its interaction with the other object-bit fields remain an
explicit memory-model review item.

**ARM memory ordering.** The GIL marking path uses an acquire fence after a
successful claim; the free-threaded path uses CPython's sequentially consistent
``_Py_atomic_and_uint8`` wrapper. The AArch64 functional tests exercise these
paths, but the ordering argument still requires review; a passing test run is
not a proof of the memory model.

**Worker thread state.** GIL helpers bind persistent ``PyThreadState`` objects;
free-threaded helpers install persistent states in TLS without full binding.
Creation and teardown order are part of the lifecycle audit.

**Synchronization.** Workers do not acquire the GIL, but the implementation
does introduce mutexes, condition variables, atomics, and deque protocols.
Lock-ordering and callback interactions require explicit review.

Memory Safety
-------------

**Pre-allocated buffers** reduce allocation during GC, avoiding
allocator re-entrancy.

**Bounds checking.** Worker indices, split-vector access, and deque operations
have local checks and assertions. Their completeness is part of the
correctness audit.

**Debug-build postconditions** verify list linkage integrity after
parallel operations.

**OOM during deque growth** is propagated without dropping work silently. The
GIL collector restores its marking flags and uses the serial traversal. The
free-threaded collector restores reference counts and aborts that collection
through the existing error path.

Resource Consumption
--------------------

The implementation caps the pool at 16 workers. Initial deque storage is about
32 KiB per worker on a 64-bit build and grows with demand. The free-threaded
build releases its pool in ``gc.disable_parallel()``; the GIL build stops its
helpers but retains the pool for restart.


Performance Impact
==================

Current Evidence
----------------

The current main-based port has correctness results on Linux AArch64, but no
submission-quality performance result yet. The benchmark protocol requires
separate optimized GIL and free-threaded builds, alternating serial and
parallel samples, raw data, source revisions, build flags, CPU affinity, and
machine metadata. Until those runs exist, this PEP makes no break-even,
latency, throughput, or scalability claim.


Rejected Alternatives
=====================

1. Parallel Cleanup / Deallocation Workers (Free-Threaded)
-----------------------------------------------------------

Parallelise the deallocation phase using ``cleanup_workers=N``.

Cleanup remains serial in the initial proposal. Parallel cleanup would widen
the semantic and review surface and requires independent evidence.

2. BRC Sharding to Reduce Cleanup Contention
----------------------------------------------

Shard BRC buckets by decrefing thread ID.

This is outside the scope of the initial marking proposal.

3. Fast Decref Optimisation (Py_BRC_FAST_DECREF)
--------------------------------------------------

Use atomic ADD instead of CAS loop for non-queued decrefs.

This is outside the scope of the initial marking proposal.

4. Multi-Threaded Delete Phase (Free-Threaded)
-----------------------------------------------

Run ``tp_clear`` / deallocation across multiple workers.

This would require a separate ownership, finalization, and allocator-safety
design. It is not included here.

5. CAS-Based Atomic Marking
-----------------------------

Use compare-and-swap loops for object marking.

The implementation uses monotonic atomic bit clearing, which also determines
which worker owns traversal of a newly reached object.

6. Ad-Hoc Thread Creation per Collection
------------------------------------------

Spawn fresh threads for each GC collection.

The implementation uses persistent pools so collection does not depend on
creating threads while the collector owns its global synchronization.


Reference Implementation
=========================

The project repository is https://github.com/SonicField/parallel_gc. Its
``cpython`` submodule records fork commit ``323d3cc90a`` on branch
``SonicField/cpython:parallel-gc-upstream-port``, based on ``python/cpython``
commit ``333071231d``. No proposal has yet been made to ``python/cpython``.

Key files (GIL build):

- ``Python/gc_parallel.c`` -- parallel root marking, subtract_refs, and
  reachability marking
- ``Include/internal/pycore_gc_parallel.h`` -- data structures, API
- ``Python/gc.c`` -- integration points (``update_refs_with_splits``,
  parallel calls in ``deduce_unreachable``)

Key files (free-threaded build):

- ``Python/gc_free_threading_parallel.c`` -- page assignment, parallel root,
  ``update_refs``, ``mark_heap``, and ``scan_heap`` phases, and worker pool
- ``Include/internal/pycore_gc_ft_parallel.h`` -- data structures, API
- ``Python/gc_free_threading.c`` -- integration and serial fallbacks for all
  four parallel free-threaded phases

Key files (shared):

- ``Include/internal/pycore_ws_deque.h`` -- Chase-Lev work-stealing deque
- ``Include/internal/pycore_gc_barrier.h`` -- barrier synchronisation
- ``Modules/gcmodule.c`` -- Python API

Test suites:

- ``Lib/test/test_gc_parallel.py`` -- end-to-end API tests
- ``Lib/test/test_gc_ft_parallel.py`` -- free-threaded internals
- ``Lib/test/test_gc_ws_deque.py`` -- Chase-Lev deque
- ``Lib/test/test_gc_parallel_properties.py`` -- property-based invariant tests

Design heritage: the Chase-Lev deque and barrier implementations derive from
CinderX [3]_, Meta's performance-oriented fork of CPython. The algorithm has
evolved substantially: multi-phase architecture, split-vector work
distribution, and free-threaded integration are new. Provenance and licensing
should be checked as part of the upstream submission.


Open Issues
===========

- **Default activation policy**: Should parallel GC auto-enable above a
  certain heap size, or remain strictly opt-in?

- **Worker ceiling**: Validate the fixed maximum of 16 on the supported
  platforms and representative hardware.

- **Platform support**: Current-port development and testing has covered Linux
  AArch64. Linux x86-64, macOS, and Windows builds have not been tested.
  The implementation uses CPython's portable atomic wrappers and
  ``PyThread_start_joinable_thread`` (available since 3.12), but
  platform-specific issues with memory ordering or thread primitives
  may exist.

- **Provenance review**: The CinderX-derived portions still require the normal
  upstream provenance and licensing review.

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
