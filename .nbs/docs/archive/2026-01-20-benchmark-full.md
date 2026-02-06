# Parallel GC Performance Benchmark Results

## Configuration

- **Build type:** FTP
- **Parallel GC available:** True
- **Parallel workers:** 8
- **Timestamp:** 2026-01-20T14:36:18.331087

## Realistic Workloads (Primary Metric)

Mixed workloads based on pyperformance benchmarks. This is the most
representative measure of real-world parallel GC benefit.

| Metric | Serial | Parallel | Change |
|--------|--------|----------|--------|
| Throughput | 1,444/sec | 1,495/sec | **+3.5%** |
| STW pause (mean) | 885ms | 997ms | +13% |
| STW pause (max) | 1856ms | 1480ms | -20% |
| GC overhead | 50.7% | 42.9% | -7.8pp |

## Synthetic Workloads (Per Heap Type)

Stress tests with 100% cyclic garbage. Shows upper-bound for GC-heavy workloads.

| Heap Type | Serial | Parallel | Throughput | STW Pause |
|-----------|--------|----------|------------|-----------|
| cyclic | 1,824,039/sec | 2,609,314/sec | +43.1% | -100% |
| ai | 1,234,185/sec | 903,472/sec | -26.8% | +0% |
| **Geometric Mean** | | | **+2.3%** | **+0%** |

## Summary

Parallel GC provides **3.5% throughput improvement** on realistic workloads.