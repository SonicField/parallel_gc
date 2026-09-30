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
`SonicField/cpython` commit `323d3cc90adcc5dcc799f79812edd339b347a46c`, on
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
gc.enable_parallel()
gc.collect()
gc.disable_parallel()
"
```

A build configured with `--with-parallel-gc` reports
`'available': True`. While enabled, `num_workers` is the configured number of
threads that may execute collector work.

Run the focused tests in the GIL build:

```bash
./python -m test -j4 \
    test_gc \
    test_gc_ws_deque \
    test_gc_parallel \
    test_gc_parallel_properties \
    test_capi.test_config \
    test_embed
```

Run the corresponding free-threaded set in its build directory:

```bash
./python -m test -j4 \
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

Parallel collection is off unless enabled through the `gc` module. There is no
environment-variable, `-X`, or `PyConfig` startup control.

```python
import gc

gc.enable_parallel()
config = gc.get_parallel_config()
gc.disable_parallel()
```

`gc.enable_parallel()` creates a pool with a fixed maximum of 16 workers. In a
GIL build the collecting thread coordinates the helpers. In a free-threaded
build it participates as worker zero, so the pool creates exactly one fewer
helper. The shared stochastic hill climber starts at four workers, tries
adjacent counts, and retains only improvements within the 2--16 range. In a
build without parallel-GC support,
`gc.enable_parallel()` and `gc.disable_parallel()` raise
`RuntimeError`, while `gc.get_parallel_config()` reports `available` as false.

## What runs in parallel

| Collector | Parallel phases | Serial phases |
|-----------|-----------------|---------------|
| GIL | interpreter-root marking, reference subtraction, reachability marking | list movement, finalization, deallocation |
| Free-threaded | root propagation, `update_refs`, `mark_heap`, `scan_heap` | finalization, deallocation |

For the free-threaded collector, page assignment prepares buckets for the
parallel heap phases. The collector scans thread stacks serially between
parallel `update_refs` and `mark_heap` to account for deferred references.
Parallel `scan_heap` restores object state and creates the unreachable
worklists.

The implementation remains stop-the-world. “Parallel” refers to collector work
performed by the collecting thread and helper threads during that pause; it
does not mean collection runs concurrently with application threads.

GIL helpers create and bind persistent `PyThreadState` objects. Free-threaded
helpers also own persistent thread states; they install those states in
thread-local storage while running collector work, without performing a full
bind. This supports debug-build reference accounting when a `tp_traverse`
implementation changes a reference count.

## Fork behavior

Fork lifecycle behavior has not yet been validated. The restored baseline does
not install special parallel-GC fork hooks; this is an explicit verification
item rather than a claimed property.

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
| `Python/gc_free_threading_parallel.c` | Free-threaded parallel collector phases |
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
