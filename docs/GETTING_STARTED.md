# Getting Started with Parallel GC for CPython

## What Is This?

This project adds an optional parallel garbage collector to CPython 3.15+. It targets the cyclic GC's mark-sweep phases -- the most expensive part of garbage collection on large heaps. Two independent implementations exist: one for GIL builds (default CPython) and one for Free-Threaded builds (`--disable-gil`). Both use Chase-Lev work-stealing deques to distribute marking work across multiple threads, reducing stop-the-world pause times by 54--67% on heaps with 1M+ tracked objects. Parallel collection is **opt-in** via `gc.enable_parallel(N)` -- serial collection remains the default, and the parallel path only activates when the heap is large enough to benefit.

---

## 5-Minute Quick Start

### 1. Build

```bash
git clone https://github.com/SonicField/cpython.git
cd cpython
git checkout parallel-gc-dev

# Free-threaded build (recommended for evaluation)
./configure --with-parallel-gc --disable-gil
make -j$(nproc)
```

Or, if you already have the outer repository checked out:

```bash
cd /path/to/parallel_gc/cpython
./configure --with-parallel-gc --disable-gil
make -j$(nproc)
```

### 2. Verify it works

```bash
./python -c "
import gc
gc.enable_parallel(4)
print(gc.get_parallel_config())
gc.collect()
print(gc.get_parallel_stats())
gc.disable_parallel()
print('OK')
"
```

You should see `'enabled': True, 'num_workers': 4` in the config output, and per-worker statistics after collection.

### 3. Run the tests

```bash
./python -m test test_gc test_gc_parallel test_gc_ft_parallel test_gc_ws_deque -v
```

### 4. See it in action

```bash
# Quick benchmark (~1 minute)
./python ../benchmarks/gc_perf_benchmark.py --quick
```

---

## Repository Layout

```
parallel_gc/
  cpython/                              CPython fork (branch: parallel-gc-dev)
    Python/
      gc_parallel.c                     GIL build: parallel mark-sweep
      gc_free_threading_parallel.c      FTP build: parallel GC over mimalloc pages
      gc.c                              GIL build: serial GC (integration points)
      gc_free_threading.c               FTP build: serial GC (integration points)
    Include/internal/
      pycore_gc_parallel.h              GIL build: data structures, API
      pycore_gc_ft_parallel.h           FTP build: data structures, page buckets
      pycore_ws_deque.h                 Chase-Lev work-stealing deque (shared)
      pycore_gc_barrier.h               Barrier synchronisation (shared)
    Modules/
      gcmodule.c                        Python API: enable/disable/config/stats
    Lib/test/
      test_gc_parallel.py               Parallel GC integration tests (FTP)
      test_gc_ft_parallel.py            FTP-specific internals (pages, atomics)
      test_gc_parallel_mark_alive.py    Mark-alive phase tests (GIL)
      test_gc_parallel_properties.py    Property-based invariant tests (FTP)
      test_gc_ws_deque.py               Work-stealing deque unit tests

  docs/
    GETTING_STARTED.md                  This file
    ARCHITECTURE.md                     GIL and FTP collector internals, invariants
    BUILD_AND_TEST.md                   All build configs, test suites, debugging
    BENCHMARKING.md                     Benchmark scripts, expected results, methodology
    DESIGN_POST.md                      Technical blog post: algorithm details
    PEP_OUTLINE.md                      Draft PEP for CPython upstream

  benchmarks/
    gc_perf_benchmark.py                Collection time and throughput
    gc_production_experiment.py         Realistic workload simulation
    gc_locality_benchmark.py            Cache/NUMA locality effects
    gc_creation_analysis.py             Object creation patterns
    results/                            Published benchmark data (JSON + text)
    README.md                           Benchmark methodology and usage

  tools/
    setup_environment.sh                First-time dev environment setup
    build_all_configs.sh                Build GIL, FTP, debug, and optimised configs
    run_tests.sh                        Quick test runner across build configs
```

---

## Reading Order

If you are reviewing or continuing this work, read the documentation in this order:

| Order | Document | What you get from it |
|-------|----------|---------------------|
| 1 | **GETTING_STARTED.md** (you are here) | Orientation, quick start, API reference, where everything lives |
| 2 | [ARCHITECTURE.md](ARCHITECTURE.md) | Deep dive: GIL and FTP collector internals, shared infrastructure, invariants, CinderX heritage |
| 3 | [BUILD_AND_TEST.md](BUILD_AND_TEST.md) | All build configurations, test suites, debugging, development workflow |
| 4 | [BENCHMARKING.md](BENCHMARKING.md) | Benchmark scripts, expected results, methodology, hardware requirements |
| 5 | [DESIGN_POST.md](DESIGN_POST.md) | Technical blog post: algorithm details, work distribution, divergence from CinderX |
| 6 | [PEP_OUTLINE.md](PEP_OUTLINE.md) | Draft PEP: motivation, API specification, rejected alternatives |

ARCHITECTURE.md is the most important document for code reviewers -- it covers the full architecture of both collectors, integration points, and correctness invariants.

---

## Key Concepts

These are the core ideas that appear throughout the codebase. Each is explained fully in [DESIGN_POST.md](DESIGN_POST.md).

**Chase-Lev work-stealing deque** -- A lock-free double-ended queue (defined in `pycore_ws_deque.h`). Each worker pushes/pops from the bottom (LIFO, cache-friendly); idle workers steal from the top (FIFO, fair). Based on Chase & Lev 2005, with Le et al. 2013 weak-memory corrections.

**Split vector** -- An array of pointers into the GC list, recorded at 8192-object intervals (`_PyGC_SPLIT_INTERVAL`) during `update_refs`. Divides the heap into segments for parallel processing while preserving allocation-order locality. Used by the GIL build only.

**Fetch-And atomic marking** -- GIL build objects are marked reachable by atomically clearing the `COLLECTING` bit in `_gc_prev` using `atomic_and` (not CAS). A preceding relaxed load filters already-marked objects cheaply (~10x cheaper than atomic RMW). Always succeeds in one operation -- no retry loop.

**Relaxed-atomic marking** -- The FTP build marks objects using relaxed load + relaxed store on `ob_gc_bits`. If two workers race to mark the same object, both write `ALIVE` (idempotent) and both traverse referents; duplicates terminate at the next level's relaxed-read check. Costs ~2-3 cycles vs ~20-40 for atomic RMW.

**Barrier synchronisation** -- Workers synchronise between phases using an epoch-based counting barrier (defined in `pycore_gc_barrier.h`), built on `PyMUTEX_T` and `PyCOND_T`. Handles spurious wakeups correctly. Shared by both GIL and FTP builds.

**Local buffer** -- A small per-worker staging area (`_PyGCLocalBuffer`) between `tp_traverse` callbacks and the deque. Pushes/pops are simple array operations with zero memory fences; the buffer is flushed to the deque only when full, amortising atomic operation costs.

**Page-based distribution (FTP)** -- The FTP build distributes work by mimalloc pages, not by GC list position. Pages are enumerated in O(pages) time and assigned to worker buckets. Normal pages use sequential filling for locality; huge pages use round-robin to spread expensive traversals.

**Coordinator-based termination** -- When a worker exhausts local work and cannot steal, it attempts to become the coordinator (via mutex election). The coordinator polls all deques and either wakes idle workers via counting semaphore (if work exists) or signals termination (if all deques are empty).

**GIL build phases** -- Four phases run inside `deduce_unreachable()`: (1) **mark_alive** pre-marks objects reachable from interpreter roots; (2) **subtract_refs** decrements gc_refs for internal references using atomic decrements over split-vector segments; (3) **mark** finds residual GC roots (gc_refs > 0) and marks locally; (4) **sweep** (serial) moves unmarked objects to the unreachable list.

**FTP build phases** -- Four phases: (1) **mark_alive** pre-marks objects reachable from interpreter roots (runs before deduce_unreachable_heap); (2) **UPDATE_REFS** initialises gc_refs from reference counts over page buckets; (3) **MARK_HEAP** finds residual roots (gc_refs > 0) and marks reachable objects; (4) **SCAN_HEAP** collects unreachable objects into per-worker worklists, then merges.

---

## Two Build Modes

Parallel GC is opt-in via the `--with-parallel-gc` configure flag, which defines `Py_PARALLEL_GC`. Both GIL and free-threaded builds use the same flag.

| | GIL Build | Free-Threaded (FTP) Build |
|---|-----------|--------------------------|
| **Configure** | `./configure --with-parallel-gc` | `./configure --with-parallel-gc --disable-gil` |
| **Compile guard** | `Py_PARALLEL_GC` | `Py_GIL_DISABLED && Py_PARALLEL_GC` |
| **Implementation** | `gc_parallel.c` | `gc_free_threading_parallel.c` |
| **Header** | `pycore_gc_parallel.h` | `pycore_gc_ft_parallel.h` |
| **Object marking** | Fetch-And on `_gc_prev` | Relaxed read/store on `ob_gc_bits` |
| **gc_refs storage** | Upper bits of `_gc_prev` | `ob_tid` (repurposed during STW) |
| **Work distribution** | Split vector (GC list intervals) | Page-based (mimalloc pages) |
| **GC phases** | mark_alive, subtract_refs, mark, sweep | mark_alive, UPDATE_REFS, MARK_HEAP, SCAN_HEAP |

**Switching between modes requires `make clean`** -- the object files and configuration are incompatible.

For optimised builds suitable for benchmarking:

```bash
./configure --with-parallel-gc --disable-gil --enable-optimizations --with-lto
make -j$(nproc)
```

Note: PGO may fail on `test_sqlite3`. Work around this by passing the profile task explicitly:

```bash
make -j$(nproc) PROFILE_TASK="-m test --pgo -x test_sqlite3"
```

---

## Python API

### Enable and Disable

```python
import gc

gc.enable_parallel(num_workers=4)   # Start 4 worker threads
gc.disable_parallel()               # Destroy workers, revert to serial
```

### Query Configuration

```python
gc.get_parallel_config()
# FTP build:
# {'available': True, 'enabled': True, 'num_workers': 4, 'parallel_cleanup': True}
#
# GIL build (with adaptive controller):
# {'available': True, 'enabled': True, 'num_workers': 4,
#  'adaptive_workers_gen0': 3, 'adaptive_workers_gen1': 4, 'adaptive_workers_gen2': 5,
#  'epsilon': 0.05}
```

The GIL build exposes the stochastic hill-climbing controller state:
- `adaptive_workers_genN`: current worker count the controller has chosen for generation N
- `epsilon`: exploration probability (starts at 0.3, decays to floor of 0.05)

### Collection Statistics

The output of `gc.get_parallel_stats()` differs between build modes.

**FTP build:**

```python
gc.get_parallel_stats()
# {'enabled': True, 'num_workers': 4,
#  'phase_timing': {
#      'stw0_ns': ..., 'merge_refs_ns': ..., 'delayed_frees_ns': ...,
#      'mark_alive_ns': ..., 'bucket_assign_ns': ...,
#      'update_refs_ns': ..., 'mark_heap_ns': ..., 'scan_heap_ns': ...,
#      'total_ns': ..., ...
#  }}
```

**GIL build:**

```python
gc.get_parallel_stats()
# {'enabled': True, 'num_workers': 4,
#  'roots_found': 142, 'roots_distributed': 8703,
#  'gc_roots_found': 0,
#  'collections_attempted': 5, 'collections_succeeded': 5,
#  'ema_per_obj_ns_gen0': 1850.1, 'ema_per_obj_ns_gen1': 100.0,
#  'ema_per_obj_ns_gen2': 2903265.5,
#  'last_generation': 2,
#  'workers': [...],    # per-worker stats
#  'phase_timing': {
#      'update_refs_ns': ..., 'mark_alive_ns': ...,
#      'subtract_refs_ns': ..., 'mark_ns': ...,
#      'total_ns': ..., ...
#  }}
```

The `ema_per_obj_ns_genN` keys report the exponential moving average of
per-object collection cost for each generation (used by the adaptive
controller). `last_generation` is the generation of the most recent collection.

The exact keys depend on the build mode. Use `sorted(gc.get_parallel_stats().keys())` to see what is available in your build.

### Command-Line and Environment Variable

```bash
# -X flag
./python -X parallel_gc=4 your_script.py

# Environment variable
PYTHONPARALLELGC=8 ./python your_script.py
```

All three methods (API, `-X` flag, environment variable) are equivalent. The API allows enabling/disabling at runtime; the other two activate parallel GC at interpreter startup.

---

## Performance Summary

Measured on an optimised (PGO+LTO) free-threaded build, 8 workers, 1M objects, Intel Xeon Platinum 8339HC (192 CPUs). Fixed seed (42), 5 iterations per run, conservative (worst-of-two-runs) numbers reported.

### Collection Speedup by Heap Type

| Heap Type | Speedup | Notes |
|-----------|---------|-------|
| Chain (linked list) | 1.89x | Pointer-chasing limits parallelism |
| Tree (binary) | 1.33x | Independent subtrees |
| Wide tree (high fan-out) | 1.37x | Many independent branches |
| Graph (random) | 2.33x | Best case -- varied connectivity |
| Layered | 1.45x | Layer dependencies limit scaling |
| Independent (disconnected) | 1.23x | No cross-references |
| AI workload (tensor clusters) | 1.43x | Realistic mixed structure |
| Web server (sessions) | 1.32x | Realistic session-based |

### Summary Metrics

| Metric | Value |
|--------|-------|
| STW pause reduction | -54% to -67% on realistic workloads |
| Synthetic throughput | +31% geomean |
| Sweet spot | 500K+ tracked objects |
| Break-even | ~100K-300K objects (overhead equals gains) |
| Below break-even | Parallel is slower (0.5x-0.9x) |

Run-to-run variance is significant on some heap types (CV 14-23%) due to cache and NUMA effects. Full data and methodology in [benchmarks/README.md](../benchmarks/README.md) and `benchmarks/results/`.

---

## Key Source Files

### Shared Infrastructure

| File | Purpose | Read first? |
|------|---------|-------------|
| `Include/internal/pycore_ws_deque.h` | Chase-Lev deque + local buffer | Yes |
| `Include/internal/pycore_gc_barrier.h` | Barrier synchronisation (POSIX + Windows) | Yes |

### GIL Build

| File | Purpose |
|------|---------|
| `Include/internal/pycore_gc_parallel.h` | Data structures, worker state, API declarations |
| `Python/gc_parallel.c` | Full implementation: mark_alive, subtract_refs, mark phases |
| `Python/gc.c` | Integration points (search for `Py_PARALLEL_GC`) |

### Free-Threaded Build

| File | Purpose |
|------|---------|
| `Include/internal/pycore_gc_ft_parallel.h` | Data structures, page buckets, thread pool, atomic marking |
| `Python/gc_free_threading_parallel.c` | Full implementation: mark_alive, UPDATE_REFS, MARK_HEAP, SCAN_HEAP |
| `Python/gc_free_threading.c` | Integration points (search for `parallel`) |

### Python API

| File | Purpose |
|------|---------|
| `Modules/gcmodule.c` | `gc.enable_parallel()`, `gc.disable_parallel()`, `gc.get_parallel_config()`, `gc.get_parallel_stats()` |

### Tests

| File | What it tests |
|------|--------------|
| `Lib/test/test_gc_parallel.py` | Parallel GC end-to-end correctness (FTP only) |
| `Lib/test/test_gc_ft_parallel.py` | FTP-specific internals: pages, marking, atomics (FTP only) |
| `Lib/test/test_gc_parallel_mark_alive.py` | Root marking pipeline (GIL only) |
| `Lib/test/test_gc_ws_deque.py` | Work-stealing deque correctness, buffer fallback |
| `Lib/test/test_gc_parallel_properties.py` | Property-based invariant tests (FTP only) |

All files are under `cpython/` in this repository.

---

## Known Limitations and Open Items

- **Opt-in only.** Parallel GC is never auto-enabled. The user must explicitly call `gc.enable_parallel(N)` or use `-X parallel_gc=N` / `PYTHONPARALLELGC=N`. There is no heuristic for choosing N.
- **Linux x86_64 only.** All development and testing has been on Linux x86_64. ARM, macOS, and Windows builds have not been tested and may have portability issues with atomics and thread primitives.
- **No CI.** There is no continuous integration pipeline. Tests are run manually.
- **Meta copyright headers.** `pycore_ws_deque.h` and `pycore_gc_barrier.h` carry Meta copyright from the CinderX port. This requires resolution before upstream submission.
- **Sweep is serial.** The sweep phase runs single-threaded in both build modes. Parallelising sweep is a potential future optimisation.
- **Small-heap overhead.** Below ~100K objects, parallel GC is slower than serial due to thread coordination overhead. The split-vector threshold prevents activation on very small heaps, but the boundary is not finely tuned.
- **Memory cost.** Each worker pre-allocates a 2 MB deque buffer at `gc.enable_parallel()` time. This memory is freed at `gc.disable_parallel()`.

---

## Links

| Resource | URL |
|----------|-----|
| CPython fork | https://github.com/SonicField/cpython |
| Branch | `parallel-gc-dev` |
| Upstream CPython | https://github.com/python/cpython |
| CinderX (design heritage) | https://github.com/facebookincubator/cinder |
| Chase-Lev deque paper | https://dl.acm.org/doi/10.1145/1073970.1073974 |
| Le et al. (weak memory models) | https://dl.acm.org/doi/10.1145/2442516.2442524 |
