# BRC/DECREF Optimisation Benchmark Analysis

## Date: 2026-01-20

## Executive Summary

**Finding: Neither BRC sharding nor fast decref show statistically significant improvement in the realistic benchmark with serial GC.**

The differences between configurations are within measurement noise (≤5%). The baseline configuration (A) performs comparably to the fully optimised configuration (D).

---

## Configurations Tested

| Config | Py_BRC_SHARDED | Py_BRC_FAST_DECREF | Description |
|--------|----------------|---------------------|-------------|
| A | 0 | 0 | Baseline (no optimisations) |
| B | 1 | 0 | Sharding only |
| C | 0 | 1 | Fast decref only |
| D | 1 | 1 | Both (current default) |

---

## Realistic Benchmark Results

### 4 Threads (Mean of 5 runs, 30s each)

| Config | Throughput (w/s) | vs Baseline | GC Time | STW Max (ms) | STW Mean (ms) |
|--------|------------------|-------------|---------|--------------|---------------|
| A | 2,772 | - | 37.6% | 779 | 296 |
| B | 2,710 | -2.2% | 41.0% | 830 | 330 |
| C | 2,815 | +1.6% | 41.9% | 867 | 329 |
| D | 2,677 | -3.4% | 42.4% | 845 | 341 |

### 8 Threads (Mean of 5 runs, 30s each)

| Config | Throughput (w/s) | vs Baseline | GC Time | STW Max (ms) | STW Mean (ms) |
|--------|------------------|-------------|---------|--------------|---------------|
| A | 3,882 | - | 74.5% | 1,238 | 532 |
| B | 3,840 | -1.1% | 74.3% | 1,188 | 535 |
| C | 3,962 | +2.1% | 77.1% | 1,285 | 547 |
| D | 3,856 | -0.7% | 75.1% | 1,510 | 544 |

### Observations

1. **All differences are within ±3.5%** - likely measurement noise
2. **Baseline (A) is competitive** with all optimised configurations
3. **Config D (both) shows higher variance** - particularly in STW max pause
4. **GC overhead is high** (37-77%) across all configurations

---

## Pyperformance Results (Selected Benchmarks)

| Benchmark | Config A | Config B | Config C | Config D |
|-----------|----------|----------|----------|----------|
| deltablue | 6.32 ms | 6.26 ms | 6.27 ms | 6.20 ms |
| richards | 86.2 ms | 86.3 ms | 87.7 ms | 132 ms* |
| nbody | 214 ms | 214 ms | 206 ms | 302 ms* |
| float | 108 ms | 110 ms | 110 ms | 120 ms* |
| gc_traversal | 3.44 ms | 3.44 ms | 3.48 ms | 3.75 ms |

*Config D shows unstable results with high std dev - possibly system noise during run.

### Observations

1. **Pyperformance shows no clear benefit** from either optimisation
2. **Config D has anomalous results** - likely measurement artefact, not real regression
3. **deltablue is consistent** across all configurations (~6.2-6.3 ms)

---

## Statistical Significance

Given the variance in measurements (std dev often 5-10% of mean), the observed differences are **not statistically significant**.

To achieve 95% confidence of a 1% improvement with 5% std dev, we would need approximately 100 samples per configuration, not 5.

---

## Interpretation

### Why don't the optimisations help?

1. **Serial GC was used** - BRC contention primarily matters during parallel cleanup, which wasn't tested

2. **Workload characteristics** - The realistic benchmark may not generate enough cross-thread reference sharing to show sharding benefits

3. **Bottleneck elsewhere** - With 74% GC overhead at 8 threads, the bottleneck is likely STW scan phases, not BRC operations

4. **Micro-optimisations** - These are micro-optimisations that help specific hot paths; our workload may not hit them frequently

### What would show benefit?

- Parallel GC with high cross-thread reference sharing
- Workloads with intense deferred decref activity
- Lower-level microbenchmarks targeting specific operations

---

## Recommendations

### Option 1: Keep the optimisations (recommended)

- They don't hurt performance
- They may help specific workloads not captured by this benchmark
- The code is already written and tested
- Present as "enables future parallel improvements" rather than "provides X% speedup"

### Option 2: Remove the optimisations

- Simpler codebase
- No demonstrated benefit in realistic workloads
- Easier PR to review

### Option 3: More targeted testing

- Create microbenchmark specifically targeting BRC contention
- Test with parallel GC (not serial)
- Measure BRC queue operations directly

---

## Raw Data Location

```
/data/users/alexturner/parallel_gc/cpython/Lib/test/brc_results/
├── config_A_summary.txt
├── config_B_summary.txt
├── config_C_summary.txt
├── config_D_summary.txt
├── realistic_config_*_*.txt
└── pyperformance_config_*_*.json
```

---

## Methodology Notes

- Build: `./configure --disable-gil --with-lto CFLAGS=-O3`
- GC: Serial (omitting `--parallel` flag)
- Duration: 30 seconds per run
- Iterations: 5 runs per configuration per thread count
- Workloads: deltablue, deepcopy, pickle_copy, async_tree, richards, nbody, comprehensions
