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

Optimized AArch64 measurements show useful large-heap regions in both build
modes, together with neutral and negative regions that constrain the claim.
The complete results and their limitations are described in `Performance
Impact`_.

Five experimental functions are added to the public ``gc`` module, although
``collect_async()`` is orthogonal to whether parallel mode is enabled. Existing
``gc`` APIs and reference-counting behaviour are intended to remain unchanged.


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
- Changes to collection frequency or generation policy do not parallelise the
  work that remains in a large collection.


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

**Atomic marking.**  In both authoritative reachability passes, Fetch-And
claims an object for traversal without a CAS retry loop. The GIL build clears
COLLECTING; free-threaded ``MARK_HEAP`` clears UNREACHABLE. Free-threaded
known-root pre-marking is a separate, duplicate-tolerant optimization and uses
relaxed idempotent bit updates.

**GIL local work buffers.**  The GIL path uses a 1024-item local buffer between
``tp_traverse`` callbacks and the deque. Push/pop requires no atomic operation;
the deque is touched on overflow and underflow. The free-threaded path pushes
directly to its deque so work is available for stealing.

**Targeted dispatch.**  Idle helpers park on per-worker condition variables.
Each dispatch wakes only the selected active helpers and waits on a shared
completion condition. An epoch barrier is used for GIL worker startup.

**Serial paths.**  If parallel GC is not enabled, the normal serial collector
runs. The GIL collector also retains the complete serial path below 16,384
candidates. Per-phase fallback behavior differs by build and is specified
below.

Why two implementations?
------------------------

The GIL and free-threaded builds have fundamentally different object
layouts and memory subsystems, requiring different marking strategies and
work distribution mechanisms.

**GIL build** (``gc_parallel.c``): Uses the ``_gc_prev`` COLLECTING bit
for marking via Fetch-And.  Split vector recorded during serial
``update_refs`` for work distribution. Phases: ``update_refs`` and candidate
count (serial) -> small-collection serial path or interpreter-root pre-mark
(parallel) -> ``subtract_refs`` (parallel) -> reachability marking (parallel)
-> list reconstruction, finalisation, and deallocation (serial).

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

Five new functions are added to the ``gc`` module::

    import gc

    # Enable parallel GC with adaptive worker selection
    gc.enable_parallel()

    # Disable parallel GC (stops worker threads and reverts to serial)
    gc.disable_parallel()

    # Query configuration
    config = gc.get_parallel_config()
    # Returns: {'available': True, 'enabled': True, 'num_workers': 16, ...}

    # Query implementation diagnostics and private phase timings
    stats = gc.get_parallel_stats()

    # Schedule the normal collector and return without waiting
    gc.collect_async()

``gc.enable_parallel()`` creates a pool with an implementation maximum of 16
workers. A GIL build uses helpers while the collecting thread coordinates
them. In a free-threaded build, the collecting thread is worker 0 and the pool
creates 15 helpers. The controller selects the active count for each
collection.

Calling ``gc.enable_parallel()`` while already enabled is a no-op.

``gc.disable_parallel()`` stops the GIL helpers but retains that pool; the
free-threaded implementation joins helpers and destroys its pool.
After disabling, ``gc.get_parallel_config()`` therefore continues to report a
16-worker pool in the GIL build and reports zero workers in the free-threaded
build. In both cases ``enabled`` is false.

If parallel GC was not compiled (``--with-parallel-gc`` not passed),
``gc.enable_parallel()`` and ``gc.disable_parallel()`` raise ``RuntimeError``.
``gc.get_parallel_config()`` returns ``{'available': False, ...}``.

``gc.get_parallel_stats()`` returns build-specific work-distribution counters
and phase timings. ``gc.collect_async()`` is a non-blocking scheduling hint; it
does not enable parallel collection and is an independent API decision for
core review.

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
    _PyGC_ParallelSubtractRefs(interp, containers)
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
``Python/gc.c``. The serial ``update_refs`` is replaced by
``update_refs_with_splits()``, which also counts candidates. Collections below
the threshold return through the existing serial subtraction and reachability
path. Larger collections perform known-root pre-marking, parallel subtraction,
parallel residual marking, and serial list reconstruction.

**Phase 0: update_refs (serial, with split recording).** Walks the GC
list and sets ``gc_refs = ob_refcnt`` for every object.  Simultaneously
records split points -- pointers into the GC list at
``_PyGC_SPLIT_INTERVAL`` (8192) object intervals -- into a growable
``_PyGCSplitVector``.  The split vector enables O(1) parallel
partitioning without an extra list traversal.

The exact candidate count is compared with
``_PyGC_MIN_PARALLEL_CANDIDATES`` (16,384). Below it, no helper is dispatched
and no sample is supplied to the adaptive controller.

**Phase 1: interpreter-root pre-marking (parallel).** The collecting thread
expands known interpreter roots by one level into a shared block queue. Workers
claim batches of 64 roots and traverse through 1024-entry local buffers and
private deques. Expanding the initial roots exposes more independent subtrees
than assigning a small number of hub roots directly. Workers do not steal in
this phase. Before completion, every local buffer and private deque must be
empty because they hold borrowed pointers and are reused by later collections.
Allocation or dispatch failure uses the serial root-mark path.

**Phase 2: subtract_refs (parallel).** Decrements ``gc_refs`` for
internal references.  Each worker is assigned a contiguous range of
split-vector entries. The parallel visitor uses atomic operations because
references cross segment boundaries; the serial visitor remains non-atomic::

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

``_PyGC_VisitStackRef()`` recognizes both visitor identities and skips borrowed
or embedded stack references, whose counts are not represented in
``Py_REFCNT``.

**Phase 3: mark (parallel).**  Workers scan their split-vector segments
for roots (objects with nonzero ``gc_refs``), mark them, and traverse each
discovered subgraph locally -- no work-stealing.  This affects load balance,
not the requirement that every discovered root be fully traversed.

**Phase 4: list reconstruction (serial).** The collecting thread walks the GC
list. Objects with the COLLECTING flag still set are moved to the unreachable
list; reachable objects have ``_gc_prev`` restored as doubly-linked list
pointers. A single owner preserves list ordering and avoids a second merge
protocol. Weak references, finalizers, resurrection handling, and deletion
then use the upstream serial machinery.

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
object for traversal. The earlier ``ALIVE`` root-propagation pass uses a
relaxed byte load and store. Two workers may both traverse the same object in
that optimization pass; this is safe because the mark is idempotent and the
later reference-difference algorithm remains authoritative.

**Phases:**

1. ``mark_alive`` pre-marks objects reachable from known interpreter roots
   using the persistent pool, with a serial fallback. It is skipped when
   ``gc.freeze()`` is active and is never the correctness authority.
2. Non-empty mimalloc pages from thread heaps and the abandoned-page pool are
   assigned to worker buckets. Normal pages are grouped for locality; huge
   pages are spread round-robin.
3. ``update_refs`` computes reference-count differences in parallel. A barrier
   separates page initialization from reference subtraction so no cross-page
   edge is processed before its target state is initialized. Bucket-assignment
   failure can use the serial heap visitor; failure after parallel mutation has
   begun aborts the collection.
4. Thread stacks are scanned serially to account for deferred references.
5. ``MARK_HEAP`` finds roots (positive adjusted counts, plus deferred-reference
   safety roots) and marks reachable objects in parallel. Workers own their
   deques LIFO for locality and steal FIFO for balance. A successful atomic
   clear assigns exactly one owner to each newly reached object.
6. ``scan_heap`` restores reachable object state and accumulates unreachable
   objects, legacy finalizers, live counts, and unique IDs in private worker
   results, which the collecting thread merges. Shutdown retains the serial
   path because disabling deferred reference counting has different locking
   requirements.

These phases run in the first stopped-world section. The collector then resumes
application threads for queued decrefs, weak-reference callbacks, and
finalizers; stops the world again for resurrection, weak-reference, and
free-list work; resumes it; and performs final ``tp_clear`` deletion serially.
The distinction is relevant to both the speed limit and the interpretation of
callback-to-callback latency.

Shared Infrastructure
---------------------

**Chase-Lev work-stealing deque** (``pycore_ws_deque.h``). Each worker
has a local deque.  Owner operations (push/take from bottom) are
lock-free LIFO for cache locality.  Steal operations (take from top) use
lock-free CAS for fairness. The standalone deque starts with 4096 pointer
entries; collector workers normally provide a preallocated 256K-entry backing
region (about 2 MiB on a 64-bit build) and can grow further. Allocation failure
is propagated to the collector.

**GIL local work buffer** (``_PyGCLocalBuffer``, 1024 entries). Staging area
between ``tp_traverse`` callbacks and the deque. Push/pop requires no atomic
operation. It is half-flushed to the deque on overflow and batch-refilled from
the same worker's deque. The active free-threaded path uses its deques directly.

**Synchronization**. Idle helpers park on per-worker condition variables;
the collecting thread waits for helper completion on a separate condition.
The epoch-based barrier in ``pycore_gc_barrier.h`` is used for the GIL startup
handshake and for multi-stage free-threaded work such as ``update_refs``. It is
resized to the active participant count for each dispatch.

**Termination.** The active GIL marking paths drain each worker's local buffer
and complete private deque without stealing. The shared pre-mark queue must
also be exhausted. Free-threaded ``MARK_HEAP`` drains local deques, steals from
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

For forks made through CPython's supported fork protocol, the parent retains
its existing helpers and adaptive history. The child replaces inherited worker
and synchronization state, creates new helpers, and resets adaptive learning
to the four-worker starting point. A collection inherited through a finalizer
fork completes without training the child's reset controller. Raw ``fork()``
calls that bypass CPython's protocol are outside this guarantee.

The free-threaded pool's helper-argument allocation is currently file-static,
matching the original implementation. The detailed lifecycle design and tests
are maintained in ``docs/FORK_ARCHITECTURE.md`` in the project repository.

Thresholds and Fallback
-----------------------

The GIL implementation records a split-vector waypoint every 8192 candidate
objects and uses the serial collector below two complete slices (16,384
candidates). Above that threshold, the interval controls list partitioning; it
does not select or cap the active worker count. The free-threaded implementation
has no corresponding small-collection threshold.

The GIL build uses serial code when the feature is disabled, workers are not
active, the collection is below threshold, split-vector work is unavailable,
or a dispatch cannot run. In the free-threaded build, page-assignment failure
uses the serial heap path. A failure after parallel ``update_refs`` mutation or
during parallel marking aborts the collection through its documented cleanup
path. Shutdown uses serial ``scan_heap``. Worker allocation or creation failure
fails ``gc.enable_parallel()`` rather than silently changing the configured
design.

Worker Selection
----------------

The fixed count of 16 is an upper bound. Both implementations use the same
stochastic random-walk controller. The active count starts at 4. The first
valid collection establishes a baseline. At an accepted count, each subsequent
collection refreshes that baseline and has a 20% chance of trying an unbiased
adjacent count. The next valid collection keeps a lower-cost trial and
otherwise restores the prior count. The accepted count persists across
collections and remains within 2 through 16.

The private measured interval extends from each implementation's internal
collection start point through the serial post-delete cleanup boundary, rather
than timing helper execution alone. Both builds pass elapsed nanoseconds and
their exact candidate count to the same shared normalization function.
Sub-threshold GIL collections do not update the controller.

Memory Overhead
---------------

- Per-worker: a normally preallocated 256K-pointer deque backing region (about
  2 MiB on a 64-bit build), growing if required, plus a 1024-pointer local
  buffer in the GIL implementation.
- Per-collection: split vector grows dynamically (8 bytes per 8192
  objects, approximately 1 KB per million objects).


Backwards Compatibility
=======================

**Existing API compatibility.** ``gc.collect()``, ``gc.get_stats()``,
``gc.callbacks``, ``gc.freeze()``, and ``gc.unfreeze()`` retain their existing
interfaces. This proposal nevertheless adds five public ``gc`` functions.

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

**OOM during deque growth** is propagated without dropping work silently.
Fallback is phase-specific: a failure before parallel mutation can use a serial
equivalent, while a structurally different partially completed operation must
restore the state defined for that phase or abort the collection.

Resource Consumption
--------------------

The implementation caps the pool at 16 workers. Normal collector deque backing
storage is about 2 MiB per worker on a 64-bit build and grows with demand. The
free-threaded build releases its pool in ``gc.disable_parallel()``; the GIL
build stops its helpers but retains the pool for restart.


Performance Impact
==================

Current Evidence
----------------

The current results use optimized PGO+LTO CPython 3.16 builds on a 72-core
AArch64 host. Serial and parallel modes use the same binary; measured runs are
alternated and include raw samples, source state, build flags, CPU affinity,
and NUMA policy.

.. list-table::
   :header-rows: 1

   * - Build
     - Mixed throughput
     - Requested 500K heaps
     - Sustained synthetic workloads
   * - GIL
     - -0.2%
     - all 8 faster; 1.26x GM
     - +9.5% throughput GM
   * - Free-threaded
     - +19.5%
     - all 8 faster; 1.22x GM
     - +2.3% throughput GM

The GIL sustained workloads reduced the mean GC callback interval by 26% in
aggregate. The free-threaded aggregate increased it by 31%, including a
finalizer-heavy workload at -14.7% throughput and +105% callback interval.
The callback interval covers the complete start/stop callback span; in the
free-threaded collector it is not a strict stop-the-world measurement. A
diagnostic run found the negative case dominated by upstream serial
finalization and deallocation, but this remains a hypothesis for further
measurement rather than a universal explanation.

These results demonstrate worthwhile large-heap regions, not universal
speedup or scalability. The GIL run records the pre-commit worktree later
recorded as the reference implementation revision; the free-threaded run
records that revision directly. Clean reruns and feature-off optimized controls
remain prerequisites for submission.


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
``cpython`` submodule records fork commit ``84be8d65be`` on branch
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

- **Platform support**: Feature-on development and testing has covered Linux
  AArch64. The standard feature-off CPython GitHub Actions matrix passed on the
  fork. Feature-on Linux x86-64, macOS, and Windows remain to be tested.
  The implementation uses CPython's portable atomic wrappers and
  ``PyThread_start_joinable_thread`` (available since 3.12), but
  platform-specific issues with memory ordering or thread primitives
  may exist.

- **Provenance review**: The CinderX-derived portions still require the normal
  upstream provenance and licensing review.

- **Serial tails**: GIL list reconstruction and both collectors' finalization
  and deletion remain serial. The free-threaded finalizer-heavy negative region
  should be characterized before considering any separate cleanup proposal.


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
