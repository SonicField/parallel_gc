# Parallel GC Performance Benchmark Results

## Configuration

- Build type: FTP
- Parallel GC available: True
- Parallel workers: 8
- Worker threads: 4
- Duration per benchmark: 10.0s
- Runs per configuration: 2
- Heap size (synthetic): 500,000
- Timestamp: 2026-01-21T03:14:49.090172

## Realistic Workloads (Primary Metric)

Mixed workloads based on pyperformance benchmarks. This is the most
representative measure of real-world parallel GC benefit.

Runtime: 41s total (51 collections)

| Metric           | Serial             | Parallel           | Change     |
|------------------|--------------------|--------------------|------------|
| Throughput       | 1,355 ± 17/s       | 1,504 ± 5/s        | +11.0%     |
| STW pause (mean) | 372 ± 88ms         | 162 ± 28ms         | -56%       |
| STW pause (max)  | 831ms              | 302ms              | -64%       |
| GC overhead      | 51.6%              | 50.9%              | -0.7%      |

## GC Collection Time (500k heap)

Time to collect a single 500,000 object heap. Lower is better.

| Heap Type    | Serial (ms)        | Parallel (ms)      | Speedup |
|--------------|--------------------|--------------------|---------|
| chain        | 119.7 ± 0.9        | 60.6 ± 14.5        | 1.98x   |
| tree         | 106.8 ± 3.8        | 60.0 ± 5.6         | 1.78x   |
| wide_tree    | 101.8 ± 3.0        | 56.5 ± 4.9         | 1.80x   |
| graph        | 104.7 ± 0.6        | 54.9 ± 0.6         | 1.91x   |
| layered      | 101.3 ± 0.6        | 71.6 ± 18.6        | 1.41x   |
| independent  | 100.1 ± 1.6        | 61.8 ± 7.8         | 1.62x   |
| ai_workload  | 122.3 ± 10.3       | 70.7 ± 13.5        | 1.73x   |
| web_server   | 91.2 ± 1.9         | 54.7 ± 0.6         | 1.67x   |
| Geomean      |                    |                    | 1.73x   |

## Synthetic Throughput (Per Heap Type)

Steady-state throughput with continuous allocation. Representative subset of heap types.

| Heap Type    | Serial             | Parallel           | Throughput | STW Change |
|--------------|--------------------|--------------------|------------|------------|
| chain        | 2,759,076/s        | 2,457,342/s        | -10.9%     | -32%       |
| graph        | 395,272/s          | 359,101/s          | -9.2%      | -86%       |
| ai_workload  | 574,161/s          | 812,625/s          | +41.5%     | -59%       |
| Geomean      |                    |                    | +4.6%      | -66%       |

### STW Pause Times

| Heap Type    | Serial Mean (ms) | Serial Max (ms) | Parallel Mean (ms) | Parallel Max (ms) |
|--------------|------------------|-----------------|--------------------|--------------------|
| chain        | 644              | 959             | 436                | 1043               |
| graph        | 1201             | 2402            | 169                | 427                |
| ai_workload  | 698              | 1317            | 285                | 451                |

## Summary

Parallel GC provides 11.0% throughput improvement on realistic workloads.
GC collection time improved by 1.73x (geometric mean across heap types).