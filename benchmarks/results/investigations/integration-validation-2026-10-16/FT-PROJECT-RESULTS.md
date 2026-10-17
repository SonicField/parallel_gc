# FT integrated-build comparison: complete project ABBA

Follow-up on 17 October: the [focused diagnostic](focused-collections/RESULTS.md) and [unchanged full repeat](full-ft-repeat/RESULTS.md) do not reproduce this report's broad module-rooted controlled pattern. The full repeat retains other negative results. This original dataset and its outcome below remain unchanged; no code repair or performance-neutrality claim follows.

## Outcome

This comparison records lower parallel-mode throughput in five of eight sustained cases and longer controlled `gc.collect()` times in ten of sixteen cases. Seven of eight mean callback durations have a positive recorded change; frame mixed is only +0.0023%, while the other six increases range from +1.57% to +14.36%. No significance or acceptance threshold is assigned. Performance neutrality is not established.

The strongest negative pattern is module-rooted controlled collection: all eight shapes take longer in both ABBA halves. Overall increases range from +18.72% for tree to +34.81% for layered. Module graph increases +27.02% while its serial control decreases −10.21%; module independent increases +21.13% while its serial control decreases −1.03%. The other serial controls range from +0.32% to +14.87%. These controls do not generally mirror the parallel increases. This is a source-associated pattern in this binary pair that needs focused reproduction and diagnosis, not proof that a particular collector mechanism caused it.

Module-cache mixed throughput decreases −7.41% (halves −3.19% and −11.58%) while its serial control increases +0.54%. Its mean callback duration increases +14.36% (halves +1.84% and +27.81%); the serial mean decreases −0.85%. The measured parallel difference worsens in the second window. Do not dismiss it as noise, infer a worker-count cause without measurements, or repair it by changing collector design.

The other negative throughput changes are frame chain −1.43%, module chain −3.43%, module graph −0.99%, and module AI workload −0.89%. Both chain throughput halves disagree in direction. Module graph and module AI workload are slower in both halves; graph's serial control is also slower (−1.94%), whereas AI's serial control increases +0.50%.

## Exact comparison and scope

- Baseline CPython: `c67363fa59543ef5d572383af927f1cff88514a1`.
- Candidate CPython: `388fd5bb46fdda6b464db566faf818505c3d6eef`.
- Source order: baseline, candidate, candidate, baseline. Four complete FT invocations ran from 23:17:25 UTC on 16 October 2026 to 05:37:40 UTC on 17 October: six hours, 20 minutes, 15 seconds.
- One fresh GCC 11.5.0 AArch64 PGO+LTO FT binary per source, with `--disable-gil --with-parallel-gc`, native decimal and verified parallel-GC PGO training. Clean CPython sources and executable hashes are recorded in [build-evidence](build-evidence/). Recorded parent checkpoints are dirty during preceding evidence work; these observations are preserved, not presented as clean parents. The timed project implementation and controller fingerprints remained unchanged.
- Unchanged full project suite: five runs per arm, 60-second sustained phases, four application threads, nominal 500,000-member heaps, seed 42, three controlled-collection warmups and 80% surviving clusters. Affinity 0–31 and NUMA CPU/memory node 0.
- Worker selection is adaptive, starting at four with the existing two-to-sixteen range. Sixteen is the ceiling, not a fixed active-worker count. This dataset does not record an adaptive worker-count history; no tuning explanation is inferred.

The candidate range removes unreferenced helpers, adds an opt-in debug verifier, and adds incremental header dependencies. The release measurements do not enable the debug verifier. These source facts do not establish identical generated machine code, PGO profiles, heap layout or system conditions.

All four inputs passed source-order, build-mode, configuration, placement, complete-workload and sample validation. All 72 analysis rows were also checked against raw input samples using a separate arithmetic calculation; both arm means and signed changes match at displayed precision. All 24 analysis-machinery tests pass. Controlled generated-member sequences match both arms and all source legs. Counts are `sum(len(cluster) for cluster in clusters)`, not all GC-tracked supporting containers or the count returned by `gc.collect()`. This report asks whether the integration changed the earlier implementation, not whether enabling parallel GC is faster than serial in every workload.

## Sustained measurements

Values are means of run-level samples with whole source legs weighted equally. Work units per second differ between mixed completions and synthetic generated members; they must not be aggregated as one common unit. Callback timing spans one collection's start/stop callbacks. It is neither the interval between collections, an application-latency percentile, nor FT stopped-world duration.

Changes are `100 × (candidate / baseline − 1)`; the null ratio is one. Negative throughput and positive duration changes are worse. Half 1 compares candidate leg 2 against baseline leg 1; half 2 compares candidate leg 3 against baseline leg 4. Serial controls have parallel GC disabled. Rounded +0.00% for frame mixed callback mean is +0.0023% in the machine report, not a claim of exact equality.

| Rooting / workload / metric | Baseline parallel mean | Candidate parallel mean | Parallel change | Half 1 | Half 2 | Serial control change |
|---|---:|---:|---:|---:|---:|---:|
| frame / mixed / throughput | 3382.24 | 3391.46 | +0.27% | -0.66% | +1.22% | +0.09% |
| frame / mixed / callback mean ms | 2.67 | 2.67 | +0.00% | -1.03% | +1.04% | -0.19% |
| frame / chain / throughput | 6227803.14 | 6138752.78 | -1.43% | -16.32% | +15.43% | +4.30% |
| frame / chain / callback mean ms | 3136.68 | 3270.27 | +4.26% | +26.50% | -14.48% | -5.87% |
| frame / graph / throughput | 1907036.97 | 1927153.83 | +1.05% | +0.66% | +1.44% | +0.02% |
| frame / graph / callback mean ms | 8.92 | 8.88 | -0.48% | -0.60% | -0.35% | +2.26% |
| frame / ai_workload / throughput | 2829867.80 | 2955360.40 | +4.43% | +4.22% | +4.65% | -1.45% |
| frame / ai_workload / callback mean ms | 1778.36 | 1896.69 | +6.65% | -3.84% | +17.70% | +38.89% |
| module / mixed / throughput | 3830.42 | 3546.54 | -7.41% | -3.19% | -11.58% | +0.54% |
| module / mixed / callback mean ms | 59.26 | 67.78 | +14.36% | +1.84% | +27.81% | -0.85% |
| module / chain / throughput | 6040514.11 | 5833588.06 | -3.43% | +2.96% | -9.63% | -4.85% |
| module / chain / callback mean ms | 2889.88 | 3036.31 | +5.07% | +2.60% | +7.54% | +5.63% |
| module / graph / throughput | 1804121.62 | 1786179.22 | -0.99% | -0.61% | -1.38% | -1.94% |
| module / graph / callback mean ms | 7.81 | 7.94 | +1.57% | -0.07% | +3.24% | +3.85% |
| module / ai_workload / throughput | 2849921.74 | 2824658.68 | -0.89% | -0.33% | -1.46% | +0.50% |
| module / ai_workload / callback mean ms | 1707.99 | 1834.91 | +7.43% | -3.64% | +18.29% | +18.79% |

## Controlled collections

These timings bracket `gc.collect()`. The generated-member sequences and surviving-cluster selection are controlled and preserved. The frame results are mixed: six lower times, frame layered +12.05% and frame independent +0.10%. Independent's halves disagree. Layered is slower in both halves while its serial control is faster in both. Every module-rooted shape is slower in both halves.

| Rooting / workload / metric | Baseline parallel mean | Candidate parallel mean | Parallel change | Half 1 | Half 2 | Serial control change |
|---|---:|---:|---:|---:|---:|---:|
| frame / chain / gc.collect() ms | 33.04 | 32.20 | -2.55% | -1.76% | -3.35% | -4.73% |
| frame / tree / gc.collect() ms | 34.02 | 33.83 | -0.54% | -5.45% | +4.78% | -1.75% |
| frame / wide_tree / gc.collect() ms | 32.95 | 31.32 | -4.95% | -2.90% | -6.94% | -2.63% |
| frame / graph / gc.collect() ms | 40.42 | 39.19 | -3.03% | +5.39% | -10.50% | -3.43% |
| frame / layered / gc.collect() ms | 45.26 | 50.71 | +12.05% | +4.16% | +20.26% | -7.06% |
| frame / independent / gc.collect() ms | 32.77 | 32.80 | +0.10% | +2.73% | -2.52% | -3.65% |
| frame / ai_workload / gc.collect() ms | 43.42 | 40.95 | -5.69% | -6.95% | -4.42% | -3.05% |
| frame / web_server / gc.collect() ms | 33.41 | 31.58 | -5.49% | -5.75% | -5.23% | -3.75% |
| module / chain / gc.collect() ms | 39.50 | 49.70 | +25.83% | +13.75% | +39.08% | +0.32% |
| module / tree / gc.collect() ms | 43.05 | 51.11 | +18.72% | +15.36% | +21.95% | +3.73% |
| module / wide_tree / gc.collect() ms | 39.26 | 49.42 | +25.88% | +16.02% | +36.57% | +4.81% |
| module / graph / gc.collect() ms | 50.72 | 64.43 | +27.02% | +15.12% | +39.78% | -10.21% |
| module / layered / gc.collect() ms | 56.77 | 76.53 | +34.81% | +18.08% | +53.83% | +14.87% |
| module / independent / gc.collect() ms | 41.47 | 50.23 | +21.13% | +13.27% | +29.48% | -1.03% |
| module / ai_workload / gc.collect() ms | 50.30 | 62.46 | +24.16% | +15.08% | +34.04% | +3.33% |
| module / web_server / gc.collect() ms | 40.08 | 50.97 | +27.18% | +12.04% | +44.32% | +6.73% |

## Frequency and callback-time fraction

Collection counts and callback-time fractions are recorded separately from per-collection means. They do not establish the heap size of each individual collection. Fractions below are percentages of run duration; subtracting displayed fractions gives percentage points, not relative percentage change.

| Rooting / workload | Parallel collections: baseline → candidate | Serial collections: baseline → candidate | Parallel callback time: baseline → candidate | Serial callback time: baseline → candidate |
|---|---:|---:|---:|---:|
| frame / mixed | 13398.00 → 13435.30 | 11103.50 → 11146.80 | 59.58% → 59.74% | 67.25% → 67.38% |
| frame / chain | 28.30 → 27.80 | 29.90 → 29.80 | 97.77% → 97.66% | 98.10% → 98.24% |
| frame / graph | 5914.60 → 5942.50 | 7325.60 → 7190.90 | 87.89% → 87.87% | 85.12% → 85.45% |
| frame / ai_workload | 38.80 → 36.20 | 62.00 → 49.30 | 98.29% → 98.33% | 99.41% → 99.01% |
| module / mixed | 543.50 → 508.10 | 450.60 → 454.70 | 53.61% → 57.10% | 61.50% → 61.56% |
| module / chain | 29.70 → 29.50 | 30.10 → 29.60 | 97.62% → 97.49% | 98.35% → 98.21% |
| module / graph | 6835.10 → 6741.60 | 8717.60 → 8437.20 | 88.97% → 89.14% | 86.18% → 86.62% |
| module / ai_workload | 39.60 → 37.70 | 59.80 → 52.40 | 98.32% → 98.25% | 99.37% → 99.17% |

## Variation, limitations and next falsifiable steps

Every sample, per-leg standard deviation and range, both halves, serial controls, callback totals, run maxima and controlled generated-member sequences are preserved in [ft-source-analysis.json](ft-source-analysis.json). Run maxima are not percentiles. Five runs in a leg share one time window; they are not five independent source-build experiments. There is one PGO binary per source and only two paired windows. No statistical-significance, noise-floor or acceptance claim is assigned.

Positive source changes are also recorded rather than suppressed: three throughput increases, one lower mean callback duration, and six lower controlled collection times. These do not cancel the consistently slower module-rooted collections. Likewise, disagreement in the chain halves does not explain the module mixed, graph or controlled-collection patterns.

After the scheduled pyperformance campaigns finish, select focused experiments without overlapping their measurements:

- Reproduce module-rooted controlled collections and frame layered with the same parameters and both collector modes. The parallel-specific hypothesis predicts recurring increases in both halves without a matching serial-control change. A failed repeat would weaken attribution to source rather than erase the current evidence.
- Rebuild both revisions with fresh parallel PGO profiles, then repeat the affected source comparison. A pattern that follows one binary but not independently rebuilt copies points toward this build/profile pair; a repeatable source pattern warrants generated-code and perf inspection.
- Examine the relation between module mixed callback duration, total callback time, collection frequency and measured work. Explaining it through worker choices requires worker-history evidence that this campaign lacks. Explaining it through larger per-collection heaps requires actual per-collection heap evidence.
- Treat chain variability separately: its opposing throughput halves are not evidence for the same cause as the consistently slower controlled module cases.

No collector redesign, threshold change, queue change or atomic/barrier change follows from these results. Hosted Linux/Windows/macOS verification and the sixteen planned pyperformance suites remain incomplete. The GIL project report is [separate](GIL-PROJECT-RESULTS.md); its controls and workload units must not be silently pooled with FT.

## Replay

All four complete Git-preserved measurement files and original scratch-file hashes are listed in [project-legs](project-legs/). Git copies add only an EOF newline and have separate hashes. The machine report fingerprints those preserved inputs. From the parent repository:

```bash
python3 \
  benchmarks/results/investigations/integration-validation-2026-10-16/analyse_project_abba.py \
  benchmarks/results/investigations/integration-validation-2026-10-16/project-legs \
  --mode ft
```

[Analysis method and machinery tests](ANALYSIS.md). No abandoned or incomplete-build measurements are included.
