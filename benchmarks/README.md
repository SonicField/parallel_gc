# Parallel GC Benchmarks

Performance benchmarks for CPython's parallel garbage collector.

## Scripts

| Script | What it measures |
|--------|------------------|
| `gc_perf_benchmark.py` | Mixed-workload throughput; optional synthetic collection and throughput tests with adaptive workers |
| `gc_adaptive_benchmark.py` | Worker-controller response across changing workload phases |
| `gc_production_experiment.py` | Cyclic garbage production and collection under realistic workloads |
| `gc_locality_benchmark.py` | Serial/parallel comparison for contiguous circular chains |
| `gc_creation_analysis.py` | Object creation patterns and their impact on parallel GC |

Runtime depends on the selected duration, number of samples, heap size, and
whether synthetic tests are enabled.

## How to Run

Build separate optimized GIL and free-threaded CPython interpreters with
parallel GC:

```bash
git clone --recurse-submodules https://github.com/SonicField/parallel_gc.git
cd parallel_gc
mkdir -p build-benchmark-gil build-benchmark-ft
(cd build-benchmark-gil && ../cpython/configure \
    --with-parallel-gc --enable-optimizations --with-lto)
make -C build-benchmark-gil -j"$(nproc)"
(cd build-benchmark-ft && ../cpython/configure \
    --with-parallel-gc --disable-gil --enable-optimizations --with-lto)
make -C build-benchmark-ft -j"$(nproc)"
```

Run the main benchmark:

```bash
# Quick smoke test
build-benchmark-gil/python benchmarks/gc_perf_benchmark.py --quick
build-benchmark-ft/python benchmarks/gc_perf_benchmark.py --quick

# Standard mixed-workload run
<build>/python benchmarks/gc_perf_benchmark.py

# Longer run with synthetic workloads; --full alone does not enable them
<build>/python benchmarks/gc_perf_benchmark.py --full --include-synthetic

# Save results as JSON
<build>/python benchmarks/gc_perf_benchmark.py --json \
    -o benchmarks/results/my_results.json
```

Run other benchmarks:

```bash
# Locality analysis
<build>/python benchmarks/gc_locality_benchmark.py --size 1000000

# Production workload simulation
<build>/python benchmarks/gc_production_experiment.py

# Object creation analysis
<build>/python benchmarks/gc_creation_analysis.py --comparison
```

## How to Interpret Results

### Collection Time (Nx speedup)

The primary metric. Measures wall-clock time for a single `gc.collect()` call on a pre-built heap. Reported as `serial_time / parallel_time`:

- **1.0x** = no speedup (parallel overhead equals parallelism gains)
- **2.0x** = parallel collection is twice as fast
- **< 1.0x** = parallel is slower (overhead exceeds gains, typically on small heaps)

### Collection Latency

Serial and parallel values both use the wall-clock interval between the
``gc.callbacks`` start and stop events, so their definitions match. This is
the full callback span, not the strictly stop-the-world portion of a
free-threaded collection.

### Throughput (ops/sec)

Operations per second in a workload that continuously creates and collects objects. Captures the combined effect of collection speedup and parallel GC overhead on sustained performance.

## Heap Types

| Heap Type | Structure |
|-----------|-----------|
| `chain` | Circular linked-list clusters |
| `tree` | Binary trees with back-references |
| `wide_tree` | Wide trees with high fan-out |
| `graph` | Random cyclic graphs |
| `independent` | Disconnected self-referencing clusters |
| `ai_workload` | Tensor-like clusters |
| `web_server` | Request/response and session clusters |
| `layered` | Layered graphs |

## Methodology

- **Seeds**: `gc_perf_benchmark.py` uses deterministic per-worker random
  streams seeded from 42, so thread scheduling does not change another
  worker's heap or workload sequence. Other multi-threaded tools still use the
  process-global generator and must not claim paired heap identity from the
  seed alone. `gc_production_experiment.py` uses deterministic workloads.
- **Warmup**: `gc_perf_benchmark.py` uses 3 fixed warmups for each collection
  configuration and measures 3 samples by default (5 with `--full`). Other
  scripts have their own settings.
- **Statistics**: Results report mean and standard deviation via
  `statistics.mean` and `statistics.stdev`, and retain every raw sample.
- **Same-binary comparison**: Parallel vs serial comparisons use the same
  Python binary — `gc.enable_parallel()` versus `gc.disable_parallel()` — not
  different builds.
- **Worker selection**: The pool has a fixed ceiling of 16. The adaptive
  controller starts at four active workers and selects the active count for
  subsequent collections.
- **Heap construction**: Serial and parallel collection passes rebuild
  equivalent heaps; they do not collect the same heap twice.
- **Run order**: `gc_perf_benchmark.py` alternates measured serial and parallel
  runs to reduce systematic drift.
- **Isolation**: `gc_perf_benchmark.py`, `gc_locality_benchmark.py`, and
  `gc_production_experiment.py` run in-process. `gc_creation_analysis.py` uses
  subprocesses for clean GC state per configuration.

## Performance Build Flags

```
./configure --with-parallel-gc --enable-optimizations --with-lto
./configure --with-parallel-gc --disable-gil --enable-optimizations --with-lto
```

These produce PGO+LTO optimized GIL and free-threaded builds. Debug builds
(`--with-pydebug`) are not suitable for performance comparison. Publishable
results must record the exact CPython commit, command line, compiler, affinity,
NUMA policy, repository dirty state, configured ceiling and observed adaptive
worker counts, all raw samples,
and every rerun.

## Results Directory

No current-port result set has been published. New results belong under
`results/` only when they include the source revisions, build configuration,
machine metadata, command line, raw samples, and variance.

Run the harness regressions with:

```bash
<build>/python -m unittest -v benchmarks.test_gc_perf_benchmark
```
