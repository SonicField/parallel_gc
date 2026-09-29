# Getting Started with Parallel GC for CPython

This project adds an optional parallel cyclic collector to GIL and
free-threaded CPython builds. The two implementations share deque and
synchronization primitives, but have separate worker pools and integrate with
different serial collectors.

## Obtain the source

Clone the complete parent repository first:

```bash
git clone --recurse-submodules https://github.com/SonicField/parallel_gc.git
cd parallel_gc
git submodule update --init --recursive
```

This is important because the parent repository contains the documentation,
benchmarks, and project-level test workflow.

### Current port status

The authoritative source is the `cpython/` submodule at
`SonicField/cpython` commit `55aeaa3e3d955dfef392c89ca7773353646ebca7`, on
branch `parallel-gc-upstream-port`. It is based on CPython commit
`333071231d3a46cccc32d7f44b99328c3299d0b1` from `python/cpython` main.

The root `Makefile` and scripts under `tools/` target the older workflow; use
the explicit commands in this guide for current-port validation.

## Build the current port

Use an out-of-tree build so GIL and free-threaded configurations do not share
generated files:

```bash
mkdir -p build-port-ft
cd build-port-ft
../cpython/configure \
    --disable-gil \
    --with-pydebug \
    --with-parallel-gc
make -j"$(nproc)"
```

For a GIL build:

```bash
cd ..
mkdir -p build-port-gil
cd build-port-gil
../cpython/configure \
    --with-pydebug \
    --with-parallel-gc
make -j"$(nproc)"
```

Install CPython's normal build dependencies first; see the
[CPython setup guide](https://devguide.python.org/getting-started/setup-building/).
Missing optional extension dependencies are reported by `configure`.

These are the two feature-on builds. The complete verification matrix also has
feature-off GIL and free-threaded controls; see
[BUILD_AND_TEST.md](BUILD_AND_TEST.md) for all four configurations.

## Verify the build

From either configured feature-on build directory:

```bash
./python -c "
import gc
print(gc.get_parallel_config())
gc.enable_parallel(4)
gc.collect()
gc.disable_parallel()
"
```

A build configured with `--with-parallel-gc` reports
`'available': True`. While enabled, `num_workers` is the configured number of
threads that may execute collector work.

Run the focused tests in the GIL build:

```bash
PYTHON_PARALLEL_GC=4 ./python -m test -j4 \
    test_gc \
    test_gc_ws_deque \
    test_gc_parallel \
    test_gc_parallel_properties \
    test_capi.test_config \
    test_embed
```

Run the corresponding free-threaded set in its build directory:

```bash
PYTHON_PARALLEL_GC=4 ./python -m test -j4 \
    test_gc \
    test_gc_ws_deque \
    test_gc_parallel \
    test_gc_parallel_properties \
    test_capi.test_config \
    test_embed \
    test_gc_ft_parallel \
    test_free_threading.test_gc
```

## Runtime controls

Parallel collection is off unless enabled at startup or through the `gc`
module:

```bash
./python -X parallel_gc=4 script.py
PYTHON_PARALLEL_GC=4 ./python script.py
```

```python
import gc

gc.enable_parallel(4)
config = gc.get_parallel_config()
gc.disable_parallel()
```

Valid worker counts are 2 through 64. In a GIL build the collecting thread
coordinates that many helpers. In a free-threaded build it participates as
worker zero, so the pool creates exactly one fewer helper. Individual
collections may activate fewer helpers when there is not enough work.

Zero is accepted by the startup controls and leaves parallel GC disabled. If
the interpreter was built without `--with-parallel-gc`, any nonzero startup
request through `-X parallel_gc`, `PYTHON_PARALLEL_GC`, or
`PyConfig.parallel_gc_workers` fails initialization. In such a build,
`gc.enable_parallel()` and `gc.disable_parallel()` raise `RuntimeError`, while
`gc.get_parallel_config()` reports `available` as false.

## What runs in parallel

| Collector | Parallel phases | Serial phases |
|-----------|-----------------|---------------|
| GIL | reference subtraction, reachability marking | `update_refs_with_splits`, list movement, finalization, deallocation |
| Free-threaded | `mark_heap` | root propagation, `update_refs`, `scan_heap`, finalization, deallocation |

For the free-threaded collector, page assignment is a separate preparation
step after serial `update_refs`. The collector then scans thread stacks
serially to account for deferred references. Parallel `mark_heap` scans the
assigned page buckets for roots and uses work-stealing for transitive
traversal. Serial `scan_heap` restores object state and creates the
unreachable worklists.

The implementation remains stop-the-world. “Parallel” refers to collector work
performed by the collecting thread and helper threads during that pause; it
does not mean collection runs concurrently with application threads.

Helpers call `tp_traverse` without attaching Python thread states. Current
CPython C-API documentation permits `tp_traverse` to run on any thread and
requires only one attached thread state during collection; the collecting
thread supplies that state.

## Fork behavior

Before `fork()`, CPython quiesces the parallel collector's worker pool. After
a successful fork:

- The parent attempts to restart the pool. If restart fails, the fork still
  succeeds and parallel GC is disabled in the parent.
- The child remains on serial GC. It does not create helper threads in the
  post-fork handler.
- The child may opt in again later with `gc.enable_parallel(N)`.

This behavior avoids inheriting synchronization state for threads that do not
exist in the child.

## Repository layout

```text
parallel_gc/
  cpython/                    authoritative CPython submodule
  docs/                       design, build, test, and proposal documents
  benchmarks/                 benchmark drivers and result storage
  Makefile                    legacy workflow for the cpython/ submodule
  tools/                      legacy helpers; not current-port validation
```

Important files in the current port:

| File | Purpose |
|------|---------|
| `Python/gc_parallel.c` | GIL parallel collector |
| `Python/gc_free_threading_parallel.c` | Free-threaded parallel mark implementation |
| `Python/gc.c` | GIL integration |
| `Python/gc_free_threading.c` | Free-threaded integration |
| `Include/internal/pycore_ws_deque.h` | Work-stealing deque and local buffer |
| `Include/internal/pycore_gc_barrier.h` | Worker synchronization |
| `Modules/gcmodule.c` | Runtime API |

## Reading order

1. [Architecture](ARCHITECTURE.md) for control flow and invariants.
2. [Build and Test](BUILD_AND_TEST.md) for the validation matrix.
3. [Benchmarking](BENCHMARKING.md) for measurement requirements.
4. [Design Post](DESIGN_POST.md) for algorithm background.
5. [PEP draft](pep-parallel-gc.rst) for the proposed upstream interface.

## Performance status

The current port has functional build-and-test evidence on Linux AArch64 but
does not yet make a performance claim. New results must name the exact source
revision, build configuration, hardware, affinity and NUMA policy, workload
parameters, sample count, and measured statistic. See
[BENCHMARKING.md](BENCHMARKING.md).
