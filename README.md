# Parallel Garbage Collection for CPython

This repository is an experimental implementation of parallel cyclic garbage
collection for GIL and free-threaded CPython builds. Parallel collection is
optional at build time and runtime.

## Repository status

Clone the complete project first:

```bash
git clone --recurse-submodules https://github.com/SonicField/parallel_gc.git
cd parallel_gc
git submodule update --init --recursive
```

The authoritative source is the checked-in `cpython/` submodule at
`SonicField/cpython` commit `9da963f754f747d64a6db4112efa2a2ef8bde111`, on
branch `parallel-gc-upstream-port`. The port is based on CPython commit
`333071231d3a46cccc32d7f44b99328c3299d0b1` from `python/cpython` main. A clone
with submodules therefore obtains the exact reviewed source.

The root `Makefile` and scripts under `tools/` still describe the older project
workflow. Use the explicit current-port commands below for build, test,
sanitizer, and benchmark evidence.

## Implemented scope

- The GIL collector runs `update_refs_with_splits` serially, then parallelises
  reference subtraction and reachability marking. The collecting thread moves
  objects between GC lists; finalization and deallocation also remain serial.
- The free-threaded collector parallelises only `mark_heap`, the transitive
  reachability phase. Root propagation, `update_refs`, `scan_heap`,
  finalization, and deallocation remain serial.

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

```bash
./python -X parallel_gc=4 your_script.py
PYTHON_PARALLEL_GC=4 ./python your_script.py
```

The runtime API is:

```python
import gc

gc.enable_parallel(4)
print(gc.get_parallel_config())
gc.collect()
gc.disable_parallel()
```

`gc.enable_parallel()` accepts worker counts from 2 through 64. Startup controls
also accept zero to leave the collector disabled. In a build without
`--with-parallel-gc`, a nonzero `-X parallel_gc`, `PYTHON_PARALLEL_GC`, or
`PyConfig.parallel_gc_workers` request fails interpreter startup. The runtime
enable and disable functions raise `RuntimeError` in that build, while
`gc.get_parallel_config()` reports that the feature is unavailable.

From a configured build directory, run:

```bash
PYTHON_PARALLEL_GC=4 ./python -m test -j4 \
    test_gc \
    test_gc_ws_deque \
    test_gc_parallel \
    test_gc_parallel_properties \
    test_capi.test_config \
    test_embed
```

For the free-threaded build, also run `test_gc_ft_parallel` and
`test_free_threading.test_gc`. See the build-and-test guide for the full matrix.

## Fork behavior

Parallel worker threads are quiesced before `fork()`. In the parent, CPython
attempts to restart the previous worker pool; if that fails, the successful
fork is preserved and parallel GC is disabled. The child does not create worker
threads in the post-fork handler and uses serial GC until
`gc.enable_parallel()` is called explicitly.

Helpers invoke `tp_traverse` without attaching Python thread states. This
matches the current C-API contract: `tp_traverse` may be called from any thread,
and only the collecting thread's state remains attached while the world is
stopped.

## Performance evidence

No performance result is claimed yet for this port. The progress log records
functional suite passes on Linux AArch64 for the current development state. See
[the benchmarking guide](docs/BENCHMARKING.md) for the measurements required
before proposing a performance claim.

## Key files

| File | Purpose |
|------|---------|
| `cpython/Python/gc_parallel.c` | GIL parallel collector |
| `cpython/Python/gc_free_threading_parallel.c` | Free-threaded parallel mark implementation |
| `cpython/Include/internal/pycore_gc_parallel.h` | GIL collector state |
| `cpython/Include/internal/pycore_gc_ft_parallel.h` | Free-threaded collector state |
| `cpython/Include/internal/pycore_ws_deque.h` | Shared work-stealing deque |
| `cpython/Include/internal/pycore_gc_barrier.h` | Shared barrier |
| `cpython/Modules/gcmodule.c` | Python-level control and configuration API |

## Documentation

- [Getting Started](docs/GETTING_STARTED.md)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Build and Test Guide](docs/BUILD_AND_TEST.md)
- [Benchmarking Guide](docs/BENCHMARKING.md)
- [Proposed Patch Series](docs/PATCH_SERIES.md)
- [Current Source Inventory](docs/SOURCE_INVENTORY.md)
- [Core-Developer Decisions](docs/CORE_DEV_DECISIONS.md)
- [Design Post](docs/DESIGN_POST.md)
- [PEP Draft](docs/pep-parallel-gc.rst)

## Links

- [Project repository](https://github.com/SonicField/parallel_gc)
- [Project CPython fork](https://github.com/SonicField/cpython)
- [Upstream CPython](https://github.com/python/cpython)
