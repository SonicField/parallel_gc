# Getting Started with Parallel GC for CPython

This project adds an optional parallel cyclic collector to GIL and
free-threaded CPython builds. The two implementations share deque and
synchronization primitives, but have separate worker pools and integrate with
different serial collectors.

## Understand the two repositories

The project has two necessary parts:

- `SonicField/cpython` contains the implementation and the material that could
  ultimately be proposed to CPython: core source, build integration, focused
  correctness tests, and CPython-facing documentation. It is checked out here
  as the `cpython/` submodule.
- `SonicField/parallel_gc` contains the specialist performance laboratory:
  benchmark workloads and harnesses, raw results, reproducibility records,
  design documents, and project-level CI. It records the exact CPython commit
  to which each body of evidence applies.

This split is deliberate. Collector performance depends on heap shape, cyclic
garbage volume, collection frequency, pause behavior, sustained application
load, and adaptive worker selection. General-purpose suites such as
`pyperformance` are valuable broad regression checks, but do not reliably
exercise or observe those conditions. The larger GC-specific benchmark system
is essential to evaluating this project, while being too specialised and
experimental for the CPython source tree.

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
`SonicField/cpython` commit `84be8d65bef72ff98c68a0e6523503ff039b21c8`, on
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
`'available': True`. `num_workers` is the fixed ceiling; while enabled,
`adaptive_workers` is the count currently selected by the controller.

Run the focused tests in the GIL build:

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

Run the corresponding free-threaded set in its build directory:

```bash
./python -m test -j4 \
    test_gc \
    test_gc_ws_deque \
    test_gc_parallel \
    test_gc_parallel_fork \
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
stats = gc.get_parallel_stats()
gc.collect_async()
gc.disable_parallel()
```

`gc.enable_parallel()` creates a pool with a fixed maximum of 16 workers. In a
GIL build the collecting thread coordinates the helpers. In a free-threaded
build it participates as worker zero, so the pool creates exactly one fewer
helper. The shared stochastic random-walk controller starts at four workers,
tries adjacent counts, and walks back after a regression within the 2--16
range. In a build without parallel-GC support,
`gc.enable_parallel()` and `gc.disable_parallel()` raise
`RuntimeError`, while `gc.get_parallel_config()` reports `available` as false.

`gc.get_parallel_stats()` reports implementation diagnostics and private phase
timings. `gc.collect_async()` schedules the ordinary collector and returns
without waiting; it does not enable parallel collection. Both are part of the
current experimental API and remain subject to core-developer review.

## What runs in parallel

| Collector | Parallel phases | Serial phases |
|-----------|-----------------|---------------|
| GIL, at least 16,384 candidates | interpreter-root pre-marking, reference subtraction, reachability marking | initial count/split walk, list reconstruction, finalization, deallocation |
| GIL, fewer than 16,384 candidates | none | complete collection |
| Free-threaded | root propagation, `update_refs`, `mark_heap`, `scan_heap` | finalization, deallocation |

For the free-threaded collector, page assignment prepares buckets for the
parallel heap phases. The collector scans thread stacks serially between
parallel `update_refs` and `mark_heap` to account for deferred references.
Parallel `scan_heap` restores object state and creates the unreachable
worklists.

Reachability analysis remains stop-the-world. “Parallel” refers to collector
work performed by the collecting thread and helpers; it does not mean that
heap marking runs concurrently with application threads. The free-threaded
collector resumes application threads around callbacks, finalizers, and final
deallocation, so its complete callback interval is broader than a single
stop-the-world pause.

GIL helpers create and bind persistent `PyThreadState` objects. Free-threaded
helpers also own persistent thread states; they install those states in
thread-local storage while running collector work, without performing a full
bind. This supports debug-build reference accounting when a `tp_traverse`
implementation changes a reference count.

## Fork behavior

Supported CPython forks leave the parent pool and its adaptive history intact.
The child replaces inherited helpers and synchronization state, resets its
adaptive controller to four workers, and excludes an inherited in-progress
collection from adaptive learning. This includes a fork from `__del__`. See
[FORK_ARCHITECTURE.md](FORK_ARCHITECTURE.md) for the precise contract, hook
ordering, tests, and unsupported raw-fork case.

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
| `cpython/Python/gc_parallel.c` | GIL parallel collector |
| `cpython/Python/gc_free_threading_parallel.c` | Free-threaded parallel collector phases |
| `cpython/Python/gc.c` | GIL integration |
| `cpython/Python/gc_free_threading.c` | Free-threaded integration |
| `cpython/Include/internal/pycore_ws_deque.h` | Work-stealing deque and local buffer |
| `cpython/Include/internal/pycore_gc_barrier.h` | Worker synchronization |
| `cpython/Modules/gcmodule.c` | Runtime API |

## Reading order

1. [Architecture](ARCHITECTURE.md) for control flow and invariants.
2. [Fork Architecture](FORK_ARCHITECTURE.md) for process-lifecycle behavior.
3. [Build and Test](BUILD_AND_TEST.md) for the validation matrix.
4. [Benchmarking](BENCHMARKING.md) for measurement requirements.
5. [Design Post](DESIGN_POST.md) for algorithm background.
6. [PEP draft](pep-parallel-gc.rst) for the proposed upstream interface.

## Performance status

Current optimized PGO+LTO measurements on Linux AArch64 show 1.26x and 1.22x
geometric-mean speedups across eight requested 500,000-object heaps for the GIL
and free-threaded builds respectively. Mixed-workload throughput was -0.2% for
GIL and +19.5% for free-threaded. Sustained workloads include a known negative
region: the free-threaded finalizer-heavy case regressed by 14.7%. These are
same-binary serial/parallel measurements, not universal performance claims.
See [BENCHMARKING.md](BENCHMARKING.md) for full results and interpretation.
