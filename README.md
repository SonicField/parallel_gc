# Parallel Garbage Collection for CPython

This project develops and evaluates parallel cyclic garbage collection for GIL
and free-threaded CPython builds. Parallel collection is optional at build time
and runtime.

The project deliberately spans two repositories:

- The `cpython/` submodule is the `SonicField/cpython` fork. It contains the
  implementation, CPython integration, focused correctness tests, build-system
  changes, and CPython-facing documentation that could form an upstream
  proposal.
- This outer `parallel_gc` repository contains the design material, project CI,
  benchmark drivers, raw performance results, and reproducibility records.
  The outer repository pins the exact CPython fork commit being evaluated.

The performance work is not optional supporting material. General-purpose
Python benchmark suites such as `pyperformance` are useful for detecting broad
interpreter regressions, but they do not reliably create large cyclic heaps,
trigger substantial collections, or distinguish collector throughput and
pause behavior. They therefore cannot, by themselves, determine whether
parallel GC works. The dedicated benchmarks in this repository provide that
evidence under controlled heap shapes, sustained workloads, and alternating
serial/parallel measurements. They are necessarily substantial and
experimental, so they do not belong in the main CPython tree.

## Repository status

Clone the complete project first:

```bash
git clone --recurse-submodules https://github.com/SonicField/parallel_gc.git
cd parallel_gc
git submodule update --init --recursive
```

The authoritative source is the checked-in `cpython/` submodule at
`SonicField/cpython` commit `86c83d41f5ae6df6558130b978d1d0a09a036a05`, on
branch `parallel-gc-upstream-port`. The port is based on CPython commit
`333071231d3a46cccc32d7f44b99328c3299d0b1` from `python/cpython` main. A clone
with submodules therefore obtains the exact reviewed source.

The root `Makefile` and scripts under `tools/` still describe the older project
workflow. Use the explicit current-port commands below for build, test,
sanitizer, and benchmark evidence.

## Implemented scope

- The GIL collector counts the generation and keeps collections below 16,384
  candidates entirely serial. Above that threshold it parallelises
  interpreter-root pre-marking, reference subtraction, and reachability
  marking. List reconstruction, finalization, and deallocation remain serial.
- The free-threaded collector parallelises root propagation, `update_refs`,
  `mark_heap`, and `scan_heap`. Finalization and deallocation remain serial.

Both implementations use persistent worker pools. The GIL path uses
split-vector work assignment. The free-threaded path distributes mimalloc pages
for `mark_heap` and uses work-stealing while traversing reachable objects.

## Build the current local port

Run these commands from the outer repository:

```bash
mkdir -p build-port-ft
cd build-port-ft
../cpython/configure \
    --disable-gil \
    --with-pydebug \
    --with-parallel-gc
make -j"$(nproc)"
```

For a GIL build, use a separate build directory:

```bash
cd ..
mkdir -p build-port-gil
cd build-port-gil
../cpython/configure \
    --with-pydebug \
    --with-parallel-gc
make -j"$(nproc)"
```

Keeping the configurations out of tree prevents incompatible generated files
and object files from being reused.

The complete verification matrix also includes feature-off GIL and
free-threaded control builds. See the [build-and-test guide](docs/BUILD_AND_TEST.md)
for all four configurations.

## Use and test

The runtime API is:

```python
import gc

gc.enable_parallel()
print(gc.get_parallel_config())
print(gc.get_parallel_stats())
gc.collect()
gc.collect_async()
gc.disable_parallel()
```

`gc.enable_parallel()` creates a pool with a fixed maximum of 16 workers. The
stochastic random-walk controller tries adjacent worker counts and walks back
after a regression. There is no environment-variable, `-X`, or `PyConfig`
startup control. In a build without parallel-GC support, the runtime enable and
disable functions raise `RuntimeError`, while
`gc.get_parallel_config()` reports that the feature is unavailable.

`gc.get_parallel_stats()` exposes implementation diagnostics and phase
timings. `gc.collect_async()` schedules the normal collector and returns
without waiting; it is part of the current experimental surface but does not
itself select parallel mode.

From a configured build directory, run:

```bash
./python -m test -j4 \
    test_gc \
    test_gc_ws_deque \
    test_gc_parallel \
    test_gc_parallel_fork \
    test_gc_parallel_properties \
    test_capi.test_config \
    test_embed
```

For the free-threaded build, also run `test_gc_ft_parallel` and
`test_free_threading.test_gc`. See the build-and-test guide for the full matrix.

## Fork behavior

Forks made through CPython's supported fork protocol retain the parent's pool
unchanged and replace the child's inherited pool with new helpers. The child
adaptive controller restarts at four workers with no parent measurement. If a
finalizer forks, the child completes the inherited collection without using it
to train the new controller. The GIL and free-threaded regression tests cover
ordinary and finalizer forks with bounded child waits. See the
[fork architecture](docs/FORK_ARCHITECTURE.md) for the lifecycle contract and
its explicit exclusion of raw extension-level `fork()` calls.

Subinterpreter cleanup after a fork could not be tested as a parallel-GC
property. Current upstream-based GIL and free-threaded controls both crash when
the main interpreter forks while an otherwise idle legacy subinterpreter
exists, without enabling parallel GC anywhere. The intended parallel-GC test
is retained but skipped with that reason. If CPython's underlying lifecycle is
fixed, the test should be enabled: pools belonging to subinterpreters that the
child is about to delete must be abandoned without joining parent-only helper
threads.

GIL helpers create and bind persistent `PyThreadState` objects. Free-threaded
helpers also own persistent thread states; they install those states in
thread-local storage while running collector work, without performing a full
bind. This supports debug-build reference accounting when a `tp_traverse`
implementation changes a reference count.

## Performance evidence

Optimized PGO+LTO measurements on the current 72-core AArch64 host show that
the implementation is worth further evaluation, while also identifying its
limits:

- GIL: all eight requested 500,000-object heaps improved, with a 1.26x
  collection-time geomean. Sustained synthetic throughput improved by 9.5%
  geomean; the mixed workload was effectively neutral at -0.2%.
- Free-threaded: all eight requested heaps improved, with a 1.22x geomean.
  Mixed-workload throughput improved by 19.5%. Sustained synthetic throughput
  improved by 2.3% geomean, but the finalizer-heavy workload regressed by
  14.7% and its callback interval increased.

These are same-binary serial/parallel comparisons, not general CPython
performance claims. Callback intervals are not strictly stop-the-world time in
the free-threaded build. Full metadata, raw samples, and qualifications are in
[the benchmarking guide](docs/BENCHMARKING.md) and the linked result files.

## Key files

| File | Purpose |
|------|---------|
| `cpython/Python/gc_parallel.c` | GIL parallel collector |
| `cpython/Python/gc_free_threading_parallel.c` | Free-threaded parallel collector phases |
| `cpython/Include/internal/pycore_gc_parallel.h` | GIL collector state |
| `cpython/Include/internal/pycore_gc_ft_parallel.h` | Free-threaded collector state |
| `cpython/Include/internal/pycore_ws_deque.h` | Shared work-stealing deque |
| `cpython/Include/internal/pycore_gc_barrier.h` | Shared barrier |
| `cpython/Modules/gcmodule.c` | Python-level control and configuration API |

## Documentation

- [Getting Started](docs/GETTING_STARTED.md)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Fork Architecture](docs/FORK_ARCHITECTURE.md)
- [Build and Test Guide](docs/BUILD_AND_TEST.md)
- [Benchmarking Guide](docs/BENCHMARKING.md)
- [Proposed Patch Series](docs/PATCH_SERIES.md)
- [Current Source Inventory](docs/SOURCE_INVENTORY.md)
- [Core-Developer Decisions](docs/CORE_DEV_DECISIONS.md)
- [Core-Developer Sprint Readiness Plan](docs/CORE_DEV_SPRINT_READINESS_PLAN.md)
- [Design Post](docs/DESIGN_POST.md)
- [PEP Draft](docs/pep-parallel-gc.rst)

## Links

- [Project repository](https://github.com/SonicField/parallel_gc)
- [Project CPython fork](https://github.com/SonicField/cpython)
- [Upstream CPython](https://github.com/python/cpython)
