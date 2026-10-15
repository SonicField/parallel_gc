# Decisions for Core-Developer Review

The current port deliberately leaves policy questions separate from the
collector mechanics. These are the decisions to resolve during the sprint.

Reconciled on 12 October 2026 for CPython `c67363fa59`. The
[review handoff](REVIEW_HANDOFF.md) names the exact checkpoint and evidence.
Decisions below are discussion items, not authorization to change collector
algorithms, atomic ordering or work distribution.

## Public surface

Decide whether the first proposal should expose all of:

- `--with-parallel-gc`;
- `gc.enable_parallel()`, `gc.disable_parallel()`, and
  `gc.get_parallel_config()`;
- diagnostic `gc.get_parallel_stats()`; and
- the orthogonal `gc.collect_async()` scheduling API, which is outside the
  [discussion PEP](pep-parallel-gc-v2.rst).

The current implementation deliberately has no startup environment variable,
`-X` option, or `PyConfig` field for selecting a worker count.

## Worker-count contract

The implementation uses a fixed maximum of 16 collector participants. A GIL
build uses 16 helpers while the collecting thread coordinates them. In a
free-threaded build, the collecting thread participates and the pool therefore
creates 15 helpers.

A shared stochastic random-walk controller starts at 4 workers. On 20% of
accepted-count collections it tries an unbiased adjacent count; the following
valid collection retains an improvement or walks back. The GIL collector
records list waypoints every 8192 candidate objects for work partitioning and
stays serial below 16,384 candidates; the split interval does not cap the
active worker count.

Both implementations normalize elapsed time with the exact candidate count in
the same shared function. Objects ultimately collected are deliberately not the
denominator: the collector must examine live candidates too, and a collection
that reclaims nothing still performs graph work.

`gc.enable_parallel()` takes no worker-count argument. Whether 16 should remain
the long-term maximum is a policy question to revisit with benchmark evidence;
it is not selected through startup configuration.

Serial execution is deliberately outside the FT worker search. Its
discontinuous cost can trap an adjacent local walk before it discovers a faster
parallel count beyond a slower intermediate one. This does not establish that
two participants always beat serial or that the walk finds a global optimum.
The fixed/adaptive experiment found fixed 16 faster than adaptive in the three
tested FT phases; convergence and workload-change behavior remain benchmark
questions.

## Pool-start contract

Both implemented contracts separate policy from resources.
`gc.enable_parallel()` enters an armed state without creating native threads.
The first collection with at least 16,384 candidates and two usable work
splits starts the 16-helper pool transactionally. A startup failure rolls back
all partial resources, completes the collection serially, emits one warning
after collection state is safe, and disables further attempts. A later
explicit enable request resets the adaptive controller and permits one retry.

GIL child-fork recovery also becomes armed without creating helpers. The
parent is unchanged, and a child collection inherited from a callback or
finalizer finishes serially before later eligible work may start a pool.
FT also arms without helpers and creates 15 helpers at the first collection,
before stopping the world. Its lifecycle mutex serializes the collection-start
decision, configuration and lifecycle operations. Supported fork preparation
acquires that mutex before stop-the-world; the parent releases it before
resuming the world. Child recovery creates no helper and leaves an enabled
collector armed. The implementation and verification are recorded in
[`LAZY_POOL_CREATION_PLAN.md`](LAZY_POOL_CREATION_PLAN.md).

Both feature-on APIs expose `pool_active`, `startup_failed`, a monotonic
startup-failure counter and a bounded error code. The public diagnostic names
and schema remain reviewable. Disabled or failed configurations report zero
`num_workers` even if reusable GIL storage is retained.

The current free-threaded configuration dictionary includes a
`parallel_cleanup` key inherited from the prototype even though finalization
and `tp_clear` deletion are serial. Its name and whether it belongs in the
public contract need an explicit decision.

## Initial implementation scope

The proposed GIL implementation parallelizes interpreter-root marking,
reference subtraction, and reachability marking. The proposed free-threaded
implementation parallelizes root propagation, `update_refs`, `mark_heap`, and
`scan_heap`. Finalization and deletion remain serial in both builds. These are
the restored original phase boundaries; narrowing them would be a design
change, not presentation cleanup.

## Failure and compatibility decisions

Unchecked join results require a separate policy: cleanup cannot assume a
helper terminated when joining it failed. GIL split-vector allocation, FT
unique-ID allocation and FT scan rollback need fault-injection investigation.
See [AUTIT-TODO.md](../AUTIT-TODO.md) for source-visible hazards, hypotheses and
repaired items. Thread-start rollback is implemented; these remaining failures
are not made safe merely by calling startup transactional.

Extension `tp_traverse` runs on helper threads, and FT helpers install their
thread states without the GIL helper's full bind. Agree an extension
compatibility test set. Complete the exact CinderX source/provenance/licensing
mapping. Retain the subinterpreter/fork skip until the feature-off control no
longer crashes.

## Landing requirements

The current Linux AArch64 functional and performance evidence is strong enough
for design discussion, not landing. Latest project results show a GIL 1.08x
collection geomean with an unstable negative graph result, and FT 1.24x with
all eight requested shapes improving. FT sustained AI throughput and callback
interval, and pyperformance `float`, remain negative results. Remaining gates
include:

- clean-revision repeats of the optimized GIL and free-threaded benchmark
  results, plus optimized feature-off controls;
- wider fault-injection and race analysis beyond the passing local GIL and FT
  ASan/TSan selections;
- current-revision Linux x86-64 and Windows repeats plus native macOS
  active-collector validation;
- explicit first-use latency and memory measurements;
- public API decisions and an agreed performance regression limit;
- a published port revision and a NEWS entry tied to a real CPython issue.
