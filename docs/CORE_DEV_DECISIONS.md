# Decisions for Core-Developer Review

The current port deliberately leaves policy questions separate from the
collector mechanics. These are the decisions to resolve during the sprint.

## Public surface

Decide whether the first proposal should expose all of:

- `--with-parallel-gc`;
- `gc.enable_parallel()`, `gc.disable_parallel()`, and
  `gc.get_parallel_config()`.

The current implementation deliberately has no startup environment variable,
`-X` option, or `PyConfig` field for selecting a worker count.

## Worker-count contract

The implementation uses a fixed maximum of 16 collector participants. A GIL
build uses 16 helpers while the collecting thread coordinates them. In a
free-threaded build, the collecting thread participates and the pool therefore
creates 15 helpers.

A shared stochastic hill-climbing controller starts at 4 workers, randomly
tries an adjacent count, and retains it only when measured cost per candidate
improves. The GIL collector records list waypoints every 8192 candidate objects
for work partitioning, but that split interval does not cap the active worker
count.

`gc.enable_parallel()` takes no worker-count argument. Whether 16 should remain
the long-term maximum is a policy question to revisit with benchmark evidence;
it is not selected through startup configuration.

## Initial implementation scope

The proposed GIL implementation parallelizes interpreter-root marking,
reference subtraction, and reachability marking. The proposed free-threaded
implementation parallelizes root propagation, `update_refs`, `mark_heap`, and
`scan_heap`. Finalization and deletion remain serial in both builds. These are
the restored original phase boundaries; narrowing them would be a design
change, not presentation cleanup.

## Landing requirements

The current Linux AArch64 functional and ASan evidence is strong enough for
design discussion, not landing. Remaining gates are:

- current optimized GIL and free-threaded benchmark results;
- ThreadSanitizer once a usable runtime is available;
- Linux x86-64 plus native Windows and macOS validation;
- canonical regeneration of `configure`;
- a published port revision and a NEWS entry tied to a real CPython issue.
