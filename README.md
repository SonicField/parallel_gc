# Parallel Garbage Collection for CPython

A parallel garbage collector for CPython 3.15+, supporting both GIL (default) and free-threaded builds. Worker threads use work-stealing deques to parallelise the mark-sweep phases, reducing stop-the-world pause times on large heaps.

## What This Is

This repository contains a CPython fork (`cpython/` subdirectory, branch `parallel-gc-dev`) with parallel GC implementations:

- **GIL build** (`Python/gc_parallel.c`) — parallelises subtract_refs, mark_alive, and mark phases during stop-the-world GC pauses
- **Free-threaded build** (`Python/gc_free_threading_parallel.c`) — parallelises update_refs and mark_heap during stop-the-world pauses, using atomics for coordination between GC worker threads

Both share the same core design: Chase-Lev work-stealing deques, coordinator-based termination detection, and barrier synchronisation.

## How to Build

### GIL build (with parallel GC)

```bash
cd cpython
./configure --with-parallel-gc
make -j$(nproc)
```

### Free-threaded build (with parallel GC)

```bash
cd cpython
./configure --with-parallel-gc --disable-gil
make -j$(nproc)
```

**Switching between modes requires `make distclean`** — the object files, `pyconfig.h`, and `config.status` are incompatible.

### Optimised build (for benchmarking)

```bash
cd cpython
./configure --with-parallel-gc --disable-gil --enable-optimizations --with-lto
make -j$(nproc)
```

## How to Use

**Command line:**
```bash
./python -X parallel_gc=4 your_script.py
```

**Environment variable:**
```bash
PYTHONPARALLELGC=8 ./python your_script.py
```

**Python API:**
```python
import gc

gc.enable_parallel(4)       # Enable with 4 workers
stats = gc.get_parallel_stats()  # Per-phase timing, per-worker stats
gc.disable_parallel()       # Revert to serial collection
```

## How to Test

```bash
cd cpython

# Core GC tests
./python -m test test_gc -v

# Parallel GC tests
./python -m test test_gc_parallel -v
./python -m test test_gc_parallel_mark_alive -v
./python -m test test_gc_ws_deque -v
```

**Both build modes must pass all tests.** Run the test suite in both GIL and free-threaded configurations before considering a change complete.

## How to Benchmark

```bash
cd cpython

# Quick smoke test
./python ../benchmarks/gc_perf_benchmark.py --quick

# Full benchmark suite
./python ../benchmarks/gc_perf_benchmark.py --full
```

Benchmark scripts in `benchmarks/`:

| Script | What it measures |
|--------|-----------------|
| `gc_perf_benchmark.py` | Collection time vs workers and heap size |
| `gc_creation_analysis.py` | Object creation overhead |
| `gc_locality_benchmark.py` | Cache/NUMA effects on scaling |
| `gc_production_experiment.py` | Realistic workload simulation |

## Results Summary

On an optimised (PGO+LTO) free-threaded build with 1M objects, 8 workers (Intel Xeon Platinum 8339HC, 192 CPUs):

| Heap Type | Collection Speedup |
|-----------|-------------------|
| Chain (linked list) | 1.89x |
| Tree (binary) | 1.33x |
| Wide tree | 1.37x |
| Graph (random) | 2.33x |
| Layered | 1.45x |
| Independent | 1.23x |
| AI workload | 1.43x |
| Web server | 1.32x |

Stop-the-world pause reduction: -54% to -67% on realistic workloads. Synthetic throughput: +31% geomean. Speedup depends on heap structure, object count, and available cores. Run-to-run variance is significant on some heap types (CV 14-23%) due to cache and NUMA sensitivity.

Results from two independent runs with fixed seeds (seed=42) and 5 iterations each. See `benchmarks/results/` for full data.

## Key Files

| File | Purpose |
|------|---------|
| `cpython/Python/gc_parallel.c` | GIL parallel GC implementation |
| `cpython/Python/gc_free_threading_parallel.c` | Free-threaded parallel GC implementation |
| `cpython/Include/internal/pycore_gc_parallel.h` | GIL parallel GC data structures |
| `cpython/Include/internal/pycore_gc_ft_parallel.h` | Free-threaded parallel GC data structures |
| `cpython/Include/internal/pycore_gc_barrier.h` | Shared barrier implementation |
| `cpython/Modules/gcmodule.c` | Python-level gc module API |

## Documentation

- [Getting Started](docs/GETTING_STARTED.md) — quick start, API reference, repository layout, reading order
- [Architecture Guide](docs/ARCHITECTURE.md) — GIL and FTP collector internals, shared infrastructure, invariants
- [Build and Test Guide](docs/BUILD_AND_TEST.md) — all build configurations, test suites, development workflow
- [Benchmarking Guide](docs/BENCHMARKING.md) — benchmark scripts, expected results, methodology
- [Design Post](docs/DESIGN_POST.md) — technical deep dive, algorithms, divergence from CinderX
- [PEP Outline](docs/PEP_OUTLINE.md) — draft PEP structure and rationale

## Platform Support

Tested on Linux x86_64. Windows and macOS builds are not yet tested and may require platform-specific work (thread primitives, CPU pause instructions).

## Links

- **Fork:** https://github.com/SonicField/cpython
- **Branch:** `parallel-gc-dev`
- **Upstream:** https://github.com/python/cpython
