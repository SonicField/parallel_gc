PEP: Unassigned (discussion starting point)
Title: Self-Tuning Parallel Cyclic Garbage Collection for CPython
Author: OpenAI Codex (drafting), Alex Turner (guidance)
Status: Discussion draft
Type: Discussion document
Requires: 703 (for the free-threaded implementation)
Python-Version: 3.16
Created: 2026-10-02
Post-History:

.. note::

   This is a starting point for Matt, Pablo and other core developers to
   understand, experiment with and discuss parallel GC. It uses a PEP-like
   structure, but it is not a PEP proposal, a formal submission or a request
   to accept the implementation. No PEP number has been assigned.

   OpenAI Codex, an AI assistant, wrote this document under Alex Turner's
   guidance. The drafting and review use
   `Verifiable Practice <https://github.com/SonicField/verifiable-practice>`_:
   distinguish design goals from observations, identify checks that can expose
   errors, preserve reproducible evidence, and report failures and unknowns.
   AI authorship and use of that method do not establish correctness; the
   source, tests and measurements remain open to independent review.

   The source and evidence were reconciled on 12 October 2026 against CPython
   ``c67363fa59``; this discussion framing was revised on 15 October, with
   documentation navigation and experimental qualifications updated on
   16 October. Collector source was not changed by those documentation edits.
   The `validation record <VALIDATION.md>`_ tracks dated evidence and pending
   publication checks. This document's reconciliation date does not identify
   the source selected by a later checkout; the parent's gitlink does.


Abstract
========

The design goal is to reduce cyclic-GC pauses progressively as the heap
exposes useful parallel work, while preserving collection coverage and tuning
to the workload and available hardware without application intervention beyond
activation. Enabling the feature should impose little cost when parallelism
does not help. The review work suggests numerical criteria in the
`performance document <PERFORMANCE.md>`_; these remain discussion material,
not a limit silently adopted by documentation changes. Current measurements
include regressions.

This document describes an experimental opt-in parallel cyclic collector for
both GIL-enabled and free-threaded CPython. Its compatibility requirement is
to preserve serial GC's collection candidates, reachability decisions and
object-lifecycle semantics, without changing collection triggers or generation
selection. That requirement is not a claim that compatibility has been proved.
Parallel phases execute extension-defined ``tp_traverse`` on helper threads
rather than the collecting thread; extension compatibility remains an open
review item. Weak-reference callbacks, finalization and deletion remain serial.

An application can enable and disable parallel GC repeatedly during one
process. Each enable operation takes no tuning arguments. The application does
not select a worker count or a heap-size threshold. While parallel GC is
enabled, the collector measures completed collections and adjusts the number
of participating workers. The GIL implementation retains a serial path for
collections too small to repay parallel dispatch. The free-threaded
implementation adjusts its active participant count when the normalized
collection cost changes. Idle helpers remain parked.

The following sections describe the design, the measurements taken, the
negative results and the evidence still missing. They are a basis for
engineering discussion, not a claim of readiness to land in CPython.


How to use this starting point
==============================

Start with the `repository README <../README.md>`_ and
`getting-started guide <GETTING_STARTED.md>`_. Clone the complete
``SonicField/parallel_gc`` parent with its submodules, not just the CPython
fork: the parent contains the benchmark laboratory, design records and pinned
source needed to reproduce the work.

Useful first-review questions are whether the phase invariants and lifecycle
contract are sound, what helper-thread traversal means for extension
compatibility, which diagnostics should be public, and how to evaluate the
measured benefits and regressions. The
`open issues <OPEN_ISSUES.md>`_ record unresolved hazards, hypotheses and
performance defects alongside the test evidence.

MUST, SHOULD and MAY below express the intended engineering contract and
design goals. They do not denote requirements approved by CPython, nor assert
that every requirement is implemented or verified. Any eventual formal
proposal needs its own review and agreed API and compatibility commitments.


Motivation
==========

Large cyclic heaps produce long serial collections
--------------------------------------------------

CPython's cyclic collector examines tracked objects and traverses their
references to distinguish reachable objects from unreachable cycles. The work
increases with the number of candidate objects and graph edges, and it runs
while useful application work is stopped.

Changing collection frequency does not divide that work. Disabling cyclic GC
avoids the pause by leaving reference cycles uncollected. Neither response
solves the large-heap collection problem.

The collector must own the tuning problem
------------------------------------------

A parallel collector that requires an application author to choose a thread
count or heap threshold transfers an interpreter implementation problem to the
application. The correct values depend on graph shape, live-object ratio,
memory locality, current hardware, and interference from the rest of the
process. The values also change during one process lifetime.

This design makes activation a policy decision rather than a tuning
exercise. The GIL collector selects serial execution below its internal
crossover. Both collectors adjust active worker counts from completed
collections. The same application can therefore use little parallel capacity
for one workload phase and more capacity for a
later, larger phase.

Parallelism must remain cheap when it does not help
---------------------------------------------------

Parallel dispatch, atomic marking, synchronization, and work distribution all
have costs. Small collections do not contain enough work to amortize those
costs. Some large graph shapes also scale poorly.

The GIL design treats serial execution of small collections as normal. FT
adapts within the parallel participant range and parks unused helpers.
Enabling either collector creates no native thread until a collection first
uses it. These policies limit overhead; they do not guarantee that every
workload benefits.

General interpreter benchmarks do not answer this question
-----------------------------------------------------------

``pyperformance`` remains useful for detecting whole-interpreter regressions.
Most of its workloads do not create controlled cyclic heaps or execute enough
large collections to measure this design. A neutral ``pyperformance`` result
does not show that parallel GC ran, scaled, or preserved pause behaviour.

The project therefore maintains a separate benchmark suite that controls heap
size and topology, alternates serial and parallel runs, records collection
intervals and throughput, and observes worker adaptation. That suite belongs
in the project repository rather than the CPython regression-test tree.


Goals
=====

The design has five goals.

1. Parallel GC MUST examine the same collection candidates and preserve the
   same reachability and object-lifecycle semantics as serial GC.

2. One call to ``gc.enable_parallel()`` MUST be sufficient to activate the
   feature. Applications MUST NOT select worker counts or collection-size
   thresholds.

3. The collector MUST adjust active parallelism from measured collection
   results. The selected count MUST persist across collections so that the
   controller learns from earlier work.

4. The collector MUST retain low-overhead behaviour when a collection cannot
   profit from broad parallelism. The GIL build MAY run that collection on the
   collecting thread. The free-threaded build MAY reduce the active working
   set while leaving unused helpers parked.

5. Large collections that expose parallel work SHOULD complete with shorter
   pauses than the corresponding serial collections on the same interpreter
   and machine.

The review work proposes numerical criteria for "low overhead" in the
`performance document <PERFORMANCE.md>`_. They are not approved by CPython,
and this documentation integration does not itself select a limit. The goal
cannot be reported as satisfied until a limit is agreed and measurements from
the source revision being evaluated meet it. Current measurements include
regressions and do not establish that goal.


Non-Goals
=========

The design does not include any of the following changes:

- a concurrent collector that runs while Python mutator threads continue;
- new generation thresholds or a new collection-trigger policy;
- user-selected GC worker counts;
- user-selected parallelization thresholds;
- parallel execution of weak-reference callbacks, finalizers, or ``tp_clear``;
- a guarantee that every heap topology gains throughput or shorter pauses;
- ``gc.collect_async()`` or any other asynchronous collection API.

The reference branch contains an experimental ``gc.collect_async()`` function.
That function is independent of parallel tracing and is outside this discussion.


Terminology
===========

A *candidate* is one object included in the existing collector's reference
initialization count. GIL counts the selected generation list; FT counts its
eligible heap objects. The count includes live candidates, not just garbage.

The *pool capacity* is the maximum number of collector workers or participants
created or reserved by one interpreter.

The *active participant count* is the number selected for the current
collection. In the free-threaded build, the collecting thread is participant
zero. In the GIL build, the collecting thread coordinates helper workers.

The *normalized collection cost* is the elapsed collection time in nanoseconds
divided by the exact candidate count. A parallel collection with valid elapsed
time and candidates can train the controller even when it reclaims nothing.
Zero-candidate or invalid timing samples do not update it; GIL sub-threshold
collections do not train it.

The *serial path* is the existing single-threaded graph-analysis path for the
selected collection.


Specification
=============

Availability
------------

A distributor enables parallel-GC support with ``--with-parallel-gc``. The
configure option defines ``Py_PARALLEL_GC``. A build without this option does
not compile the parallel collector.

The same option supports both build modes::

    # GIL-enabled build
    ./configure --with-parallel-gc

    # Free-threaded build
    ./configure --with-parallel-gc --disable-gil

The current implementation requires a 64-bit target and CPython's supported
thread primitives. The GIL and free-threaded implementations are mutually
exclusive at compile time.

Runtime activation
------------------

The experimental implementation provides these functions in the ``gc`` module::

    gc.enable_parallel()
    gc.disable_parallel()
    gc.get_parallel_config()
    gc.get_parallel_stats()

``gc.enable_parallel()`` takes no arguments. The function MUST arm the
collector without creating native helper threads. A successful call makes
parallel policy available to a later eligible collection; it does not promise
that the pool has started. Allocation of the GIL's lightweight armed state can
still fail at enable time and raise an exception.

The first eligible GIL collection MUST start its pool after the candidate walk
and before parallel dispatch. FT MUST attempt startup before stopping the
world, because helper thread-state creation can require runtime table growth
that itself stops the world.

IF pool startup fails, THEN the collector MUST cancel partial startup,
reclaim its resources and complete the collection serially. The collector MUST
enter FAILED and make no automatic startup retry. AFTER safe collection
cleanup, the collector MUST attempt one ``RuntimeWarning`` for that request.
A warning-delivery exception MUST NOT replace a successful serial collection
with an exception. An explicit later enable MUST re-arm and permit another
lazy startup attempt. Unchecked join results remain a separate reference
implementation defect requiring an agreed failure policy.

After startup, while parallel GC remains enabled, the interpreter MUST reuse
that worker pool across collections. It MUST NOT create and join helper
threads for each collection. Operating-system thread creation and teardown are
expensive enough
to consume the collection-time saving that parallel GC is intended to provide.
Persistent pooling is therefore a performance requirement, not merely a
lifecycle convenience. Lazy startup avoids the first-thread cost in armed
workloads that never use helpers; the first-use collection pays startup cost.

In a supporting build, when no collection is active, calling
``gc.enable_parallel()`` while parallel GC is enabled is a no-op, and calling
``gc.disable_parallel()`` while it is disabled is a no-op. During an active
collection, either call raises ``RuntimeError``, including a call that would
otherwise be a no-op.

``gc.disable_parallel()`` MUST prevent later collections from dispatching
parallel work. An implementation MAY retain stopped pool storage for a later
restart. Retained storage MUST NOT change the values documented by
``gc.get_parallel_config()``.

IF a build does not contain parallel-GC support, THEN
``gc.enable_parallel()`` and ``gc.disable_parallel()`` MUST raise
``RuntimeError``. In that build, ``gc.get_parallel_config()`` MUST report
``available`` as false and ``enabled`` as false.

Configuration changes MUST be serialized per interpreter. IF a collection is
active, THEN an enable or disable request MUST raise ``RuntimeError``. When an
enable or disable call returns, every state change performed by that call MUST
be visible to the next collection.

The design adds no environment variable, ``-X`` option, ``PyConfig`` field,
or Python argument for selecting a worker count.

Configuration and diagnostic results
------------------------------------

``gc.get_parallel_config()`` returns a dictionary. All builds report
``available``, ``enabled`` and ``num_workers``. Supporting builds also report
``pool_active`` and ``startup_failed``; ``adaptive_workers`` is present only
while parallel GC is enabled. The fields have these meanings:

``available``
    True when the build contains parallel-GC support.

``enabled``
    True when policy is ARMED or ACTIVE. A later eligible collection can
    attempt startup if necessary. False in DISABLED or FAILED.

``num_workers``
    The pool capacity when enabled, or zero when disabled.

``adaptive_workers``
    The current active participant count. This key is present only while
    parallel GC is enabled.

``pool_active``
    True only after a complete helper pool is ready. False while armed.

``startup_failed``
    True in FAILED after a pool-start transaction fails. Explicit enable or
    disable clears this per-request state.

The two state fields above are reported in feature-on builds. Feature-off
builds currently report only ``available``, ``enabled`` and ``num_workers``.

``gc.get_parallel_stats()`` exposes implementation diagnostics used for test
and performance analysis. The GIL and free-threaded collectors report
different phase data. This draft does not define a stable schema for that
dictionary. A formal proposal would need to define a stable schema or make
the function a private diagnostic API. That choice remains open for discussion.

Both current implementations report ``num_workers`` as zero while disabled or
failed, including when the GIL implementation retains reusable storage.
Startup diagnostics include a monotonic failure count and a bounded error
code. The API schema remains subject to review.

The current free-threaded implementation also reports
``parallel_cleanup=True`` even though cleanup is serial. The implementation
must remove that key or give the key a definition that matches executed code.

Adaptive worker selection
-------------------------

Both implementations use the same controller and the same normalized cost.
The current pool capacity is 16. The controller begins at four active
participants and restricts the active count to the inclusive range from two
through 16.

The first eligible collection records a baseline. After each collection at an
accepted count, the controller has a 20 percent probability of selecting one
adjacent count for the next eligible collection. The direction is unbiased.
The controller retains the trial count only when the next collection has a
lower normalized cost than the previous accepted measurement. Otherwise, the
controller restores the previous count.

The accepted count persists until the controller selects and evaluates another
trial. The child after ``fork()`` discards inherited measurements and restarts
at four participants.

The controller does not infer hardware capacity from a CPU-count query. It
observes how completed collections perform on the hardware and under the
contention available to the process. The stochastic adjacent walk does not
guarantee discovery of a global optimum. It provides bounded exploration and
reverses trials that make the measured cost worse.

FT deliberately excludes serial execution from this search. Serial cost can
be discontinuous with the parallel cost curve. For example, serial can beat
two participants while four participants beat both. A local walk that
retreats into serial can fail to cross the worse intermediate parallel count
and never discover four. Excluding serial avoids that particular trap; local
minima and measurement noise within the parallel range remain possible.
This is the reason for the parallel search domain, not a claim that two
participants always beat serial.

GIL execution policy
--------------------

The GIL collector counts candidates while performing the existing serial
``update_refs`` traversal. A collection with fewer than 16,384 candidates
continues through the serial subtraction and reachability path. The collector
does not wake helpers and does not train the worker controller from that
collection.

The value 16,384 is an internal crossover policy, not an application setting.
The implementation records list waypoints every 8,192 candidates for work
partitioning. Two complete partitions form the current crossover point.

For an eligible collection, the collecting thread dispatches the active helper
count selected by the controller. Helpers parallelize known-root traversal,
reference subtraction, and reachability marking. The collecting thread
reconstructs GC lists and executes weak-reference, finalization, resurrection,
and deletion work serially.

Free-threaded execution policy
------------------------------

The free-threaded collector uses the collecting thread as participant zero and
creates up to 15 helper threads. For an enabled collection, only the
controller-selected participants enter parallel phases. The remaining helpers
stay parked.

Participants parallelize reference-count adjustment, heap marking, and heap
scanning. Known-root propagation is also dispatched to the participants, but
its effective parallelism is conditional: on 15 October 2026 a live 1M-object
graph reachable only from module state was traversed almost entirely by one
worker (0.61–0.83x serial at 16 workers), while the same graph reachable from
a frame local scaled to 3.39x
(`scaling review <reviews/2026-10-15-claude-scaling-review.md>`_). The
implementation partitions work by mimalloc page and uses work stealing during
known-root propagation and heap marking. Weak-reference, finalization,
resurrection, and deletion work remains serial.

The free-threaded implementation does not use the GIL implementation's
16,384-candidate serial crossover. It controls overhead by reducing active
participation and by keeping non-participating helpers asleep.

Collection semantics
--------------------

Parallel GC MUST use the generation selected by the existing collector. It
MUST NOT change automatic collection triggers or promotion policy.

For the state immediately before weak-reference and finalization processing,
the parallel and serial paths MUST classify the same candidate objects as
reachable and unreachable. Parallel worklist order and traversal order are not
part of this contract.

Weak-reference callbacks, ``__del__`` methods, resurrection handling, and
``tp_clear`` calls MUST execute on the collecting thread. This design does not
parallelize those operations.

Parallel phases invoke ``tp_traverse`` from helper operating-system threads.
The collecting thread creates persistent ``PyThreadState`` objects for
helpers. GIL helpers bind their states; FT helpers install them in thread-local
storage during work without a full bind. The serial collector invokes
``tp_traverse`` on the collecting thread. This design changes that execution
context. Compatibility evidence for real extension
modules is a requirement for acceptance even if the public C API does not
promise a specific traversal thread.

Worker and process lifecycle
----------------------------

Each interpreter owns its parallel-GC state. Interpreter finalization MUST
stop or invalidate every helper owned by that interpreter before freeing pool
memory.

Before a supported CPython ``fork()``, FT acquires its pool lifecycle lock
before stopping the Python world. This ordering lets a thread holding the lock
finish its transaction. The runtime
verifies that no parallel-GC dispatch is active. The parent's helpers remain
parked; the fork protocol does not replace, stop, or restart them. The parent
retains its pool and adaptive history. The FT parent releases the lifecycle
lock before resuming the world. The child reinitializes the inherited lock.
IF parallel policy was enabled before the fork, THEN the child MUST abandon
inherited helper resources, reset adaptive history and enter ARMED without
creating a thread. A child MUST NOT join a thread that existed only in the
parent. DISABLED and FAILED children MUST preserve those states. A collection
inherited from a callback or finalizer MUST complete serially and MUST NOT
train the child's reset controller. Later eligible work starts a new pool
through the ordinary lazy transaction and failure contract.

Tests for a main-interpreter fork with a live idle legacy subinterpreter are
retained but skipped: feature-off controls also crash in that upstream
scenario. This is a recorded coverage gap, not evidence that the parallel
collector handles the scenario or that all subinterpreter operations fail.

Failure behaviour
-----------------

Workers MUST NOT silently discard traversal work. Every successful parallel
phase MUST either process every item assigned to that phase or make the
collection fail before later phases consume incomplete state.

IF a resource failure occurs before a parallel phase mutates collector state,
THEN the collector MAY execute the corresponding serial phase. A serial
fallback MUST begin from state accepted by the serial implementation.

The source audit records unchecked split-vector growth and free-threaded
unique-ID accumulation. Free-threaded scan rollback is a separate hypothesis
awaiting fault injection, not a reproduced failure. These items require
investigation of failures after partial mutation. This discussion does not
describe the recovery paths as complete. Before the implementation can be
accepted, each applicable path needs to restore a valid serial entry state or
terminate the collection through a defined error path.


Implementation Overview
=======================

Why there are two collectors
----------------------------

GIL-enabled and free-threaded CPython represent and enumerate GC state
differently. The GIL collector stores temporary reference counts and flags in
``PyGC_Head`` and walks generation lists. The free-threaded collector stores
temporary state in object fields and enumerates mimalloc pages. One shared
phase implementation would hide these differences rather than remove them.

The implementations share the worker-selection algorithm, normalization
function, work-stealing deque, barrier primitives, lifecycle contract, and
public activation model. They do not share object enumeration or marking
state.

GIL collector
-------------

The GIL collector performs these operations:

1. The collecting thread updates temporary reference counts, counts exact
   candidates, and records list waypoints.
2. A sub-threshold collection continues through the existing serial path.
3. Helpers pre-mark objects reachable from interpreter roots.
4. Helpers subtract internal references across list partitions.
5. Helpers find roots and mark reachable subgraphs.
6. The collecting thread reconstructs the reachable and unreachable lists.
7. The existing serial code handles weak references, finalizers, resurrection,
   and deletion.

Workers atomically clear the ``COLLECTING`` bit to claim one object for
traversal. Worker-local buffers reduce atomic deque traffic. Private deques
must be empty when a marking phase finishes because their entries are borrowed
object pointers.

Free-threaded collector
-----------------------

The free-threaded collector performs these operations:

1. Participants propagate reachability from known interpreter roots.
2. The collecting thread assigns non-empty mimalloc pages to worker buckets.
3. Participants compute adjusted reference counts.
4. The collecting thread accounts for deferred references on thread stacks.
5. Participants find roots and mark reachable objects. Idle participants steal
   work from active deques.
6. Participants scan pages into private results, and the collecting thread
   merges those results.
7. The existing collector handles weak references, finalizers, resurrection,
   and deletion outside the parallel graph phases.

Workers atomically clear the ``UNREACHABLE`` bit to claim one object for
traversal. A phase barrier prevents reference subtraction from observing a
page whose temporary state has not been initialized.

The earlier known-root propagation is an optimization rather than the
authoritative reachability decision. Its ``ALIVE`` update is idempotent, so two
workers can mark and traverse the same object without changing the result. The
implementation uses relaxed atomic byte loads and stores rather than atomic
read-modify-write ownership in that pass. It accepts duplicate traversal
instead of paying for an atomic ownership operation on
every edge. The later reference-difference pass remains authoritative and uses
an atomic ``UNREACHABLE`` transition to assign exactly one traversal owner.

Detailed phase algorithms, atomic-ordering arguments, deque invariants, and
fork state transitions belong in the project architecture documents. Those
details remain review requirements; copying them into this discussion
would not make them verified.


Compatibility
=============

Code that does not call ``gc.enable_parallel()`` continues to use the serial
collector. A build without ``--with-parallel-gc`` contains no parallel
collector implementation.

This design does not change the signatures of existing ``gc`` functions.
It does not add a public C API or stable-ABI entry point.

Traversal order is not stable in CPython's GC API. Applications that depend on
callback or finalizer ordering not guaranteed by the existing API remain
unsupported. Parallel graph traversal does not move weak-reference callbacks
or finalizers to helper threads.

The material compatibility change is helper-thread execution of
``tp_traverse``. Acceptance requires an audit of documented ``tp_traverse``
requirements and testing against extension types that maintain thread-local or
interpreter-local state.


Resource Use
============

The current pool capacity is 16. On first use a GIL build creates 16 helpers.
A free-threaded build reserves 16 participants and creates 15 helpers
because the collecting thread is participant zero.

Each worker normally receives a 256-K-entry pointer deque, 2 MiB on a 64-bit
build. The GIL implementation also gives each worker a
1,024-pointer local traversal buffer. Deques can grow when required.

Reducing the active participant count parks helpers; it does not reduce the
pool's reserved memory. ``gc.disable_parallel()`` destroys the free-threaded
pool. The current GIL implementation stops its helpers and retains pool
storage for a later restart.


Performance Requirements and Evidence
=====================================

Questions and measurements
--------------------------

Performance benefit and controller correctness are separate questions.
Deterministic tests can check trial and rollback rules; only integration and
benchmark measurements can show whether the selected counts improve
performance. The random walk has no global-optimum or convergence guarantee.
The following checks do not assume that every workload must benefit.

.. list-table::
   :header-rows: 1

   * - Question
     - Measurement
     - Interpretation or counterexample
   * - Which heaps have shorter collection intervals?
     - Alternating runs at recorded heap sizes and topologies; report the
       parallel/serial elapsed-time ratio and sample uncertainty per workload.
     - A ratio below 1 indicates improvement and above 1 indicates regression.
       Uncertainty spanning 1 leaves the direction unresolved.
   * - What does enabling cost when parallelism does not help?
     - Same-binary small-heap, low-GC and poorly scaling workloads; measure
       first use separately from later collections.
     - Report time ratios and absolute startup cost. The low-overhead goal
       requires an agreed limit and fails if measurements exceed it. The
       performance document records suggested criteria, not acceptance by
       documentation alone.
   * - Does the controller obey its contract?
     - Deterministic tests of count bounds, invalid samples, trial acceptance,
       rollback and persistence across collections.
     - An out-of-range count, learning from an invalid sample, or retaining a
       trial whose normalized cost is not lower contradicts the contract.
   * - Does adaptation improve performance without user tuning?
     - Fresh-process ABBA comparisons with recorded worker trajectories against
       private fixed-count controls at 2, 4, 8 and 16 across workload phases.
     - Compare elapsed-time ratios per phase. Adaptive losing to a tested fixed
       count identifies a cost of adaptation in that experiment, not a breach
       of the trial/rollback rules or proof about an untested optimum.
   * - Do measured benefits repeat on other hardware?
     - Repeat named workloads on recorded architectures and core counts.
     - Report each machine's ratios and uncertainty. A regression contradicts
       a claimed benefit for that workload on that machine; results on one
       host do not establish benefits elsewhere.

The benchmark protocol MUST record the CPython revision, build options, PGO
and LTO state, CPU affinity, NUMA policy, workload parameters, raw samples,
worker trajectories, and failures. Runtime-mode samples MUST use the same
executable and alternate modes. Pyperformance and adaptive/fixed campaigns use
fresh-process ABBA; the project full suite uses alternating paired runs. Record
which protocol each result used. A one-second run does not satisfy this
protocol.

Current evidence
----------------

The callback interval covers the complete start-to-stop callback span. In the
free-threaded collector, that span includes work outside the individual
stop-the-world sections. It is not a direct measurement of one continuous
free-threaded stop-the-world pause. Collection elapsed time, callback interval
and application throughput must not be treated as interchangeable metrics.

The latest project campaigns used PGO+LTO builds on one 72-logical-CPU AArch64
host. GIL collector ``669ed6b17e`` was measured on 7 October; FT collector
``195830171f`` was measured after lazy startup on 8 October. CPython head
``c67363fa59`` adds release-build test guards without changing the measured FT
collector. Parallel-GC phases were included in PGO training.

.. list-table::
   :header-rows: 1

   * - Build
     - Mixed throughput
     - Eight 500,000-object heaps
     - Sustained synthetic throughput
   * - GIL
     - Effectively unchanged
     - 1.08x geometric mean; one unstable negative graph result
     - +7.6 percent geometric mean
   * - Free-threaded
     - +23.5 percent
     - 8 of 8 faster; 1.24x geometric mean
     - +7.0 percent geometric mean

GIL mixed mean callback interval increased 3 percent and maximum interval
increased 21 percent. The sustained AI workload's mean interval increased
8 percent, although its throughput improved. The project result does not show
uniformly lower GIL latency.

FT mixed mean callback interval decreased 26 percent. Its sustained chain
mean interval increased 13 percent, while its AI workload lost 9.9 percent
throughput and increased mean interval by 116 percent. The AI maximum interval
increased from 3.38 to 14.39 seconds. Aggregate throughput improvements must
not conceal these negative results.

The FT rigorous pyperformance ABBA campaign completed 93 programs producing
119 named measurements. ``gc_traversal`` improved 41.8 percent,
``create_gc_cycles`` improved 22.7 percent and ``btree_gc_only`` improved
16.8 percent. ``float`` was 10.5 percent slower. SQLite and interpreter startup
differences were not significant. Seven programs were excluded for dependency
or missing-extension problems; this was not the complete default suite.

The complete GIL pyperformance sweep predates lazy startup. A focused rigorous
SQLite ABBA after that change was neutral: 1.421316 microseconds disabled and
1.429422 microseconds armed, a non-significant 0.57 percent difference. Earlier
eager-start SQLite regressions are superseded by these focused GIL and full FT
measurements, not erased from their original records.

One hypothesis for the FT AI result is cross-thread biased reference-counting
cost during serial finalization and deletion. The collector
executes finalizers on the collecting thread. A decrement of an object owned by
another thread cannot use that object's owner-local reference-count path and
instead uses shared atomic or queued BRC processing. A finalizer-driven
deallocation cascade can therefore create substantial cross-thread
reference-count traffic after parallel graph analysis has finished.

This explanation is a hypothesis. The current result contains callback spans
and throughput but no BRC-path counters or isolated serial-tail measurement,
so it does not establish the cause. Measurements that show no association
between cross-thread ownership, shared or queued BRC work, and the additional
callback span would reject the hypothesis. Changing BRC is outside this discussion.

The full reports, raw-result links, executable hashes and commands are in the
`GIL benchmark record <../benchmarks/results/arm64-316-669ed6b-full-analysis-2026-10-08.md>`_
and the
`FT benchmark record <../benchmarks/results/arm64-316-1958301-ft-lazy-analysis-2026-10-08.md>`_.

The FT adaptive/fixed ABBA experiment compared fixed counts 2, 4, 8 and 16
against adaptive arms in three workload phases. Fixed 16 was best for those
phases; the adaptive arms improved on fixed 2 and 4 but had not reached 16
within three cycles. This does not establish convergence time or an optimum
on other workloads. The local optimiser has no global-optimum guarantee.

A later release-build experiment found that free-threaded known-root
propagation scaling depends on where live data is rooted and on heap shape;
the project benchmarks above hold their heaps in function locals, the
favourable case (`performance document <PERFORMANCE.md>`_ section 4).

The historical collection-shape benchmarks also used creation workers that
could retain discarded batches, adding unintended stack roots. Their actual
garbage fraction is unknown. This limits interpretation of those shape
measurements; the mixed, sustained and pyperformance workloads did not use
that creation pool. The repair and module-rooted benchmark additions are
tracked in the `integration plan <CLAUDE_INTEGRATION_PLAN.md>`_.

These measurements establish that the implementation has profitable regions
and negative regions on that machine. They do not establish performance after
future changes, a universal speedup, cross-platform scaling, or that the
suggested low-overhead criteria are met. The complete raw-data provenance and reproduction commands
belong in the project benchmark record.

Functional and sanitizer evidence
---------------------------------

Local GIL and FT selections exercise lazy startup, injected startup failures,
serial fallback, warning delivery, explicit retry, enable/disable lifecycle,
fork recovery and collector/deque invariants. Recorded ASan and TSan
selections completed without diagnostics. These are bounded selections:
ASan leak detection was disabled, TSan used recorded options and suppressions,
and neither result establishes correctness on untested paths or platforms.

Earlier Linux and Windows full workflows passed at ``d396f837b9``; a later
four-build matrix passed before the current local commits. Those runs do not
validate ``c67363fa59`` or subsequent source. The
`validation record <VALIDATION.md>`_ tracks required runs and results for each
published source pair; live GitHub status was unavailable during reconciliation.
Full-suite workflows use the default disabled runtime policy; focused tests
explicitly activate parallel GC. The
`testing guide <TESTING.md>`_, `lazy-pool contract <DESIGN.md>`_
and `open issues <OPEN_ISSUES.md>`_ identify contracts and coverage gaps.
Exact historical lifecycle selections remain available with
``git show 724b74b:docs/LAZY_POOL_CREATION_PLAN.md``. No tests were rerun for
this document revision.

Evidence still needed
---------------------

The project tracks the following validation work. This is a starting list for
review, not acceptance criteria agreed by CPython:

- clean-revision optimized GIL and free-threaded benchmark runs;
- optimized feature-off controls from the same source revision;
- a numerical regression limit for workloads that do not benefit;
- worker-trajectory results that exercise growth, retreat, and workload change;
- Linux AArch64, Linux x86-64, Windows, and macOS functional results;
- full CPython regression results for both GIL and free-threaded builds;
- race analysis on the parallel collector, with exact test selection, options
  and suppressions. Local GIL and FT TSan selections are recorded; they do not
  cover every collector path;
- results from an extension ``tp_traverse`` test set agreed during review. The
  project has not yet defined that test set.


Security and Correctness
========================

Parallel GC adds atomic object-state transitions, work-stealing deques,
mutexes, condition variables, barriers, and helper thread states to code that
walks arbitrary extension-defined object graphs. A lost work item can classify
a reachable object as unreachable. A stale work item can dereference an object
after its lifetime ends. A lifecycle race can leave a helper using interpreter
state during finalization or after ``fork()``.

Tests can expose instances of these defects; passing tests cannot prove their
absence. Review therefore includes the memory-ordering argument for every
shared object-state transition and the ownership invariant for every queue.
Debug builds assert list integrity and phase postconditions. Dynamic race and
memory analysis form part of the evidence needed for review.

No worker executes user finalizers or ``tp_clear``. That boundary limits the
new concurrency surface; it does not remove the need to audit extension
``tp_traverse`` implementations.


Rejected Alternatives
=====================

Require applications to select a worker count
----------------------------------------------

This makes application configuration part of collector correctness and
performance. One fixed value cannot track changes in heap topology, process
contention, or hardware. The design keeps the choice inside the collector.

Expose a heap-size threshold
----------------------------

Object count alone does not predict graph cost or parallel scalability. The
GIL collector uses an internal serial crossover to avoid dispatch on small
collections, but that value is implementation policy rather than an
application contract.

Use every available CPU
-----------------------

CPUs beyond the useful parallel width increase synchronization and cache
traffic. The implementation caps pool capacity and measures adjacent worker
counts instead of equating CPU count with useful GC parallelism.

Create threads for each collection
----------------------------------

Creating and joining helpers for every collection places operating-system
thread lifecycle costs directly on the pause path. Those costs are large
enough to erase the benefit of parallel collection. Persistent helpers instead
pay creation cost once at first use and remain parked between collections.
Explicit activation only arms the collector. The transactional startup and
serial failure contract protect the first-use collection; persistence is
required to amortize the creation cost.

Parallelize finalization and deletion
-------------------------------------

Finalizers and ``tp_clear`` execute arbitrary extension and Python behaviour.
Parallel execution would change their concurrency contract and would require a
separate ownership design. This design leaves them on the collecting thread.

Implement only the free-threaded collector
------------------------------------------

GIL-enabled Python also experiences long stop-the-world cyclic collections and
has idle cores during those collections. The two implementations share the
user model and controller while retaining their required internal differences.

Replace stop-the-world GC with concurrent GC
---------------------------------------------

Concurrent collection requires barriers or another mechanism that preserves a
consistent graph while mutators run. That is a different collector design.
This design parallelizes bounded phases inside the existing collection
model.


Activation and future decisions
===============================

The experimental implementation keeps parallel GC disabled at build time
unless a distributor passes ``--with-parallel-gc``. A supporting build keeps
parallel GC disabled at runtime until code calls ``gc.enable_parallel()``.

The functions described here are experimental branch interfaces, not an
accepted public API or a release commitment. An eventual formal proposal must
settle the API and its compatibility obligations. Automatic activation and
default enablement are outside this discussion; the design is opt-in.


Reference Implementation
========================

The project repository is https://github.com/SonicField/parallel_gc. The
``cpython`` submodule points to the implementation branch in
https://github.com/SonicField/cpython. No pull request has been opened against
``python/cpython``.

The implementation is primarily contained in these files:

- ``Python/gc_parallel.c`` and ``Include/internal/pycore_gc_parallel.h`` for
  the GIL collector;
- ``Python/gc_free_threading_parallel.c`` and
  ``Include/internal/pycore_gc_ft_parallel.h`` for the free-threaded collector;
- ``Include/internal/pycore_gc_random_walk.h`` for shared adaptation;
- ``Include/internal/pycore_ws_deque.h`` for worker deques;
- ``Include/internal/pycore_gc_barrier.h`` for phase synchronization;
- ``Modules/gcmodule.c`` for runtime activation and diagnostics.

The project repository contains the architecture, fork design, test matrix,
benchmark protocol, raw performance records, and unresolved source audit. The
parent revision's ``cpython`` gitlink selects the implementation for a checkout;
it does not automatically follow the fork branch's latest tip. The
`repository README <../README.md>`_ records the entry path. The
`validation record <VALIDATION.md>`_ identifies the dated review baseline,
benchmark revisions and CI outcomes. Historical measurements remain attached
to their original source, not silently relabelled as results for newer code.


Open Decisions and Blockers
===========================

The following decisions and defects remain unresolved.

1. Agree the maximum accepted regression for enabled workloads that do not
   benefit from parallelism; the performance document records review-work
   proposals for that discussion.
2. Decide whether ``gc.get_parallel_stats()`` has a stable public schema or a
   private diagnostic name.
3. Specify and implement every post-mutation resource-failure path.
4. Complete the ``tp_traverse`` compatibility audit and extension testing.
5. Produce current-head performance and required platform evidence.
6. Define failure policy for unsuccessful helper joins; startup rollback does
   not resolve this separate lifetime problem.
7. Map attributed CinderX-derived portions to exact source and licensing.
8. Resolve the upstream subinterpreter/fork coverage gap when the feature-off
   control permits the test to run.
9. Measure first-use startup latency and pool memory use explicitly.


Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal licence, at the option of the reader.
