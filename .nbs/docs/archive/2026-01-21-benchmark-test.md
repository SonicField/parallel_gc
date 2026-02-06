# Parallel GC Performance Benchmark Results

## Configuration

- **Build type:** FTP
- **Parallel GC available:** True
- **Parallel workers:** 8
- **Worker threads:** 4
- **Duration per benchmark:** 10.0s
- **Runs per configuration:** 2
- **Heap size (synthetic):** 500,000
- **Timestamp:** 2026-01-21T01:09:35.129296

## Realistic Workloads (Primary Metric)

Mixed workloads based on pyperformance benchmarks. This is the most
representative measure of real-world parallel GC benefit.

Runtime: 41s total (44 collections)

| Metric           | Serial           | Parallel         | Change   |
|------------------|------------------|------------------|----------|
| Throughput       | 1,407 ± 216/s    | 1,593 ± 38/s     | **+13.2%** |
| STW pause (mean) | 600 ± 457ms      | 186 ± 93ms       | -69%     |
| STW pause (max)  | 1108             | 396              | -64%     |
| GC overhead      | 48.7            % | 51.6            % | +2.9%    |

## GC Collection Time (500k heap)

Time to collect a single 500,000 object heap. Lower is better.

| Heap Type | Serial (ms)      | Parallel (ms)    | Speedup |
|-----------|------------------|------------------|---------|
| cyclic    | 145.8 ± 4.2      | 134.3 ± 1.6      | 1.09x   |
| ai        | 175.9 ± 6.6      | 178.6 ± 4.3      | 0.98x   |
| **Geomean** |                  |                  | **1.03x** |

## Synthetic Throughput (Per Heap Type)

Stress tests with 100% cyclic garbage. Shows upper-bound for GC-heavy workloads.

| Heap Type | Serial           | Parallel         | Throughput | STW Pause |
|-----------|------------------|------------------|------------|-----------|
| cyclic    | 2,073,497/s      | 1,987,486/s      | -4.1%      | -53%      |
| ai        | 622,475/s        | 594,466/s        | -4.5%      | +0%      |
| **Geomean** |                  |                  | **-4.3%**   | **-53%**   |

## Summary

Parallel GC provides **13.2% throughput improvement** on realistic workloads.
GC collection time improved by **1.03x** (geometric mean across heap types).