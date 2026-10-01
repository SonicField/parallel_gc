# Decisions for Core-Developer Review

The current port deliberately leaves policy questions separate from the
collector mechanics. These are the decisions to resolve during the sprint.

## Public surface

Decide whether the first proposal should expose all of:

- `--with-parallel-gc`;
- `gc.enable_parallel()`, `gc.disable_parallel()`, and
  `gc.get_parallel_config()`;
- diagnostic `gc.get_parallel_stats()`; and
- the orthogonal `gc.collect_async()` scheduling API.

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

## Landing requirements

The current Linux AArch64 functional and performance evidence is strong enough
for design discussion, not landing. Both build modes improve all eight
requested 500,000-object heaps, while the free-threaded finalizer-heavy
sustained case is a documented negative region. Remaining gates are:

- clean-revision repeats of the optimized GIL and free-threaded benchmark
  results, plus optimized feature-off controls;
- ThreadSanitizer once a usable runtime is available;
- Linux x86-64 plus native Windows and macOS validation;
- a published port revision and a NEWS entry tied to a real CPython issue.
