# Parallel GC Performance Investigation Plan

## Goal

Explain and remove avoidable runtime regressions in the GIL and free-threaded collectors without changing their algorithms, thresholds, adaptive policy, atomic ordering, or observable behavior.

Assembly and performance-counter evidence must identify the cost before any optimization is proposed. Each optimization must be independently measurable and reviewable.

## Historical evidence checkpoint

The initial evidence came from rigorous four-leg ABBA campaigns on the same 72-core AArch64 host. Both campaigns used one optimized CPython 3.16 binary per build, configured with `--with-parallel-gc --enable-optimizations --with-lto`. The free-threaded build also used `--disable-gil`.

The order was disabled, enabled, enabled, disabled. Each campaign completed all 96 workloads and produced 122 measurements. The CPython source was clean at revision `b60b59e22e49770894c29d9ddf61544816f80ac7`.

| Build | Enabled/disabled geomean | Significant improvements | Significant regressions | No significant change |
|-------|---------------------------|--------------------------|-------------------------|-----------------------|
| GIL | 1.0022, or 0.22% slower | 6 | 19 | 97 |
| Free-threaded | 1.0152, or 1.52% slower | 17 | 8 | 97 |

These aggregate figures include the invalid `bench_mp_pool` comparison described below. Preserve them as a record of the original campaigns, but do not use them as corrected collector-wide estimates.

Raw evidence:

- GIL: `benchmarks/results/pyperformance/gil-full-2026-10-02/`
- Free-threaded: `benchmarks/results/pyperformance/ft-full-2026-10-03/`

The parent repository was dirty because the pyperformance integration and result files were still being developed. Each campaign records the repository states, build configuration, four input hashes, combined-result hashes, and comparison hash in `campaign.json`. Treat these results as investigation evidence, not final submission evidence.

## Post-PGO evidence checkpoint

The current results use parallel-aware PGO candidate binaries whose substantive source is CPython commit `d396f837b9ab1f23573b404f70848584dff83bc7`. The PGO integration, workload calibration, profile coverage, binary hashes, complete ABBA results, and limitations are recorded in [`pgo-runtime-abba-arm64-2026-10-07.md`](../benchmarks/results/pyperformance/pgo-runtime-abba-arm64-2026-10-07.md).

The current runtime ABBA campaigns completed the same 96 programs and 122 named measurements in disabled, enabled, enabled, disabled order.

| Build | Enabled/disabled geomean | Significant improvements | Significant regressions | No significant change |
|---|---:|---:|---:|---:|
| GIL | 1.000720, or 0.072% slower | 6 | 12 | 104 |
| Free-threaded | 0.966212, or 3.38% faster | 28 | 3 | 91 |

The exact-container traversal work reversed the previous free-threaded `btree_gc_only`, `gc_traversal`, and `create_gc_cycles` regressions. In the current campaign they were respectively 1.28, 1.60, and 1.22 times faster with parallel GC enabled.

`sqlite_synth` remains slower in both builds. The GIL pairs were 37.7% and 38.4% slower, producing a combined 38.1% regression. The free-threaded pairs were 10.0% and 10.7% slower, producing a combined 10.4% regression. This cross-build and within-campaign reproduction makes it the next shared investigation target. It does not identify the cause.

A subsequent fixed-loop diagnostic isolated the shared trigger to creation of the process's first thread. One unrelated thread reproduced nearly the entire slowdown without parallel GC, and the workload performed no cyclic collection. The method, results, rejected explanations, and remaining uncertainty are recorded in [`sqlite-thread-transition-2026-10-07.md`](../benchmarks/results/pyperformance/investigations/sqlite-thread-transition-2026-10-07.md).

The proposed cross-collector response is documented in [`LAZY_POOL_CREATION_PLAN.md`](LAZY_POOL_CREATION_PLAN.md). It requires transactional startup, lazy helper creation, serial fallback after failure, and no automatic retry. The plan is not implementation authorization until its five approval points are resolved.

The supplementary PGO workload was tested separately with full control, candidate, candidate, control campaigns while parallel GC remained disabled. The GIL candidate/control geomean was 0.993831 and the free-threaded geomean was 0.998143. No significant slowdown reproduced across both builds. With 122 uncorrected simultaneous tests, benchmark-specific PGO claims still require focused repetition.

## Excluded harness artifact: `bench_mp_pool`

The original campaigns reported `bench_mp_pool` as 27.6% slower in the GIL build and 134.3% slower in the free-threaded build. A focused rigorous ABBA run reproduced the free-threaded result at 4.89 and 4.90 milliseconds disabled versus 11.4 and 11.5 milliseconds enabled.

The benchmark itself triggered no collections. Running the same workload with parallel GC enabled only in the parent was neutral. The regression appeared when the project `sitecustomize` activated parallel GC before multiprocessing imported and started its forkserver.

The activation code used pyperf's private `--worker` command-line argument to identify a benchmark process. The forkserver carries the original pyperf arguments after its `-c` command. Its `sitecustomize` therefore also saw `--worker`, incorrectly enabled parallel GC, and created a helper pool. Every child forked from that server then recovered an enabled pool and created another 15 helpers. Ten pool constructions made 52 `clone()` calls disabled and 382 enabled.

`--worker` is a pyperf argument. It has no parallel-GC meaning and must have no effect on collector state. This result is a benchmark-harness artifact, not a collector regression, and is excluded from both offender lists.

### Agreed harness repair

- Remove all command-line inspection from parallel-GC benchmark activation.
- Apply the requested mode in the project-owned pyperf hook, which pyperf instantiates for the measurement worker.
- Keep pyperf's command-timer helper passive.
- Make preflight call the activation function explicitly rather than fabricating a `--worker` argument.
- Preserve PID-bound attestation so recorded results still prove which process applied the mode.
- Prove that arbitrary command-line arguments, including `--worker`, cannot alter GC state.
- Prove that forkserver and multiprocessing children do not receive benchmark-induced activation merely by inheriting the campaign environment.

This is a harness-only repair. It does not add, remove, or reinterpret a CPython command-line option.

## GIL offenders

The following GIL and free-threaded inventories describe the historical pre-optimization campaigns. They are retained to show why the completed traversal work was undertaken. Use the post-PGO checkpoint above for current priorities.

The pair columns compare enabled with disabled in the first and second halves of the ABBA campaign. A value greater than 1.0 is slower with parallel GC enabled.

### Primary reproducible targets

| Priority | Benchmark | Combined regression | First pair | Second pair | Evidence assessment |
|----------|-----------|--------------------:|-----------:|------------:|---------------------|
| 1 | `sqlite_synth` | 38.6% | 38.9% | 38.3% | Large and exceptionally consistent |
| 2 | `create_gc_cycles` | 18.0% | 19.2% | 16.9% | Large and consistent |
| 3 | `sqlalchemy_declarative` | 5.6% | 4.4% | 6.9% | Consistent |
| 4 | `pathlib` | 5.1% | 5.8% | 4.5% | Consistent |

### Revalidation queue

`asyncio_tcp_ssl` was 8.9% slower in the combined result, but its pair results were 0.9% and 16.9% slower. `stdlib_startup` was 5.1% slower in the combined result, but its pair results were 1.1% faster and 11.4% slower. These measurements require targeted reproduction before profiling or optimization work is justified.

## Free-threaded offenders

### Primary reproducible targets

| Priority | Benchmark | Combined regression | First pair | Second pair | Evidence assessment |
|----------|-----------|--------------------:|-----------:|------------:|---------------------|
| 1 | `btree_gc_only` | 132.1% | 142.9% | 121.3% | Very large and reproduced |
| 2 | `gc_traversal` | 80.9% | 80.0% | 81.7% | Very large and exceptionally consistent |
| 3 | `create_gc_cycles` | 23.2% | 29.8% | 16.8% | Reproduced, but magnitude drifted |
| 4 | `float` | 17.2% | 17.2% | 17.2% | Large and exceptionally consistent |
| 5 | `sqlite_synth` | 10.9% | 11.7% | 10.0% | Large and consistent |
| 6 | `sqlalchemy_declarative` | 3.0% | 3.9% | 2.2% | Smaller but consistent |

### Revalidation queue

`stdlib_startup` was 89.8% slower in the combined result, but its pair results were 177.3% and 0.6% slower. The combined number is not a reproducible regression and must not be used as an optimization target without a clean targeted reproduction.

## Performance controls

Fixes must preserve the regions that already improve. In the GIL campaign, `btree_gc_only` was 1.87 times faster, `gc_traversal` was 1.11 times faster, and `btree` was 1.05 times faster. In the free-threaded campaign, 17 async-tree and graph measurements improved significantly; the largest async-tree improvements were approximately 10 to 14 percent.

The project-specific 500,000-requested-object throughput and pause benchmarks remain mandatory. A pyperformance improvement does not justify losing collection speed or pause reduction on those graphs, adaptive behavior, or correctness.

## Investigation rules

1. Do not infer machine behavior from the C source alone. Read the final PGO+LTO AArch64 assembly and collect hardware-counter evidence.
2. Do not change the collection threshold, phase structure, adaptive algorithm, atomic ordering, or safety checks as a performance shortcut.
3. Do not modify upstream pyperformance benchmark code. Use runner options and project-owned instrumentation.
4. Compare enabled and disabled modes in the same binary with identical benchmark work, loop counts, affinity, and environment.
5. Alternate modes and retain every run. Do not select favorable samples.
6. Change one performance mechanism per commit. Revert a change that does not improve its stated target or that damages a regression control.
7. Run both GIL and free-threaded checks after every source optimization, even when the change appears collector-specific.

## Investigation sequence

### 1. Freeze and verify the baselines

- Verify the campaign hashes and executable metadata recorded in both `campaign.json` files.
- Produce a compact machine-readable table containing the combined ratio, both ABBA pair ratios, significance result, loop counts, and variance for every measurement.
- Record CPU affinity, NUMA placement, frequency policy, kernel perf restrictions, and available Arm PMU events before collecting profiles.
- Repeat the final submission campaigns from clean published parent and CPython revisions after the investigation is complete.

Exit condition: every quoted offender can be reproduced from retained raw data, and suspect results are visibly separated from reproducible results.

### 2. Build focused reproductions

- Run the primary offenders individually in short ABBA campaigns before spending time on profiles.
- Force identical loop counts between modes when pyperf calibration selected different counts. This tests whether fixed setup costs or nonlinear work affected the normalized result without changing benchmark source.
- Record GC collection counts, generations, candidate counts, chosen worker counts, and phase timings where the existing public diagnostics provide them.
- Use an enable-then-disable control where needed to distinguish active collection costs from persistent pool memory or lifecycle costs.

Exit condition: each profiling target has a stable command that preserves its full regression and performs identical work in both modes.

### 3. Inspect the optimized AArch64 machine code

- Confirm that the disassembled executable is the exact PGO+LTO binary used by the focused reproduction.
- Compare the enabled and disabled collection paths and identify the actual inner loops selected at runtime.
- Record which source helpers were inlined by LTO, which calls remain, whether calls are direct or indirect, and the emitted branch structure.
- Inspect address-generation, dependent loads, spills, loop-carried dependencies, and code size around the collector hot loops.
- Use `perf annotate` or equivalent symbolized output to connect hot instructions to the final disassembly.

Exit condition: a written instruction-level delta exists for each hot collector path. Source-level guesses are not accepted as findings.

### 4. Measure hardware behavior

- Start with cycles, instructions, branches, branch misses, cache references, and cache misses.
- Add available Arm-specific L1 data-cache, last-level-cache, TLB, stalled-cycle, and memory-access events only after checking `perf list` on this host.
- Use small event groups or repeated runs to avoid misleading multiplexed counts.
- Record elapsed time, counter scaling, context switches, migrations, and CPU placement for every run.
- Collect call graphs only after verifying that the chosen unwind method produces complete stacks for the optimized binary.

Exit condition: the regression is apportioned to measured instructions, branch behavior, memory behavior, synchronization, system calls, or another observed cost. A statistically significant wall-time delta alone is insufficient.

### 5. Test falsifiable offender-specific hypotheses

For GIL `sqlite_synth`, `create_gc_cycles`, and the smaller object-heavy regressions, determine whether the additional time is inside collection, outside collection, or a fixed activation cost. If it is inside collection, use assembly and counters to identify the exact loop and instruction sequence.

The `bench_mp_pool` hypothesis has been resolved as a benchmark-activation defect. Repair and test the harness before regenerating either campaign; do not optimize the collector against the invalid result.

For free-threaded `btree_gc_only` and `gc_traversal`, split the profile by collector phase. Measure whether the regression occurs in parallel graph work, stop-the-world coordination, serial finalization and deletion, BRC processing, or another phase. The existing finalizer/BRC explanation remains a hypothesis until counters or instrumentation distinguish those phases.

For free-threaded `float` and `sqlite_synth`, determine whether the cost is associated with collections at all. Their consistency makes them useful controls against explanations that apply only to large graph traversal.

Exit condition: each proposed cause has a result that could reject it and recorded evidence that either rejects or supports it.

### 6. Optimize one proven cost at a time

- Prefer ordinary compiler-visible improvements such as local inlining, removal of redundant loads, and streamlined hot-loop control flow when the assembly proves they are relevant.
- Preserve every check and state transition unless a separate correctness argument and explicit approval authorize a behavioral change.
- Add or retain correctness tests before changing source.
- Rebuild the optimized binary and rerun the focused ABBA reproduction after each change.
- Run the corresponding regression-control benchmarks and the focused GIL and free-threaded test suites before retaining the change.

Exit condition: the isolated change reduces the measured cost, preserves behavior, and does not merely transfer the regression to the other collector or a 500,000-requested-object workload.

### 7. Re-run complete evidence

- Run rigorous GIL and free-threaded pyperformance ABBA campaigns.
- Run the full project-specific throughput and pause campaigns for both builds.
- Run optimized feature-off controls to measure compile-time overhead separately from runtime activation.
- Preserve raw samples, negative regions, build metadata, repository revisions, and dirty-state fingerprints.

Exit condition: the final evidence is produced from clean published revisions and is suitable for core-developer review.

## Progress log

| Stage | Status | Evidence or blocker |
|-------|--------|---------------------|
| Baseline campaigns | Complete | Post-PGO GIL and FT campaigns completed all workloads at substantive CPython revision `d396f837b9`; the raw evidence and report are committed. |
| Baseline offender inventory | Complete | `sqlite_synth` is the only large regression reproduced in both current builds; FT `float` and GIL `create_gc_cycles` remain build-specific targets. |
| Focused reproductions | In progress | The `sqlite_synth` diagnostic found zero collections and reproduced the cost with one unrelated thread; a rigorous already-threaded pool/no-pool control remains. |
| AArch64 assembly audit | In progress | The completed traversal audit led to retained exact-container paths; `sqlite_synth` has not yet been attributed to a source path. |
| Hardware-counter profiles | In progress | Previous traversal profiles are retained; no `sqlite_synth` counter result exists yet. |
| Proven-cause optimizations | In progress | Exact list, tuple, and dictionary traversal changes were independently tested and retained; no `sqlite_synth` change is authorized yet. |
| Full post-fix campaigns | Partial | Rigorous pyperformance campaigns are complete. Full project-specific throughput and pause campaigns and GitHub regressions remain. |

Add a dated entry here after every material measurement, rejected hypothesis, retained optimization, or reverted optimization. Record the exact command, binary identity, repository revisions, machine controls, raw-result location, observation, and remaining uncertainty.

### 2026-10-05: multiprocessing result classified as a harness artifact

The focused rigorous campaign used:

```bash
/tmp/parallel-gc-pyperformance-driver/bin/python \
    benchmarks/run_pyperformance.py abba \
    --python build-pyperformance-ft/python \
    --benchmarks concurrent_imap \
    --run-style rigorous \
    --output-dir /tmp/parallel-gc-perf.GuaPHn/mp-abba
```

It reproduced 4.89 and 4.90 milliseconds disabled versus 11.4 and 11.5 milliseconds enabled. A direct 100-pool control was neutral when only the parent enabled parallel GC and recorded no GC callbacks. A forkserver probe then showed disabled children with one thread and enabled children with 16 threads under the current command-line-based activation scheme.

`strace -f -c -e trace=clone,clone3` around ten pool constructions counted 52 clones disabled and 382 enabled. Reading `multiprocessing.forkserver` established the mechanism: it appends the original pyperf arguments to its `-c` invocation, causing `sitecustomize` to see the unrelated `--worker` argument and activate the collector in the server.

Decision: replace command-line-based activation with hook-owned activation, retain explicit preflight and PID-bound result attestation, and add process-boundary tests before accepting new pyperformance results.

### 2026-10-07: parallel-aware PGO and post-optimization campaigns completed

CPython commit `d396f837b9` adds a supplementary PGO task for builds configured with parallel GC. The task exercises both collector implementations and exact container layouts, verifies that the parallel path ran, and contributes its counters before profile merging. Standard-PGO controls and parallel-aware-PGO candidates were built for GIL and free-threaded configurations with the same source, compiler options, and LTO settings.

Full control, candidate, candidate, control experiments ran with parallel GC disabled. The GIL candidate/control geometric mean was 0.993831; the free-threaded value was 0.998143. Significant changes were mixed in direction and no slowdown reproduced across builds. The retained decision was to keep the supplementary PGO task.

Full disabled, enabled, enabled, disabled experiments then used one parallel-aware-PGO binary per build. GIL enabled/disabled geometric mean time was 1.000720. Free-threaded enabled/disabled geometric mean time was 0.966212. The earlier free-threaded traversal regressions became substantial improvements after the exact-container work.

`sqlite_synth` remained 38.1% slower in the GIL build and 10.4% slower in the free-threaded build. Both halves of both campaigns reproduced the direction and magnitude. Decision: preserve the complete evidence, run all GitHub regression configurations, then investigate `sqlite_synth` as a shared cost. Do not change collector code until focused timing and collection evidence locates the additional work.

Evidence: [`pgo-runtime-abba-arm64-2026-10-07.md`](../benchmarks/results/pyperformance/pgo-runtime-abba-arm64-2026-10-07.md).

### 2026-10-07: `sqlite_synth` isolated to the first-thread transition

A fixed-loop diagnostic ran the unmodified pyperformance `bench_sqlite()` function in fresh GIL and free-threaded processes. Each process ran one warmup and five measurements at 131,072 loops; three fresh processes were used for each mode.

The measured workload triggered no cyclic collections. Disabling automatic GC did not change the parallel-enabled result. Enabling and then disabling the pool retained the slowdown.

One unrelated Python thread, created and joined without enabling parallel GC, reproduced 38.9% slowdown in the GIL build and 11.4% in the free-threaded build. Direct observation showed glibc's `__libc_single_threaded` flag change from 1 to 0 after either one unrelated thread or pool creation and remain 0 after thread exit. Creating 15 unrelated threads did not add material cost beyond the first.

In already-threaded diagnostic processes, enabling the pool added approximately 1.2% in each build. That small difference did not use randomized ABBA ordering and is not yet an established effect size.

Decision: classify most of the current `sqlite_synth` regression as the process's irreversible first-thread transition, with parallel GC acting as the trigger. Do not attribute it to graph traversal or collection phases. Before considering a design change, run a rigorous already-threaded pool/no-pool comparison and measure the lower-level hot path. Immediate versus lazy pool creation is a design trade-off and requires explicit discussion.

Evidence: [`sqlite-thread-transition-2026-10-07.md`](../benchmarks/results/pyperformance/investigations/sqlite-thread-transition-2026-10-07.md).
