# Unchanged full FT repeat, 17 October 2026

## Outcome

The original broad module-rooted controlled-collection slowdown did not reproduce. Every module case increases in the first ABBA half and decreases in the second. Four overall means increase (+0.46% to +5.34%) and four decrease. The original full comparison had all eight increase in both halves (+18.72% to +34.81%). Neither the original result nor this repeat is discarded.

The repeat retains negative measurements. Seven of eight frame-rooted controlled cases take longer in both halves (+2.43% to +5.91%). Three of eight sustained parallel throughput means decrease: frame mixed −1.11%, frame AI-shaped −3.93%, and module-cache mixed −1.97%. The first two decrease in both halves; module mixed has opposing halves. Three callback-duration means increase, with only frame graph higher in both halves. These are recorded differences, not a performance-neutrality or acceptance verdict.

Frame AI-shaped throughput decreases while its serial control increases +1.78%. Frame controlled independent and AI-shaped collections increase while their serial controls decrease −1.49% and −1.71%. These differences still need explanation. Conversely, controls move with several other measurements: frame tree collection increases +5.91% with serial +4.95%; frame graph callback mean increases +1.10% with serial +1.91%. Control movement is evidence, not an automatic subtraction or excuse.

No code repair occurred. The same source/binary pair produces different controlled-collection patterns across time windows and invocation contexts. The repeats weaken a context-independent attribution to the integrated source. They do not establish noise, identify an allocator/worker/PGO cause, or prove that a particular collector mechanism is safe to change.

## Experiment and checks

Four original full invocations ran baseline–current–current–baseline from 09:58:22 to 16:18:26 UTC on 17 October 2026: six hours twenty minutes four seconds to controller completion. Execution session 74721 and wait cell 569 completed with exit 0; their processes are gone. [Protocol, timestamps and complete evidence](README.md).

Baseline is CPython `c67363fa59543ef5d572383af927f1cff88514a1`; current is `388fd5bb46fdda6b464db566faf818505c3d6eef`. The same existing GCC 11.5 AArch64 PGO+LTO FT binaries were used in the original full comparison, focused diagnostic and this repeat. No new binary was substituted. Native/runtime preflights pass, sources are clean, and original binary/benchmark/analyser fingerprints remain unchanged. Parent provenance records unrelated untracked files and documentation/evidence work; it is not labelled clean.

The original `gc_perf_benchmark.py` runs as `__main__`, from the parent root, with unchanged `--full --include-synthetic --json`: five runs per arm, 60-second sustained phases, four application/creation threads, nominal 500,000-member heaps, seed 42, three controlled warmups and 80% surviving clusters. CPU affinity is 0–31, with NUMA CPU/memory node 0. Worker selection remains adaptive, starting at four with the existing two-to-sixteen range. Sixteen is a ceiling, not a fixed active count. No timed worker-count history is recorded.

All four actual documents pass source order, configuration, compiled mode, placement, complete workload and sample validation. Controlled generated-member sequences match both arms, every repeat leg and the original full experiment. Counts are generated cluster members, not all supporting GC containers or objects reclaimed. All 72 analysis rows preserve raw samples, per-leg ranges and standard deviations, both halves, serial controls, counts and timing totals.

An independent raw-sample calculation checks 1,584 fields, including every leg/source mean, source change, both halves and per-leg parallel/serial ratio. [Complete checks](evidence/complete-checks.json) record the arithmetic-rounding tolerances; they are not performance cutoffs. All twenty-four existing analyser tests pass. Archive replay reproduces all rows, content hashes and leg metadata exactly; only input path names differ. Numerical checks ran on CPU 32; lightweight artifact copying, hashing and commits were not affinity-pinned. No builds or competing benchmark campaigns ran during measurement. The launch process snapshot is not proof of continuous machine isolation.

## Sustained measurements

Source means weight whole legs equally. Change is `100 × (current / baseline − 1)`; the null ratio is one. Negative throughput and positive duration changes are worse. Half 1 is current leg 2 / baseline leg 1; half 2 is current leg 3 / baseline leg 4. Serial controls have parallel GC disabled. Mixed completed-work units and synthetic generated-member units must not be aggregated as one common throughput unit.

Callback duration spans one collection's start/stop callbacks. It is not the interval between collections, an application-latency percentile or FT stopped-world duration.

| Rooting / workload / metric | Baseline parallel mean | Current parallel mean | Parallel change | Half 1 | Half 2 | Serial control change |
|---|---:|---:|---:|---:|---:|---:|
| frame / mixed / throughput | 3411.23 | 3373.28 | -1.11% | -1.74% | -0.48% | -0.59% |
| frame / mixed / callback mean ms | 2.69 | 2.72 | +0.77% | +1.70% | -0.14% | +0.86% |
| frame / chain / throughput | 6040745.62 | 6406780.21 | +6.06% | +7.44% | +4.63% | +5.35% |
| frame / chain / callback mean ms | 2916.12 | 2797.11 | -4.08% | -2.57% | -5.41% | -6.14% |
| frame / graph / throughput | 1927238.68 | 1938081.69 | +0.56% | +0.19% | +0.94% | -0.10% |
| frame / graph / callback mean ms | 8.86 | 8.96 | +1.10% | +1.14% | +1.07% | +1.91% |
| frame / ai_workload / throughput | 2925148.08 | 2810148.94 | -3.93% | -2.72% | -5.15% | +1.78% |
| frame / ai_workload / callback mean ms | 1943.86 | 1845.38 | -5.07% | +6.02% | -13.53% | -19.57% |
| module / mixed / throughput | 3874.84 | 3798.35 | -1.97% | -4.54% | +0.61% | -1.30% |
| module / mixed / callback mean ms | 58.24 | 58.34 | +0.16% | +2.89% | -2.62% | +0.06% |
| module / chain / throughput | 5550044.24 | 6084372.34 | +9.63% | +3.81% | +15.22% | -7.01% |
| module / chain / callback mean ms | 3282.40 | 3104.41 | -5.42% | -1.55% | -9.66% | +9.82% |
| module / graph / throughput | 1804316.32 | 1836043.81 | +1.76% | +0.58% | +2.95% | +1.07% |
| module / graph / callback mean ms | 7.88 | 7.85 | -0.32% | +0.78% | -1.42% | +1.93% |
| module / ai_workload / throughput | 2909181.99 | 2959557.21 | +1.73% | +6.48% | -2.63% | +2.68% |
| module / ai_workload / callback mean ms | 1898.54 | 1742.13 | -8.24% | +1.77% | -16.26% | -18.53% |

Five throughput means increase and five callback-duration means decrease. These observations do not cancel negative cases or establish collector-specific benefits.

## Controlled collections

These are means of the existing `gc.collect()` timing bracket, in milliseconds. Seven frame cases increase in both halves; frame chain decreases in both. Every module case has opposing halves. The complete means must not hide those differences.

| Rooting / workload / metric | Baseline parallel mean | Current parallel mean | Parallel change | Half 1 | Half 2 | Serial control change |
|---|---:|---:|---:|---:|---:|---:|
| frame / chain / gc.collect() ms | 32.55 | 31.96 | -1.81% | -1.48% | -2.16% | -1.92% |
| frame / tree / gc.collect() ms | 33.05 | 35.00 | +5.91% | +6.89% | +4.91% | +4.95% |
| frame / wide_tree / gc.collect() ms | 31.10 | 32.28 | +3.81% | +5.94% | +1.67% | +1.25% |
| frame / graph / gc.collect() ms | 38.10 | 40.27 | +5.70% | +11.10% | +0.25% | +0.86% |
| frame / layered / gc.collect() ms | 41.07 | 42.78 | +4.17% | +6.85% | +1.51% | +1.91% |
| frame / independent / gc.collect() ms | 31.79 | 32.70 | +2.86% | +1.81% | +3.90% | -1.49% |
| frame / ai_workload / gc.collect() ms | 40.87 | 41.86 | +2.43% | +2.31% | +2.54% | -1.71% |
| frame / web_server / gc.collect() ms | 32.35 | 33.54 | +3.66% | +7.18% | +0.34% | +1.16% |
| module / chain / gc.collect() ms | 42.41 | 41.27 | -2.68% | +15.37% | -18.30% | -3.55% |
| module / tree / gc.collect() ms | 44.07 | 43.78 | -0.66% | +16.88% | -16.87% | +3.46% |
| module / wide_tree / gc.collect() ms | 44.96 | 41.99 | -6.61% | +15.28% | -24.56% | -5.47% |
| module / graph / gc.collect() ms | 55.11 | 55.37 | +0.46% | +13.68% | -13.02% | -11.52% |
| module / layered / gc.collect() ms | 63.20 | 61.94 | -1.98% | +17.21% | -20.15% | -4.55% |
| module / independent / gc.collect() ms | 42.34 | 42.83 | +1.15% | +23.38% | -18.48% | +4.44% |
| module / ai_workload / gc.collect() ms | 55.76 | 56.59 | +1.48% | +15.48% | -12.36% | +2.47% |
| module / web_server / gc.collect() ms | 42.01 | 44.25 | +5.34% | +16.17% | -4.89% | +4.35% |

## Frequency, total timing and maxima

Counts and callback-time fractions are separate measurements, not evidence of individual collection heap sizes. Fractions are mean percentages of run duration. Subtracting displayed fractions produces percentage points, not relative percentage changes.

| Rooting / workload | Parallel collections: baseline → current | Serial collections: baseline → current | Parallel callback fraction: baseline → current | Serial callback fraction: baseline → current |
|---|---:|---:|---:|---:|
| frame / mixed | 13284.20 → 13028.00 | 10997.50 → 10825.30 | 59.64% → 58.95% | 67.16% → 66.69% |
| frame / chain | 28.70 → 29.00 | 30.00 → 29.70 | 97.69% → 97.77% | 98.14% → 98.38% |
| frame / graph | 5946.30 → 5886.60 | 7291.00 → 7168.10 | 87.77% → 87.84% | 85.07% → 85.22% |
| frame / ai_workload | 36.10 → 37.90 | 48.40 → 55.20 | 98.18% → 98.37% | 98.81% → 99.23% |
| module / mixed | 550.80 → 548.10 | 459.10 → 457.30 | 53.39% → 53.14% | 61.11% → 60.85% |
| module / chain | 28.70 → 28.30 | 30.20 → 29.40 | 97.57% → 97.76% | 98.27% → 98.13% |
| module / graph | 6774.40 → 6789.50 | 8677.20 → 8529.00 | 88.94% → 88.83% | 86.06% → 86.23% |
| module / ai_workload | 37.00 → 38.80 | 49.10 → 55.20 | 98.25% → 98.57% | 98.84% → 99.29% |

Other recorded negative timing changes are listed below. Run maximum means are means of each run's maximum, not percentiles. Relative callback-fraction changes are not percentage-point changes. No tiny positive value is relabelled exact neutrality.

| Rooting / workload / metric | Parallel change | Half 1 | Half 2 | Serial control change |
|---|---:|---:|---:|---:|
| frame / chain / callback fraction | +0.08% | +0.08% | +0.07% | +0.25% |
| frame / graph / run maximum mean | +10.35% | +12.95% | +8.10% | +23.81% |
| frame / graph / callback total ms | +0.08% | -0.12% | +0.29% | +0.19% |
| frame / graph / callback fraction | +0.08% | -0.13% | +0.28% | +0.18% |
| frame / ai_workload / callback total ms | +1.03% | +4.08% | -1.77% | -5.31% |
| frame / ai_workload / callback fraction | +0.20% | +0.13% | +0.27% | +0.42% |
| module / chain / callback fraction | +0.20% | -0.10% | +0.50% | -0.14% |
| module / ai_workload / callback fraction | +0.33% | +0.15% | +0.52% | +0.46% |

## What the three FT experiments establish

| Experiment | Invocation context | Module controlled means higher | Module higher in both halves | Frame layered change |
|---|---|---:|---:|---:|
| [Original full](../FT-PROJECT-RESULTS.md) | Original full `__main__`, preceding sustained workloads | 8/8 | 8/8 | +12.05%, both halves positive |
| [Focused](../focused-collections/RESULTS.md) | Controlled cases only, normal module import | 3/8 | 1/8 | -4.82%, opposing halves |
| This unchanged full repeat | Original full `__main__`, preceding sustained workloads, later time window | 4/8 | 0/8 | +4.17%, both halves positive |

The focused invocation alone could not distinguish a context-dependent problem from other variation. This full repeat restores the original invocation and still does not reproduce the broad module pattern. An explanation based solely on normal import versus `__main__`, or solely on omitted sustained phases, is insufficient for all three outcomes. Actual heap/allocator state, adaptation history and host conditions were not held identical or continuously recorded. One fixed binary per source does not isolate build/profile effects. No cause is established.

Five runs within a leg share one process and time window. ABBA halves are two comparisons, not independent replicated builds. A modest mean with strongly opposing halves is not an accepted null result. Nor does the failed broad repeat erase the seven frame increases or frame AI-shaped throughput decrease. Keep all three datasets separate rather than pooling their different contexts and windows.

## Remaining work and replay

For the remaining frame differences, an independently rebuilt PGO baseline/current pair and generated-code inspection can test whether the pattern follows this binary pair. For module variation, a useful next experiment must distinguish competing state/history explanations rather than change the collector until one result looks better. Those are possible investigations, not authorized atomic, barrier, traversal, queue, threshold, adaptation or failure-policy changes.

The sixteen full-default pyperformance suites remain incomplete pending agreement on dependency compatibility repairs. Current hosted Linux/Windows/macOS source artifacts and job outcomes remain unverified. Full local debug passes do not replace hosted coverage. This complete FT repetition does not finish the handoff goal.

From the parent root:

```bash
python3 \
    benchmarks/results/investigations/integration-validation-2026-10-16/analyse_project_abba.py \
    benchmarks/results/investigations/integration-validation-2026-10-16/full-ft-repeat/evidence \
    --mode ft
```

[All raw legs, logs, checks and the 72-row report](evidence/). Archive JSONs are byte-identical to scratch originals; compressed logs decompress byte-identically. Original hashes and archive hashes are preserved separately. No scratch data was removed, workload dropped or runtime-mode check bypassed.
