# Parallel GC Performance Benchmark Results

## Configuration

- Build type: GIL
- Parallel GC available: True
- Parallel worker ceiling: 16
- Worker threads: 4
- Duration per benchmark: 60.0s
- Runs per configuration: 5
- Heap size (synthetic): 500,000
- Random seed: 42
- Collection warmup runs: 3
- Collection survivor ratio: 0.8
- Collection creation threads: 4
- Timestamp: 2026-09-30T09:43:24.419352-07:00
- Runtime parallel-GC config: `{'available': True, 'enabled': True, 'num_workers': 16, 'adaptive_workers': 4}`
- Python Version: `3.16.0a0 (heads/parallel-gc-upstream-port-dirty:323d3cc90a, Sep 30 2026, 08:16:11) [GCC 11.5.0 20240719 (Red Hat 11.5.0-15)]`
- Python Executable: `/data/users/alexturner/parallel_gc/build-benchmark-restored-gil/python`
- Python Implementation: `CPython`
- Python Cache Tag: `cpython-316`
- Python Build: `('heads/parallel-gc-upstream-port-dirty:323d3cc90a', 'Sep 30 2026 08:16:11')`
- Python Git: `('CPython', 'heads/parallel-gc-upstream-port-dirty', '323d3cc90a')`
- Compiler: `GCC 11.5.0 20240719 (Red Hat 11.5.0-15)`
- Configure Args: `'--with-parallel-gc' '--enable-optimizations' '--with-lto'`
- Cflags: `-fno-omit-frame-pointer -mno-omit-leaf-frame-pointer  -fno-strict-overflow -Wsign-compare -DNDEBUG -g -O3 -Wall`
- Ldflags: ``
- Py Cflags Nodist: `-fno-semantic-interposition -flto -fuse-linker-plugin -ffat-lto-objects -g -std=c11 -Wextra -Wno-unused-parameter -Wno-missing-field-initializers -Wstrict-prototypes -Werror=implicit-function-declaration -fvisibility=hidden -fprofile-use -fprofile-correction -I../cpython/Include/internal -I../cpython/Include/internal/mimalloc`
- Py Ldflags Nodist: `-fno-semantic-interposition -flto -fuse-linker-plugin -ffat-lto-objects -g`
- Py Parallel Gc: `1`
- Py Gil Disabled: `0`
- Platform: `Linux-6.16.1-0_fbk3_0_gd6c130b80483-aarch64-with-glibc2.34`
- Machine: `aarch64`
- Processor: `aarch64`
- Logical Cpu Count: `72`
- Available Cpu Count: `72`
- Pythonhashseed: `None`
- Benchmark Seed: `42`
- Command Line: `['/data/users/alexturner/parallel_gc/build-benchmark-restored-gil/python', '../benchmarks/gc_perf_benchmark.py', '--full', '--output', '../benchmarks/results/arm64-316-gil-adaptive-full-2026-09-30.md']`
- Project Git: `{'revision': '4111da582d435e58cbbb5445bb56aaebf5089702', 'dirty': True, 'worktree_sha256': '7afbd45313e2ec46397a4e97fc4114eda683f43d933cc6f77b5c2d6ff8751bee', 'untracked_files': ['benchmarks/gc_adaptive_benchmark.py', 'benchmarks/results/arm64-316-ft-adaptive-full-2026-09-30.md', 'build-fidelity-ft/', 'build-fidelity-gil/', 'cpython-original/', 'cpython-upstream-port/', 'docs/GIL_PORT_CALLSITE_MAPPING.md', 'docs/PORT_FIDELITY_LEDGER.md', 'docs/TEST_FIDELITY_LEDGER.md']}`
- Cpython Git: `{'revision': '323d3cc90adcc5dcc799f79812edd339b347a46c', 'dirty': True, 'worktree_sha256': '3a15cce147c6d02933d64318006f12f676dd5c06ea5b95ed5861ddc732151528', 'untracked_files': ['Include/internal/pycore_gc_random_walk.h', 'Lib/test/test_gc_parallel_mark_alive.py']}`
- Cpu Affinity: `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71]`
- Numa Policy: `policy: default
preferred node: current
physcpubind: 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71
cpubind: 0
nodebind: 0
membind: 0
preferred:`

## Mixed Workload Throughput

Results for this project's handwritten allocation workload.

Runtime: 601s total (168779 collections)

| Metric           | Serial             | Parallel           | Change     |
|------------------|--------------------|--------------------|------------|
| Throughput       | 2,416 ± 5/s        | 2,250 ± 13/s       | -6.9%      |
| Collection latency (mean) | 1.6 ± 0.1ms        | 5.3 ± 0.2ms        | +224% |
| Collection latency (max) | 186ms              | 198ms              | +6% |
| Collection time | 65.1%              | 87.3%              | +22.2%     |

## Raw Samples

Callback latency is the full interval between the GC start and stop callbacks; it is not a stop-the-world measurement.

| Benchmark | Mode | Run | Active workers | Throughput/s | Callback latency mean (ms) | Callback latency max (ms) | Collections | Duration (s) |
|-----------|------|-----|----------------|--------------|----------------------------|---------------------------|-------------|--------------|
| mixed_workload | serial | 1 | — | 2418.223549 | 1.694179 | 165.212458 | 23384 | 60.160278 |
| mixed_workload | serial | 2 | — | 2414.111278 | 1.585516 | 178.174735 | 24449 | 60.177425 |
| mixed_workload | serial | 3 | — | 2410.476879 | 1.733255 | 137.132929 | 23003 | 60.108853 |
| mixed_workload | serial | 4 | — | 2423.228260 | 1.631143 | 186.449076 | 23964 | 60.134244 |
| mixed_workload | serial | 5 | — | 2414.704539 | 1.559994 | 158.351844 | 24614 | 60.163468 |
| mixed_workload | parallel-adaptive | 1 | 4→11 | 2234.657861 | 5.303549 | 143.135742 | 9891 | 60.117928 |
| mixed_workload | parallel-adaptive | 2 | 10→12 | 2253.004485 | 5.277162 | 198.250856 | 9925 | 60.126822 |
| mixed_workload | parallel-adaptive | 3 | 11→15 | 2269.005736 | 5.598119 | 176.784746 | 9444 | 60.148372 |
| mixed_workload | parallel-adaptive | 4 | 16→9 | 2240.411190 | 5.060170 | 189.010511 | 10297 | 60.088523 |
| mixed_workload | parallel-adaptive | 5 | 9→7 | 2252.212806 | 5.361313 | 184.243354 | 9808 | 60.120873 |

## Summary

Parallel GC shows -6.9% throughput change on the mixed workload.