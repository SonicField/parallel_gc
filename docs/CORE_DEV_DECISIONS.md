# Decisions for Core-Developer Review

The current port deliberately leaves policy questions separate from the
collector mechanics. These are the decisions to resolve during the sprint.

## Public surface

Decide whether the first proposal should expose all of:

- `--with-parallel-gc`;
- `gc.enable_parallel()`, `gc.disable_parallel()`, and
  `gc.get_parallel_config()`;
- `-X parallel_gc=N` and `PYTHON_PARALLEL_GC=N`;
- `PyConfig.parallel_gc_workers`.

The implementation and tests currently support that complete surface, but it
is isolated in the final API/configuration patch so it can be narrowed without
changing either collector.

## Worker-count contract

The configured value has one meaning in both builds: it is the maximum number
of threads that may execute collector work, from 2 through 64. A GIL build
uses that many helpers while the collecting thread coordinates them. In a
free-threaded build, the collecting thread participates and the pool therefore
creates exactly one fewer helper. A collection may activate fewer helpers and
uses at most one participant per 8192 candidate objects. The grain remains a
policy choice to revisit after benchmark results exist.

Startup accepts zero as disabled or 2 through 64 as a concurrency limit. A
nonzero startup request fails initialization in a feature-off build rather
than being silently ignored.

## Initial implementation scope

The proposed GIL implementation parallelizes reference subtraction and
reachability marking. The proposed free-threaded implementation parallelizes
only `mark_heap`; its root propagation, reference setup, scan, finalization,
and deletion remain upstream serial code. Expanding either scope should be a
follow-up backed by independent correctness and performance evidence.

## Landing requirements

The current Linux AArch64 functional and ASan evidence is strong enough for
design discussion, not landing. Remaining gates are:

- current optimized GIL and free-threaded benchmark results;
- ThreadSanitizer once a usable runtime is available;
- Linux x86-64 plus native Windows and macOS validation;
- canonical regeneration of `configure`;
- a published port revision and a NEWS entry tied to a real CPython issue.
