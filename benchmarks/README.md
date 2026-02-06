# Parallel GC Benchmarks

Performance benchmarks for CPython's parallel garbage collector.

## Scripts

| Script | What it measures | Runtime |
|--------|-----------------|---------|
| `gc_perf_benchmark.py` | Collection time and throughput across heap types and worker counts | ~5 min (standard), ~1 min (--quick), ~15 min (--full) |
| `gc_production_experiment.py` | Cyclic garbage production and collection under realistic workloads | ~5 min |
| `gc_locality_benchmark.py` | Cache and NUMA locality effects on parallel GC scaling | ~2 min |
| `gc_creation_analysis.py` | Object creation patterns and their impact on parallel GC | ~3 min |

## How to Run

Build an optimised free-threaded CPython with parallel GC:

```bash
cd cpython
make clean
./configure --with-parallel-gc --disable-gil --enable-optimizations --with-lto
make -j$(nproc)
```

Run the main benchmark:

```bash
# Quick smoke test
./python ../benchmarks/gc_perf_benchmark.py --quick

# Standard suite (recommended for publication)
./python ../benchmarks/gc_perf_benchmark.py --workers 8 --heap-size 1000000

# Full suite with synthetic workloads
./python ../benchmarks/gc_perf_benchmark.py --full --include-synthetic

# Save results as JSON
./python ../benchmarks/gc_perf_benchmark.py --json -o results/my_results.json
```

Run other benchmarks:

```bash
# Locality analysis
./python ../benchmarks/gc_locality_benchmark.py --size 1000000 --workers 8

# Production workload simulation
./python ../benchmarks/gc_production_experiment.py

# Object creation analysis
./python ../benchmarks/gc_creation_analysis.py --all-phases
```

## How to Interpret Results

### Collection Time (Nx speedup)

The primary metric. Measures wall-clock time for a single `gc.collect()` call on a pre-built heap. Reported as `serial_time / parallel_time`:

- **1.0x** = no speedup (parallel overhead equals parallelism gains)
- **2.0x** = parallel collection is twice as fast
- **< 1.0x** = parallel is slower (overhead exceeds gains, typically on small heaps)

### STW Pause Reduction

Stop-the-world pause time reduction percentage. Measures the total time all application threads are blocked during GC. Lower is better.

### Throughput (ops/sec)

Operations per second in a workload that continuously creates and collects objects. Captures the combined effect of collection speedup and parallel GC overhead on sustained performance.

## Heap Types

| Heap Type | Structure | Parallelism |
|-----------|-----------|-------------|
| `chain` | Linked list (worst case) | Poor — pointer-chasing limits parallelism |
| `tree` | Binary tree | Good — independent subtrees |
| `wide_tree` | Wide tree (high fan-out) | Best — many independent branches |
| `graph` | Random graph | Good — varied connectivity |
| `independent` | Disconnected objects | Good — no cross-references |
| `ai_workload` | Tensor-like clusters | Realistic — mixed structure |
| `web_server` | Request/response simulation | Realistic — session-based |
| `layered` | Layered architecture | Moderate — layer dependencies |

## Methodology

- **Seeds**: All collection benchmarks use `random.seed(42)` for reproducible heap construction. `gc_production_experiment.py` uses deterministic workloads (no randomness).
- **Warmup**: Each benchmark discards warmup iterations before measurement (3 warmup + 5 measured in `gc_perf_benchmark.py`, configurable in others).
- **Statistics**: Results report mean and standard deviation via `statistics.mean`/`statistics.stdev`. Coefficient of variation (CV) is reported for high-variance heap types.
- **Same-binary comparison**: Parallel vs serial comparisons use the same Python binary — `gc.enable_parallel(N)` vs `gc.disable_parallel()` — not different builds.
- **Isolation**: `gc_perf_benchmark.py`, `gc_locality_benchmark.py`, and `gc_production_experiment.py` run in-process with heaps rebuilt between measurements. `gc_creation_analysis.py` uses subprocess isolation (`--subprocess` mode) for clean GC state per configuration.

## Hardware Requirements

- Minimum: 4 cores, 4 GB RAM
- Recommended: 8+ cores, 16 GB RAM
- Published results: Intel Xeon Platinum 8339HC, 192 CPUs, 4 NUMA nodes

## Build Flags for Published Results

```
./configure --with-parallel-gc --disable-gil --enable-optimizations --with-lto
```

This produces a PGO+LTO optimised free-threaded build. Debug builds (`--with-pydebug`) are significantly slower and not suitable for performance comparison.

## Results Directory

`results/` contains benchmark output from Intel Xeon runs:

| File | Configuration |
|------|--------------|
| `intel_1m_w8.json/txt` | 1M objects, 8 workers (current, seed=42) |
| `intel_1m_w8_run1.json/txt` | 1M objects, 8 workers (independent run) |
| `intel_locality_1m.txt` | Locality analysis, 1M objects |
| `system_info.txt` | Hardware and build configuration |
| `archive/` | Earlier runs (500K/w8, 1M/w8, 1M/w16) |
