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
- Timestamp: 2026-09-30T13:02:35.796081-07:00
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
- Command Line: `['/data/users/alexturner/parallel_gc/build-benchmark-threshold-gil/python', '/data/users/alexturner/parallel_gc/benchmarks/gc_perf_benchmark.py', '--full', '--include-synthetic', '--output', '/data/users/alexturner/parallel_gc/benchmarks/results/arm64-316-gil-adaptive-threshold-full-2026-09-30.md']`
- Project Git: `{'revision': '4111da582d435e58cbbb5445bb56aaebf5089702', 'dirty': True, 'worktree_sha256': '419a59e077769d0bdfdbc29582471f8db66578906c8977811b3eb80214269830', 'untracked_files': ['benchmarks/gc_adaptive_benchmark.py', 'benchmarks/results/arm64-316-ft-adaptive-full-2026-09-30.md', 'benchmarks/results/arm64-316-gil-adaptive-full-2026-09-30-crash.md', 'benchmarks/results/arm64-316-gil-adaptive-full-2026-09-30.md', 'benchmarks/results/arm64-316-gil-adaptive-threshold-standard-2026-09-30.md', 'build-fidelity-ft/', 'build-fidelity-gil/', 'cpython-original/', 'cpython-upstream-port/', 'docs/GIL_PORT_CALLSITE_MAPPING.md', 'docs/PORT_FIDELITY_LEDGER.md', 'docs/TEST_FIDELITY_LEDGER.md']}`
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

Runtime: 601s total (254279 collections)

| Metric           | Serial             | Parallel           | Change     |
|------------------|--------------------|--------------------|------------|
| Throughput       | 2,434 ± 9/s        | 2,430 ± 10/s       | -0.2%      |
| Collection latency (mean) | 1.5 ± 0.1ms        | 1.5 ± 0.0ms        | -1% |
| Collection latency (max) | 290ms              | 269ms              | -7% |
| Collection time | 63.0%              | 62.9%              | -0.1%      |

## GC Collection Time (500,000-object heap)

Time to collect one requested 500,000-object heap. Lower is better.

| Heap Type    | Serial (ms)        | Parallel (ms)      | Speedup |
|--------------|--------------------|--------------------|---------|
| chain        | 136.4 ± 2.9        | 101.3 ± 6.1        | 1.35x   |
| tree         | 165.8 ± 7.5        | 131.1 ± 8.6        | 1.26x   |
| wide_tree    | 143.3 ± 2.6        | 111.2 ± 11.1       | 1.29x   |
| graph        | 458.2 ± 49.0       | 387.9 ± 29.9       | 1.18x   |
| layered      | 387.6 ± 34.8       | 308.6 ± 37.7       | 1.26x   |
| independent  | 178.3 ± 11.4       | 142.8 ± 14.3       | 1.25x   |
| ai_workload  | 147.6 ± 8.2        | 114.4 ± 7.3        | 1.29x   |
| web_server   | 186.3 ± 10.2       | 156.6 ± 5.7        | 1.19x   |
| Geomean      |                    |                    | 1.26x   |

## Synthetic Throughput (Per Heap Type)

Steady-state throughput with continuous allocation.

| Heap Type    | Serial             | Parallel           | Throughput | Latency change |
|--------------|--------------------|--------------------|------------|----------------|
| chain        | 2,745,487/s        | 3,040,610/s        | +10.7%     | -31%           |
| graph        | 1,044,820/s        | 1,110,383/s        | +6.3%      | -7%            |
| ai_workload  | 1,634,532/s        | 1,824,440/s        | +11.6%     | -36%           |
| Geomean      |                    |                    | +9.5%      | -26% |

### Collection Latencies

| Heap Type    | Serial Mean (ms) | Serial Max (ms) | Parallel Mean (ms) | Parallel Max (ms) |
|--------------|------------------|-----------------|--------------------|-------------------|
| chain        | 70               | 849             | 49                 | 551                |
| graph        | 7.0              | 2123            | 6.5                | 955                |
| ai_workload  | 46               | 1529            | 29                 | 981                |

## Raw Samples

Callback latency is the full interval between the GC start and stop callbacks; it is not a stop-the-world measurement.

| Benchmark | Mode | Run | Active workers | Throughput/s | Callback latency mean (ms) | Callback latency max (ms) | Collections | Duration (s) |
|-----------|------|-----|----------------|--------------|----------------------------|---------------------------|-------------|--------------|
| mixed_workload | serial | 1 | — | 2448.667642 | 1.592177 | 233.328030 | 24473 | 60.082470 |
| mixed_workload | serial | 2 | — | 2427.135501 | 1.514411 | 290.476874 | 25138 | 60.205127 |
| mixed_workload | serial | 3 | — | 2433.009899 | 1.547422 | 258.200104 | 24774 | 60.077026 |
| mixed_workload | serial | 4 | — | 2430.882493 | 1.435025 | 228.124643 | 26014 | 60.129192 |
| mixed_workload | serial | 5 | — | 2429.813039 | 1.400070 | 245.231360 | 26354 | 60.243730 |
| mixed_workload | parallel-adaptive | 1 | 4→13 | 2422.904905 | 1.458137 | 263.838981 | 25825 | 60.128650 |
| mixed_workload | parallel-adaptive | 2 | 13→16 | 2416.669779 | 1.434240 | 253.741015 | 25952 | 60.074819 |
| mixed_workload | parallel-adaptive | 3 | 16→10 | 2430.518534 | 1.538762 | 268.896861 | 24943 | 60.161236 |
| mixed_workload | parallel-adaptive | 4 | 10→9 | 2436.933849 | 1.454333 | 193.830123 | 25859 | 60.141969 |
| mixed_workload | parallel-adaptive | 5 | 9→12 | 2442.190450 | 1.538134 | 217.383632 | 24947 | 60.209064 |
| synthetic_chain | serial | 1 | — | 2522844.771979 | 70.673999 | 808.123228 | 851 | 60.211077 |
| synthetic_chain | serial | 2 | — | 2812591.819996 | 81.531029 | 554.118589 | 739 | 60.272806 |
| synthetic_chain | serial | 3 | — | 2797652.612032 | 70.976543 | 829.030151 | 848 | 60.224918 |
| synthetic_chain | serial | 4 | — | 2798178.651140 | 61.813708 | 563.441349 | 976 | 60.378275 |
| synthetic_chain | serial | 5 | — | 2796165.957633 | 67.122345 | 849.083010 | 897 | 60.265522 |
| synthetic_chain | parallel-adaptive | 1 | 6→10 | 2897464.366866 | 59.146739 | 550.734133 | 1020 | 60.373478 |
| synthetic_chain | parallel-adaptive | 2 | 10→11 | 3070756.545471 | 44.289593 | 485.340139 | 1360 | 60.357243 |
| synthetic_chain | parallel-adaptive | 3 | 12→15 | 3077916.614985 | 46.024382 | 485.227211 | 1311 | 60.432047 |
| synthetic_chain | parallel-adaptive | 4 | 14→14 | 3048225.208411 | 48.388840 | 535.874006 | 1247 | 60.412465 |
| synthetic_chain | parallel-adaptive | 5 | 14→5 | 3108687.227308 | 45.551163 | 485.245867 | 1322 | 60.280107 |
| synthetic_graph | serial | 1 | — | 1054815.828526 | 6.623581 | 1281.448329 | 8390 | 60.245967 |
| synthetic_graph | serial | 2 | — | 1069324.567561 | 6.930406 | 1940.581610 | 8039 | 60.123186 |
| synthetic_graph | serial | 3 | — | 1007424.300916 | 8.209818 | 2122.803258 | 6872 | 60.207005 |
| synthetic_graph | serial | 4 | — | 1042356.482316 | 6.560142 | 1413.793950 | 8469 | 60.342120 |
| synthetic_graph | serial | 5 | — | 1050179.748776 | 6.621420 | 2067.633415 | 8407 | 60.278824 |
| synthetic_graph | parallel-adaptive | 1 | 6→13 | 1123510.583848 | 6.665178 | 955.393169 | 8349 | 60.288885 |
| synthetic_graph | parallel-adaptive | 2 | 14→5 | 1111019.410135 | 5.530071 | 732.908488 | 9892 | 60.283015 |
| synthetic_graph | parallel-adaptive | 3 | 5→11 | 1074206.117786 | 6.519770 | 881.905422 | 8507 | 60.247655 |
| synthetic_graph | parallel-adaptive | 4 | 11→4 | 1118193.691539 | 7.208461 | 651.967858 | 7759 | 60.326579 |
| synthetic_graph | parallel-adaptive | 5 | 3→4 | 1124985.121866 | 6.658980 | 477.260469 | 8265 | 60.120262 |
| synthetic_ai_workload | serial | 1 | — | 1666748.642365 | 39.577281 | 1528.822504 | 1515 | 60.274643 |
| synthetic_ai_workload | serial | 2 | — | 1682824.865280 | 40.240492 | 996.889693 | 1492 | 60.431257 |
| synthetic_ai_workload | serial | 3 | — | 1641802.844989 | 33.046914 | 867.513522 | 1821 | 60.601576 |
| synthetic_ai_workload | serial | 4 | — | 1623688.728017 | 58.317835 | 798.118523 | 1039 | 60.819024 |
| synthetic_ai_workload | serial | 5 | — | 1557592.480385 | 58.808394 | 955.193689 | 1025 | 60.505795 |
| synthetic_ai_workload | parallel-adaptive | 1 | 4→11 | 1802618.804497 | 26.500767 | 823.549296 | 2259 | 60.378450 |
| synthetic_ai_workload | parallel-adaptive | 2 | 12→10 | 1790862.464003 | 26.090834 | 718.277612 | 2288 | 60.207387 |
| synthetic_ai_workload | parallel-adaptive | 3 | 10→13 | 1844846.462541 | 28.879821 | 697.845358 | 2074 | 60.318675 |
| synthetic_ai_workload | parallel-adaptive | 4 | 14→13 | 1860072.529502 | 33.037737 | 718.120012 | 1813 | 60.285268 |
| synthetic_ai_workload | parallel-adaptive | 5 | 13→13 | 1823797.811375 | 32.885013 | 981.194711 | 1822 | 60.316732 |

- `chain` serial collection samples (ms): `[138.44478130340576, 133.78837890923023, 132.7586080878973, 138.2420603185892, 138.72929755598307]`
- `chain` parallel collection samples (ms): `[101.80146805942059, 90.6562265008688, 104.13941368460655, 104.06907740980387, 105.98020348697901]`
- `chain` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

- `tree` serial collection samples (ms): `[159.34846736490726, 174.5530180633068, 172.1596159040928, 157.74307306855917, 165.26731569319963]`
- `tree` parallel collection samples (ms): `[131.95847067981958, 142.6250198855996, 118.49176324903965, 129.62046079337597, 133.02686717361212]`
- `tree` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

- `wide_tree` serial collection samples (ms): `[140.65850339829922, 146.32227551192045, 144.87022813409567, 144.16145160794258, 140.60864597558975]`
- `wide_tree` parallel collection samples (ms): `[123.25610313564539, 114.04137779027224, 100.16285814344883, 98.97465445101261, 119.45116519927979]`
- `wide_tree` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

- `graph` serial collection samples (ms): `[412.10413351655006, 458.3951383829117, 414.38793670386076, 475.58038122951984, 530.5742984637618]`
- `graph` parallel collection samples (ms): `[374.931407161057, 419.33941282331944, 342.69316494464874, 403.40653620660305, 399.1108722984791]`
- `graph` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

- `layered` serial collection samples (ms): `[381.7125065252185, 442.4856202676892, 396.7881267890334, 354.66276947408915, 362.3498296365142]`
- `layered` parallel collection samples (ms): `[296.50737904012203, 370.75036857277155, 298.58145024627447, 308.03275387734175, 269.04887054115534]`
- `layered` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

- `independent` serial collection samples (ms): `[190.8534513786435, 184.4753995537758, 178.53283789008856, 160.1843796670437, 177.68060509115458]`
- `independent` parallel collection samples (ms): `[140.32358676195145, 156.77861589938402, 157.77382533997297, 124.72616881132126, 134.36953723430634]`
- `independent` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

- `ai_workload` serial collection samples (ms): `[151.70991979539394, 157.22962748259306, 145.39845753461123, 135.22081170231104, 148.57743680477142]`
- `ai_workload` parallel collection samples (ms): `[123.77569265663624, 120.63492275774479, 108.05011168122292, 110.6891818344593, 108.7102796882391]`
- `ai_workload` generated object counts: `[399728, 399728, 399728, 399728, 399728]`

- `web_server` serial collection samples (ms): `[185.79422868788242, 193.20947863161564, 169.99853681772947, 185.77253445982933, 196.5912440791726]`
- `web_server` parallel collection samples (ms): `[148.60300440341234, 158.10170210897923, 163.5692808777094, 159.0482397004962, 153.71547639369965]`
- `web_server` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

## Summary

Parallel GC shows -0.2% throughput change on the mixed workload.
GC collection time improved by 1.26x (geometric mean across heap types).