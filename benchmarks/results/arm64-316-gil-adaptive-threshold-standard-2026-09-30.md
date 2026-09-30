# Parallel GC Performance Benchmark Results

## Configuration

- Build type: GIL
- Parallel GC available: True
- Parallel worker ceiling: 16
- Worker threads: 4
- Duration per benchmark: 30.0s
- Runs per configuration: 3
- Heap size (synthetic): 500,000
- Random seed: 42
- Collection warmup runs: 3
- Collection survivor ratio: 0.8
- Collection creation threads: 4
- Timestamp: 2026-09-30T12:59:18.546508-07:00
- Runtime parallel-GC config: `{'available': True, 'enabled': True, 'num_workers': 16, 'adaptive_workers': 4}`
- Python Version: `3.16.0a0 (heads/parallel-gc-upstream-port-dirty:323d3cc90a, Sep 30 2026, 12:54:53) [GCC 11.5.0 20240719 (Red Hat 11.5.0-15)]`
- Python Executable: `/data/users/alexturner/parallel_gc/build-benchmark-threshold-gil/python`
- Python Implementation: `CPython`
- Python Cache Tag: `cpython-316`
- Python Build: `('heads/parallel-gc-upstream-port-dirty:323d3cc90a', 'Sep 30 2026 12:54:53')`
- Python Git: `('CPython', 'heads/parallel-gc-upstream-port-dirty', '323d3cc90a')`
- Compiler: `GCC 11.5.0 20240719 (Red Hat 11.5.0-15)`
- Configure Args: `'--with-parallel-gc' '--enable-optimizations' '--with-lto'`
- Cflags: `-fno-omit-frame-pointer -mno-omit-leaf-frame-pointer  -fno-strict-overflow -Wsign-compare -DNDEBUG -g -O3 -Wall`
- Ldflags: ``
- Py Cflags Nodist: `-fno-semantic-interposition -flto -fuse-linker-plugin -ffat-lto-objects -g -std=c11 -Wextra -Wno-unused-parameter -Wno-missing-field-initializers -Wstrict-prototypes -Werror=implicit-function-declaration -fvisibility=hidden -fprofile-use -fprofile-correction -I/data/users/alexturner/parallel_gc/cpython/Include/internal -I/data/users/alexturner/parallel_gc/cpython/Include/internal/mimalloc`
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
- Command Line: `['/data/users/alexturner/parallel_gc/build-benchmark-threshold-gil/python', '/data/users/alexturner/parallel_gc/benchmarks/gc_perf_benchmark.py', '--output', '/data/users/alexturner/parallel_gc/benchmarks/results/arm64-316-gil-adaptive-threshold-standard-2026-09-30.md']`
- Project Git: `{'revision': '4111da582d435e58cbbb5445bb56aaebf5089702', 'dirty': True, 'worktree_sha256': '24a367067e3ffd0d12645356c4b8b829cd3bb16ac1d1b2ef5e8428fd238060b4', 'untracked_files': ['benchmarks/gc_adaptive_benchmark.py', 'benchmarks/results/arm64-316-ft-adaptive-full-2026-09-30.md', 'benchmarks/results/arm64-316-gil-adaptive-full-2026-09-30-crash.md', 'benchmarks/results/arm64-316-gil-adaptive-full-2026-09-30.md', 'build-fidelity-ft/', 'build-fidelity-gil/', 'cpython-original/', 'cpython-upstream-port/', 'docs/GIL_PORT_CALLSITE_MAPPING.md', 'docs/PORT_FIDELITY_LEDGER.md', 'docs/TEST_FIDELITY_LEDGER.md']}`
- Cpython Git: `{'revision': '323d3cc90adcc5dcc799f79812edd339b347a46c', 'dirty': True, 'worktree_sha256': 'c59cd7f2f5675cf1c61f886e8bfa38c6bcb178d3c91b494d3d9c06370b597295', 'untracked_files': ['Include/internal/pycore_gc_random_walk.h', 'Lib/test/test_gc_parallel_mark_alive.py']}`
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

Runtime: 181s total (67029 collections)

| Metric           | Serial             | Parallel           | Change     |
|------------------|--------------------|--------------------|------------|
| Throughput       | 2,418 ± 4/s        | 2,398 ± 0/s        | -0.8%      |
| Collection latency (mean) | 1.8 ± 0.0ms        | 1.9 ± 0.1ms        | +4% |
| Collection latency (max) | 132ms              | 136ms              | +3% |
| Collection time | 67.2%              | 68.2%              | +1.0%      |

## Raw Samples

Callback latency is the full interval between the GC start and stop callbacks; it is not a stop-the-world measurement.

| Benchmark | Mode | Run | Active workers | Throughput/s | Callback latency mean (ms) | Callback latency max (ms) | Collections | Duration (s) |
|-----------|------|-----|----------------|--------------|----------------------------|---------------------------|-------------|--------------|
| mixed_workload | serial | 1 | — | 2417.931137 | 1.788102 | 132.133994 | 11306 | 30.117897 |
| mixed_workload | serial | 2 | — | 2414.691484 | 1.818078 | 127.744089 | 11152 | 30.058084 |
| mixed_workload | serial | 3 | — | 2421.994571 | 1.752856 | 126.973456 | 11561 | 30.218482 |
| mixed_workload | parallel-adaptive | 1 | 4→7 | 2398.422643 | 1.918503 | 136.063253 | 10832 | 30.116043 |
| mixed_workload | parallel-adaptive | 2 | 7→8 | 2398.613764 | 1.891360 | 122.726721 | 10830 | 30.091964 |
| mixed_workload | parallel-adaptive | 3 | 9→9 | 2398.065945 | 1.788049 | 126.944590 | 11348 | 30.091750 |

## Summary

Parallel GC shows -0.8% throughput change on the mixed workload.