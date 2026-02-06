# Parallel GC Performance Benchmark Results

## Configuration

- Build type: FTP
- Parallel GC available: True
- Parallel workers: 8
- Worker threads: 4
- Duration per benchmark: 10.0s
- Runs per configuration: 2
- Heap size (synthetic): 500,000
- Timestamp: 2026-01-21T01:47:22.723814

## Realistic Workloads (Primary Metric)

Mixed workloads based on pyperformance benchmarks. This is the most
representative measure of real-world parallel GC benefit.

Runtime: 42s total (40 collections)

| Metric           | Serial             | Parallel           | Change     |
|------------------|--------------------|--------------------|------------|
| Throughput       | 1,487 ± 84/s       | 1,564 ± 19/s       | +5.2%      |
| STW pause (mean) | 342 ± 95ms         | 362 ± 71ms         | +6%        |
| STW pause (max)  | 809ms              | 538ms              | -34%       |
| GC overhead      | 48.6%              | 50.9%              | +2.3%      |

## GC Collection Time (500k heap)

Time to collect a single 500,000 object heap. Lower is better.

| Heap Type    | Serial (ms)        | Parallel (ms)      | Speedup |
|--------------|--------------------|--------------------|---------|
| chain        | 165.4 ± 0.1        | 143.6 ± 2.1        | 1.15x   |
| tree         | 85.4 ± 6.2         | 75.0 ± 2.5         | 1.14x   |
| wide_tree    | 107.4 ± 2.1        | 89.8 ± 1.9         | 1.20x   |
| graph        | 363.6 ± 5.8        | 351.9 ± 16.1       | 1.03x   |
| layered      | 4.9 ± 0.1          | 4.5 ± 0.2          | 1.08x   |
| independent  | 223.6 ± 10.2       | 212.4 ± 2.6        | 1.05x   |
| ai_workload  | 214.2 ± 13.7       | 211.6 ± 3.9        | 1.01x   |
| web_server   | 204.5 ± 8.8        | 198.5 ± 2.4        | 1.03x   |
| Geomean      |                    |                    | 1.09x   |

## Synthetic Throughput (Per Heap Type)

Steady-state throughput with continuous allocation. Representative subset of heap types.

| Heap Type    | Serial             | Parallel           | Throughput | STW Pause |
|--------------|--------------------|--------------------|------------|-----------|
| chain        | 15,985/s           | 14,923/s           | -6.6%      | -100%     |
| graph        | 12,848/s           | 12,114/s           | -5.7%      | -77%      |
| ai_workload  | 16,486/s           | 17,437/s           | +5.8%      | N/A       |
| Geomean      |                    |                    | -2.4%      | -77%      |

## Summary

Parallel GC provides 5.2% throughput improvement on realistic workloads.
GC collection time improved by 1.09x (geometric mean across heap types).