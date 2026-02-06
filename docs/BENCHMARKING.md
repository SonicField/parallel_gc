# Benchmarking Guide

How to run benchmarks, interpret results, and what numbers to expect from the parallel GC.

## Quick Start

```bash
cd cpython

# Build optimised (required for meaningful benchmarks)
./configure --with-parallel-gc --disable-gil --enable-optimizations --with-lto
make -j$(nproc)

# Quick sanity check (~1 minute)
./python ../benchmarks/gc_perf_benchmark.py --quick

# Standard run (~5 minutes)
./python ../benchmarks/gc_perf_benchmark.py

# Full run (~15 minutes, 5 iterations, synthetic heaps included)
./python ../benchmarks/gc_perf_benchmark.py --full --include-synthetic
```

---

## Benchmark Scripts

### gc_perf_benchmark.py — Primary Benchmark Suite

The main benchmark measuring parallel GC performance across realistic and synthetic workloads.

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--quick` | Quick sanity check (2 runs, 10s each) | — |
| `--full` | Full suite (5 runs, 60s each) | — |
| `--duration, -d` | Duration per benchmark (seconds) | 30 |
| `--runs, -r` | Number of runs per configuration | 3 |
| `--threads, -t` | Application worker threads | 4 |
| `--workers, -w` | Parallel GC worker count | 8 |
| `--heap-size, -s` | Objects for synthetic benchmarks | 500,000 |
| `--json, -j` | Output JSON instead of markdown | — |
| `--output, -o` | Output file (default: stdout) | — |
| `--verbose, -v` | Include per-phase timing details | — |
| `--include-synthetic` | Include synthetic stress tests | — |

**Realistic workloads (7):**

| Workload | Cycles | Description |
|----------|--------|-------------|
| deltablue | HIGH | Constraint solver, bidirectional references |
| deepcopy | HIGH | Tree copy creating cyclic garbage |
| pickle_copy | HIGH | Serialisation round-trip |
| async_tree | HIGH | Async task tree simulation |
| richards | MINIMAL | OS task scheduler simulation |
| nbody | MINIMAL | N-body physics (compute-heavy) |
| comprehensions | NONE | List/dict/set comprehensions (acyclic) |

**Synthetic heap types (8):**

| Heap Type | Description | Parallelism |
|-----------|-------------|-------------|
| chain | Circular linked lists | Low (sequential) |
| tree | Binary trees with back-references | Medium |
| wide_tree | Single root, many children | Medium |
| graph | Random graphs with cycles | High (best case) |
| layered | Neural-network-like layers | Medium-High |
| independent | Self-referencing isolated clusters | High |
| ai_workload | ML computation graph with finalisers | Medium |
| web_server | HTTP request/response lifecycle | Medium |

**Output metrics:**
- **Throughput** (workloads/sec or objects/sec) — mean, stddev, min/max
- **STW pause** (ms) — mean, max across collections
- **GC overhead** (% of total time)
- **Speedup** — ratio of parallel to serial
- **Geometric mean** — across all heap types

**Examples:**

```bash
# Standard with 8 workers
./python ../benchmarks/gc_perf_benchmark.py --workers 8

# JSON output for automated processing
./python ../benchmarks/gc_perf_benchmark.py --json -o results.json

# Verbose with synthetic heaps
./python ../benchmarks/gc_perf_benchmark.py --full --include-synthetic --verbose
```

### gc_creation_analysis.py — Multi-Threaded Allocation Impact

Investigates how multi-threaded object creation affects parallel GC performance through heap distribution analysis.

**Modes:**

```bash
# Test impact of creation thread count
./python ../benchmarks/gc_creation_analysis.py --creation-threads --heap ai_workload

# Compare chain vs cluster heap structures
./python ../benchmarks/gc_creation_analysis.py --chain-vs-clusters

# Compare abandoned threads vs thread pool
./python ../benchmarks/gc_creation_analysis.py --abandon-vs-pool --heap ai_workload

# Show all GC phase timings (uses subprocess for clean state)
./python ../benchmarks/gc_creation_analysis.py --all-phases --heap ai_workload
```

**Key options:**
- `--threads` — creation threads (default: 1)
- `--size` — objects to create (default: 400,000)
- `--workers` — parallel GC workers (default: 8)
- `--heap` — structure: chain, clusters, ai_workload
- `--survivors` — keep all objects alive (100% survivors)

### gc_locality_benchmark.py — Cache Locality Worst Case

Tests parallel GC on contiguous circular chains — the worst case for parallelisation (high cache locality, sequential traversal).

```bash
./python ../benchmarks/gc_locality_benchmark.py --size 500000 --workers 8 --survivor-ratio 0.8
```

**Options:**
- `--size, -s` — number of objects (default: 500,000)
- `--workers, -w` — parallel GC workers (default: 8)
- `--survivor-ratio, -r` — fraction surviving (default: 0.8 = 20% garbage)
- `--iterations, -i` — timed iterations (default: 5)
- `--warmup` — warmup iterations (default: 2)

### gc_production_experiment.py — Cyclic Garbage Survey

Measures which standard benchmarks actually produce cyclic garbage. Useful for understanding which workloads benefit from parallel GC.

```bash
# Run all 14 benchmarks
./python ../benchmarks/gc_production_experiment.py

# Specific benchmarks
./python ../benchmarks/gc_production_experiment.py --benchmarks deltablue richards

# List available benchmarks
./python ../benchmarks/gc_production_experiment.py --list

# JSON output
./python ../benchmarks/gc_production_experiment.py --output results.json
```

Classifies each benchmark as HIGH_CYCLES, MODERATE_CYCLES, MINIMAL_CYCLES, or NO_CYCLES.

---

## Expected Results

All results below are from an optimised (PGO+LTO) free-threaded build on Intel Xeon Platinum 8339HC (192 CPUs, 4 NUMA nodes), 8 parallel GC workers, 1M objects, fixed seed=42, 5 iterations.

### Collection Time Speedup

| Heap Type | Serial (ms) | Parallel (ms) | Speedup |
|-----------|-------------|---------------|---------|
| Chain | 224.3 | 118.6 | 1.89x |
| Tree | 237.9 | 178.9 | 1.33x |
| Wide tree | 248.2 | 180.6 | 1.37x |
| Graph | 315.0 | 135.5 | **2.33x** |
| Layered | 177.1 | 122.4 | 1.45x |
| Independent | 159.4 | 129.5 | 1.23x |
| AI workload | 193.7 | 135.9 | 1.43x |
| Web server | 157.7 | 119.5 | 1.32x |

### STW Pause Reduction

- **Realistic workloads:** -54% to -67% STW pause reduction
- **Synthetic throughput geometric mean:** +31%

### When Parallel GC Helps

| Heap Size | Expected Speedup |
|-----------|-----------------|
| < 100K objects | 0.5-0.9x (slower — overhead dominates) |
| 100K-300K | 0.9-1.1x (break-even) |
| 300K-500K | 1.1-1.3x (slight win) |
| > 500K | **1.2-2.3x** (clear win) |

### When Parallel GC Does Not Help

- Heaps under 100K objects (overhead exceeds benefit)
- Linear chains or binary trees with limited parallelism in graph structure
- Very short-lived automatic gen-0/gen-1 collections (barrier overhead dominates)

---

## Methodology

### Reproducibility

The collection and throughput benchmarks (`gc_perf_benchmark.py`, `gc_creation_analysis.py`, `gc_locality_benchmark.py`) use `random.seed(42)` for reproducible heap topologies. `gc_production_experiment.py` does not set a fixed seed because its workloads are deterministic (no random heap generation). Results are reported as the **worst-of-two-runs** per heap type — no cherry-picking.

### Run-to-Run Variance

Some heap types show significant run-to-run variance (CV 14-23%) due to cache and NUMA sensitivity:

| Heap Type | Typical CV |
|-----------|-----------|
| Chain | 3-5% |
| Tree | 5-8% |
| Graph | 14-18% |
| Layered | 15-20% |
| AI workload | 14-23% |
| Web server | 12-18% |

This variance is inherent to work-stealing on NUMA hardware. To get stable numbers:

1. Use at least 5 iterations (`--runs 5` or `--full`)
2. Pin to a single NUMA node if possible: `numactl --cpunodebind=0 --membind=0 ./python ...`
3. Run on a quiet machine (no competing workloads)
4. Report geometric mean across heap types, not individual results

### Comparing Serial vs Parallel

The benchmarks run both serial and parallel configurations in the same process, same heap, same seed. This eliminates most sources of measurement noise except cache/NUMA effects.

### What the Numbers Mean

- **Collection speedup:** How much faster a single `gc.collect()` call is with parallel workers. This is the primary metric.
- **STW pause reduction:** How much shorter the application-visible pause is. This matters for latency-sensitive workloads.
- **Throughput change:** Overall application throughput (allocation + collection + work). Usually neutral — parallel GC reduces collection time but doesn't speed up allocation.
- **GC overhead:** Time spent in GC as a percentage of total time. Lower is better.

---

## Benchmark Results Location

Published results are in `benchmarks/results/`:

| File | Contents |
|------|----------|
| `intel_1m_w8.txt` | Summary (8 workers, 1M objects) |
| `intel_1m_w8.json` | Full JSON data |
| `intel_1m_w8_run1.txt/json` | Run 1 data |
| `intel_locality_1m.txt` | Locality benchmark results |
| `system_info.txt` | Hardware and build configuration |

### System Info

The reference results were collected on:

```
CPU: Intel Xeon Platinum 8339HC @ 1.80GHz
Sockets: 4 x 24 cores (96 physical, 192 logical with HT)
NUMA: 4 nodes
L3 cache: 132 MiB (4 x 33 MiB)
Build: Python 3.15.0a2+, --disable-gil --enable-optimizations --with-lto
```

---

## Tips

- **Always use an optimised build** for benchmarking. Debug builds have assertions and Py_REF_DEBUG overhead that distort results.
- **Warm up** before timing. The `--warmup` option (default: 2 iterations) handles this.
- **Don't compare across machines** without documenting hardware. NUMA topology, cache sizes, and core count all affect results.
- **The `--quick` flag** is for sanity checking, not publishable results. Use `--full` for numbers you'll report.
- **JSON output** (`--json`) is machine-readable for automated analysis and regression tracking.
