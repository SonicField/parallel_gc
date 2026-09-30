# Parallel GC Performance Benchmark Results

## Configuration

- Build type: FREE-THREADED
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
- Timestamp: 2026-09-30T08:31:32.459438-07:00
- Runtime parallel-GC config: `{'available': True, 'enabled': True, 'num_workers': 16, 'adaptive_workers': 4, 'parallel_cleanup': True}`
- Python Version: `3.16.0a0 free-threading build (heads/parallel-gc-upstream-port-dirty:323d3cc90a, Sep 30 2026, 07:59:28) [GCC 11.5.0 20240719 (Red Hat 11.5.0-15)]`
- Python Executable: `/data/users/alexturner/parallel_gc/build-benchmark-restored-ft/python`
- Python Implementation: `CPython`
- Python Cache Tag: `cpython-316`
- Python Build: `('heads/parallel-gc-upstream-port-dirty:323d3cc90a', 'Sep 30 2026 07:59:28')`
- Python Git: `('CPython', 'heads/parallel-gc-upstream-port-dirty', '323d3cc90a')`
- Compiler: `GCC 11.5.0 20240719 (Red Hat 11.5.0-15)`
- Configure Args: `'--with-parallel-gc' '--disable-gil' '--enable-optimizations' '--with-lto'`
- Cflags: `-fno-omit-frame-pointer -mno-omit-leaf-frame-pointer  -fno-strict-overflow -Wsign-compare -DNDEBUG -g -O3 -Wall`
- Ldflags: ``
- Py Cflags Nodist: `-fno-semantic-interposition -flto -fuse-linker-plugin -ffat-lto-objects -g -std=c11 -Wextra -Wno-unused-parameter -Wno-missing-field-initializers -Wstrict-prototypes -Werror=implicit-function-declaration -fvisibility=hidden -fprofile-use -fprofile-correction -I../cpython/Include/internal -I../cpython/Include/internal/mimalloc`
- Py Ldflags Nodist: `-fno-semantic-interposition -flto -fuse-linker-plugin -ffat-lto-objects -g`
- Py Parallel Gc: `1`
- Py Gil Disabled: `1`
- Platform: `Linux-6.16.1-0_fbk3_0_gd6c130b80483-aarch64-with-glibc2.34`
- Machine: `aarch64`
- Processor: `aarch64`
- Logical Cpu Count: `72`
- Available Cpu Count: `72`
- Pythonhashseed: `None`
- Benchmark Seed: `42`
- Command Line: `['/data/users/alexturner/parallel_gc/build-benchmark-restored-ft/python', '../benchmarks/gc_perf_benchmark.py', '--full', '--include-synthetic', '--output', '../benchmarks/results/arm64-316-ft-adaptive-full-2026-09-30.md']`
- Project Git: `{'revision': '4111da582d435e58cbbb5445bb56aaebf5089702', 'dirty': True, 'worktree_sha256': 'b391e7249c6834a78201aa6e7df5ef0ac9933c25b8e8704cbc1bec339ae1d13d', 'untracked_files': ['benchmarks/gc_adaptive_benchmark.py', 'build-fidelity-ft/', 'build-fidelity-gil/', 'cpython-original/', 'cpython-upstream-port/', 'docs/GIL_PORT_CALLSITE_MAPPING.md', 'docs/PORT_FIDELITY_LEDGER.md', 'docs/TEST_FIDELITY_LEDGER.md']}`
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

Runtime: 600s total (116473 collections)

| Metric           | Serial             | Parallel           | Change     |
|------------------|--------------------|--------------------|------------|
| Throughput       | 2,701 ± 8/s        | 3,227 ± 15/s       | +19.5%     |
| Collection latency (mean) | 3.7 ± 0.0ms        | 3.0 ± 0.0ms        | -21% |
| Collection latency (max) | 14ms               | 26ms               | +86% |
| Collection time | 67.3%              | 61.4%              | -5.9%      |

## GC Collection Time (500,000-object heap)

Time to collect one requested 500,000-object heap. Lower is better.

| Heap Type    | Serial (ms)        | Parallel (ms)      | Speedup |
|--------------|--------------------|--------------------|---------|
| chain        | 109.9 ± 1.9        | 92.5 ± 0.9         | 1.19x   |
| tree         | 122.1 ± 0.6        | 104.6 ± 0.9        | 1.17x   |
| wide_tree    | 125.7 ± 1.7        | 105.8 ± 0.8        | 1.19x   |
| graph        | 178.0 ± 5.4        | 132.9 ± 2.9        | 1.34x   |
| layered      | 171.2 ± 4.2        | 117.2 ± 4.0        | 1.46x   |
| independent  | 136.7 ± 8.0        | 115.9 ± 5.0        | 1.18x   |
| ai_workload  | 178.3 ± 5.5        | 161.9 ± 5.5        | 1.10x   |
| web_server   | 145.4 ± 2.4        | 123.0 ± 2.5        | 1.18x   |
| Geomean      |                    |                    | 1.22x   |

## Synthetic Throughput (Per Heap Type)

Steady-state throughput with continuous allocation.

| Heap Type    | Serial             | Parallel           | Throughput | Latency change |
|--------------|--------------------|--------------------|------------|----------------|
| chain        | 6,002,657/s        | 6,332,694/s        | +5.5%      | +10%           |
| graph        | 1,954,922/s        | 2,322,423/s        | +18.8%     | +54%           |
| ai_workload  | 3,262,420/s        | 2,950,019/s        | -9.6%      | +14%           |
| Geomean      |                    |                    | +4.3%      | +25% |

### Collection Latencies

| Heap Type    | Serial Mean (ms) | Serial Max (ms) | Parallel Mean (ms) | Parallel Max (ms) |
|--------------|------------------|-----------------|--------------------|-------------------|
| chain        | 4800             | 34980           | 5265               | 43328              |
| graph        | 251              | 619             | 388                | 801                |
| ai_workload  | 2455             | 10356           | 2810               | 14534              |

## Raw Samples

Callback latency is the full interval between the GC start and stop callbacks; it is not a stop-the-world measurement.

| Benchmark | Mode | Run | Active workers | Throughput/s | Callback latency mean (ms) | Callback latency max (ms) | Collections | Duration (s) |
|-----------|------|-----|----------------|--------------|----------------------------|---------------------------|-------------|--------------|
| mixed_workload | serial | 1 | — | 2703.674653 | 3.746065 | 9.645735 | 10809 | 60.007220 |
| mixed_workload | serial | 2 | — | 2690.926001 | 3.744726 | 13.743188 | 10791 | 60.003880 |
| mixed_workload | serial | 3 | — | 2694.427964 | 3.742823 | 8.168535 | 10791 | 60.005687 |
| mixed_workload | serial | 4 | — | 2704.138327 | 3.731966 | 5.835870 | 10809 | 60.004697 |
| mixed_workload | serial | 5 | — | 2709.640233 | 3.715388 | 13.920662 | 10845 | 60.003907 |
| mixed_workload | parallel-adaptive | 1 | 4→14 | 3248.595944 | 2.953074 | 4.962709 | 12492 | 60.006847 |
| mixed_workload | parallel-adaptive | 2 | 14→14 | 3234.781919 | 2.932571 | 25.896758 | 12541 | 60.006827 |
| mixed_workload | parallel-adaptive | 3 | 4→13 | 3216.710732 | 2.953007 | 5.393210 | 12464 | 60.006639 |
| mixed_workload | parallel-adaptive | 4 | 13→15 | 3224.866167 | 2.948529 | 5.137655 | 12494 | 60.003730 |
| mixed_workload | parallel-adaptive | 5 | 4→16 | 3210.781353 | 2.975783 | 16.701876 | 12437 | 60.003463 |
| synthetic_chain | serial | 1 | — | 6677550.336203 | 4374.398892 | 27799.311934 | 16 | 71.075046 |
| synthetic_chain | serial | 2 | — | 6042665.544462 | 4515.533151 | 27710.457655 | 16 | 73.651470 |
| synthetic_chain | serial | 3 | — | 5492335.734646 | 5328.711754 | 34980.297022 | 17 | 92.382554 |
| synthetic_chain | serial | 4 | — | 5464902.474181 | 5376.795731 | 26483.393947 | 17 | 93.402948 |
| synthetic_chain | serial | 5 | — | 6335830.424063 | 4404.773489 | 27008.491546 | 16 | 71.632788 |
| synthetic_chain | parallel-adaptive | 1 | 4→4 | 9070201.868231 | 3872.925558 | 27039.602909 | 16 | 62.537131 |
| synthetic_chain | parallel-adaptive | 2 | 4→5 | 5516548.561758 | 5311.667413 | 37738.646142 | 17 | 92.585716 |
| synthetic_chain | parallel-adaptive | 3 | 4→3 | 5450400.733386 | 6133.999565 | 41938.275299 | 16 | 100.574843 |
| synthetic_chain | parallel-adaptive | 4 | 3→3 | 5148095.329639 | 6476.530702 | 43327.531095 | 16 | 106.864455 |
| synthetic_chain | parallel-adaptive | 5 | 4→3 | 6478223.301395 | 4529.362946 | 30739.273656 | 16 | 74.097168 |
| synthetic_graph | serial | 1 | — | 1945356.759263 | 236.976281 | 618.676437 | 227 | 60.054383 |
| synthetic_graph | serial | 2 | — | 1963213.703200 | 247.565912 | 537.388243 | 218 | 60.027698 |
| synthetic_graph | serial | 3 | — | 1942442.322087 | 289.669379 | 460.737021 | 189 | 60.028964 |
| synthetic_graph | serial | 4 | — | 1961700.962769 | 247.912060 | 427.174394 | 218 | 60.093563 |
| synthetic_graph | serial | 5 | — | 1961895.035852 | 234.896977 | 415.679903 | 229 | 60.121259 |
| synthetic_graph | parallel-adaptive | 1 | 4→9 | 2189924.800120 | 535.263314 | 710.123453 | 107 | 60.562628 |
| synthetic_graph | parallel-adaptive | 2 | 9→14 | 2332246.569027 | 311.161360 | 801.464081 | 177 | 60.172197 |
| synthetic_graph | parallel-adaptive | 3 | 4→7 | 2258499.909112 | 513.346101 | 762.257419 | 111 | 60.360242 |
| synthetic_graph | parallel-adaptive | 4 | 7→11 | 2542277.732735 | 144.382957 | 432.841860 | 349 | 60.002886 |
| synthetic_graph | parallel-adaptive | 5 | 4→9 | 2289167.924504 | 435.573759 | 621.647042 | 129 | 60.004510 |
| synthetic_ai_workload | serial | 1 | — | 3280507.995235 | 2423.780039 | 8895.434047 | 26 | 63.740103 |
| synthetic_ai_workload | serial | 2 | — | 3322556.232449 | 2540.545170 | 10356.322602 | 25 | 64.429933 |
| synthetic_ai_workload | serial | 3 | — | 3148544.280119 | 2755.431081 | 10343.566298 | 24 | 67.145242 |
| synthetic_ai_workload | serial | 4 | — | 3184307.139981 | 2344.718690 | 7838.934382 | 28 | 66.373998 |
| synthetic_ai_workload | serial | 5 | — | 3376185.066472 | 2212.189852 | 7641.716944 | 28 | 62.601912 |
| synthetic_ai_workload | parallel-adaptive | 1 | 4→4 | 3075969.786920 | 2749.071257 | 13253.265423 | 23 | 64.308443 |
| synthetic_ai_workload | parallel-adaptive | 2 | 4→5 | 2734070.286291 | 2879.668934 | 14534.494377 | 24 | 70.592822 |
| synthetic_ai_workload | parallel-adaptive | 3 | 4→5 | 2938245.963469 | 2813.784019 | 13163.561665 | 23 | 65.849164 |
| synthetic_ai_workload | parallel-adaptive | 4 | 4→6 | 3252416.098489 | 2685.614884 | 13159.603050 | 23 | 62.446508 |
| synthetic_ai_workload | parallel-adaptive | 5 | 4→6 | 2749393.629168 | 2922.667969 | 13470.645493 | 23 | 68.573423 |

- `chain` serial collection samples (ms): `[106.92630149424076, 112.06299532204866, 110.26588827371597, 109.78956334292889, 110.51715537905693]`
- `chain` parallel collection samples (ms): `[92.07935817539692, 91.53080731630325, 93.04861444979906, 92.23078284412622, 93.82584039121866]`
- `chain` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

- `tree` serial collection samples (ms): `[121.49724178016186, 121.74921203404665, 121.65970727801323, 122.71223124116659, 122.71731812506914]`
- `tree` parallel collection samples (ms): `[103.62300090491772, 104.24006450921297, 104.09340728074312, 105.41422106325626, 105.69473449140787]`
- `tree` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

- `wide_tree` serial collection samples (ms): `[126.11332349479198, 125.12041535228491, 123.84641915559769, 125.0621760264039, 128.30643448978662]`
- `wide_tree` parallel collection samples (ms): `[106.86137154698372, 106.23394139111042, 105.38746789097786, 105.00311199575663, 105.41777312755585]`
- `wide_tree` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

- `graph` serial collection samples (ms): `[168.88005565851927, 179.79642748832703, 178.89747396111488, 183.40241815894842, 178.85180842131376]`
- `graph` parallel collection samples (ms): `[132.4951834976673, 130.57938683778048, 130.82786835730076, 133.01579654216766, 137.67747953534126]`
- `graph` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

- `layered` serial collection samples (ms): `[168.41521672904491, 176.73869896680117, 168.38027257472277, 174.751796759665, 167.55952779203653]`
- `layered` parallel collection samples (ms): `[111.32010724395514, 122.28230573236942, 118.25365480035543, 118.05784422904253, 116.19878374040127]`
- `layered` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

- `independent` serial collection samples (ms): `[150.09210724383593, 135.57028770446777, 136.17896661162376, 129.77467384189367, 131.73693511635065]`
- `independent` parallel collection samples (ms): `[122.54797201603651, 118.47688909620047, 113.36105782538652, 115.60885794460773, 109.27387792617083]`
- `independent` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

- `ai_workload` serial collection samples (ms): `[172.56463784724474, 174.71083719283342, 176.22102983295918, 185.0896356627345, 183.13249666243792]`
- `ai_workload` parallel collection samples (ms): `[158.90525840222836, 155.69450426846743, 162.96706162393093, 161.84906754642725, 170.3094458207488]`
- `ai_workload` generated object counts: `[399728, 399728, 399728, 399728, 399728]`

- `web_server` serial collection samples (ms): `[143.98282766342163, 145.2893689274788, 144.5556003600359, 143.6599437147379, 149.64362420141697]`
- `web_server` parallel collection samples (ms): `[122.71773442626, 121.38380017131567, 127.08709295839071, 120.51556631922722, 123.3684616163373]`
- `web_server` generated object counts: `[500000, 500000, 500000, 500000, 500000]`

## Summary

Parallel GC provides 19.5% throughput improvement on the mixed workload.
GC collection time improved by 1.22x (geometric mean across heap types).