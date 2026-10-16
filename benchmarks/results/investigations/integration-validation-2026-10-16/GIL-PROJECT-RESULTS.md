# GIL integrated-build comparison: complete project ABBA

## Outcome

This comparison records lower parallel-mode throughput in four of eight sustained cases, larger mean callback durations in six of eight cases, and longer controlled `gc.collect()` times in thirteen of sixteen cases. It does not establish performance neutrality. Several changes also appear in the serial controls, and some ABBA halves disagree. These observations do not establish that the collector integration caused the changes.

The negative throughput changes are frame-rooted mixed −1.31%, frame-rooted graph −3.40%, module-cache mixed −2.16%, and module-rooted graph −1.67%. Their serial controls change −1.18%, −2.91%, −2.03%, and −1.46%, respectively. Both mixed-workload halves are slower; the graph halves disagree in direction. Do not dismiss the measured decreases or label them statistically significant from this one build pair.

Mean callback duration increases are substantial: frame mixed +30.04%, frame graph +33.34%, frame AI workload +16.43%, module-cache mixed +15.49%, module graph +24.12%, and module AI workload +13.89%. Serial-control increases are +31.42%, +32.78%, +16.36%, +9.04%, +19.72%, and +16.48%. The module-cache mixed and module graph differences warrant particular follow-up because their parallel increases exceed the corresponding serial increases. That comparison is a diagnostic pattern, not a confound correction or proof of cause.

## Exact comparison and scope

- Baseline CPython: `c67363fa59543ef5d572383af927f1cff88514a1`.
- Candidate CPython: `388fd5bb46fdda6b464db566faf818505c3d6eef`.
- Source order: baseline, candidate, candidate, baseline. Four complete invocations ran on 16 October 2026 from 17:51:41 to 23:17:25 UTC: five hours, 25 minutes, 44 seconds in total.
- One fresh GCC 11.5.0 AArch64 PGO+LTO GIL binary per source, with verified native decimal and parallel-GC PGO training. Sources were recorded clean; executable hashes and local selected-test evidence are preserved in [build-evidence](build-evidence/).
- Unchanged full project suite: five runs per arm, 60-second sustained phases, four application threads, nominal 500,000-member heaps, seed 42, three controlled-collection warmups and 80% surviving clusters. CPU affinity 0–31 and NUMA CPU/memory node 0.
- GC worker selection is adaptive, starting at four with the existing two-to-sixteen range; sixteen is the ceiling, not a fixed active-worker count. Original and module-rooted variants are distinct cases.

The three candidate commits remove unreferenced helpers, add an opt-in debug verifier, and add incremental header dependencies. No GIL serial-collector source file changes in this range. Release measurements do not enable the debug verifier. This narrows the source hypotheses; it does not prove identical generated machine code, PGO profiles, heap layout or system conditions.

All four inputs passed source-order, build-mode, configuration, placement, complete-workload and sample-count validation. Controlled generated-member sequences match both modes and all source legs. These counts are `sum(len(cluster) for cluster in clusters)`, not the total number of GC-tracked supporting containers or the count returned by `gc.collect()`.

## Sustained measurements

Each value is a mean of run-level measurements, with whole source legs weighted equally. Throughput is the workload's reported work units per second; mixed completions and synthetic generated members are not one common unit to aggregate. Callback timing is the start-to-stop duration of one collection, not the interval between collections or an application-latency percentile.

Changes are `100 × (candidate / baseline − 1)`. The null ratio is one. Negative throughput and positive duration changes are worse. Half 1 compares candidate leg 2 with baseline leg 1; half 2 compares candidate leg 3 with baseline leg 4. Serial controls have the same workload but disabled parallel GC.

| Rooting / workload / metric | Baseline parallel mean | Candidate parallel mean | Parallel change | Half 1 | Half 2 | Serial control change |
|---|---:|---:|---:|---:|---:|---:|
| frame / mixed / throughput | 2456.99 | 2424.81 | -1.31% | -1.08% | -1.53% | -1.18% |
| frame / mixed / callback mean ms | 1.48 | 1.93 | +30.04% | +16.81% | +44.90% | +31.42% |
| frame / chain / throughput | 3353201.44 | 3383673.07 | +0.91% | -1.32% | +3.23% | +3.11% |
| frame / chain / callback mean ms | 41.09 | 36.66 | -10.79% | +21.87% | -30.14% | -22.79% |
| frame / graph / throughput | 1177337.19 | 1137264.91 | -3.40% | +0.57% | -7.17% | -2.91% |
| frame / graph / callback mean ms | 4.95 | 6.60 | +33.34% | +45.90% | +23.64% | +32.78% |
| frame / ai_workload / throughput | 1949525.95 | 1982388.51 | +1.69% | +3.63% | -0.20% | +1.51% |
| frame / ai_workload / callback mean ms | 18.09 | 21.06 | +16.43% | +45.47% | +1.19% | +16.36% |
| module / mixed / throughput | 2345.31 | 2294.54 | -2.16% | -2.06% | -2.26% | -2.03% |
| module / mixed / callback mean ms | 2.25 | 2.60 | +15.49% | +19.95% | +11.22% | +9.04% |
| module / chain / throughput | 3244877.54 | 3406323.50 | +4.98% | +1.10% | +9.10% | +5.01% |
| module / chain / callback mean ms | 45.24 | 38.47 | -14.96% | +16.34% | -33.38% | -20.04% |
| module / graph / throughput | 1267777.54 | 1246608.29 | -1.67% | +1.09% | -4.33% | -1.46% |
| module / graph / callback mean ms | 4.33 | 5.37 | +24.12% | +47.31% | +7.18% | +19.72% |
| module / ai_workload / throughput | 1969903.28 | 1995101.15 | +1.28% | +0.44% | +2.13% | +0.69% |
| module / ai_workload / callback mean ms | 16.12 | 18.36 | +13.89% | +51.15% | -5.34% | +16.48% |

## Controlled collections

These timings bracket `gc.collect()`. Unlike sustained callback means, the generated-member sequences and surviving-cluster selection are controlled. The sequences are retained in the machine-readable report; they must not be assumed to equal the nominal requested heap size.

| Rooting / workload / metric | Baseline parallel mean | Candidate parallel mean | Parallel change | Half 1 | Half 2 | Serial control change |
|---|---:|---:|---:|---:|---:|---:|
| frame / chain / gc.collect() ms | 37.39 | 37.00 | -1.05% | +1.53% | -3.46% | +0.48% |
| frame / tree / gc.collect() ms | 41.62 | 45.29 | +8.82% | +5.52% | +12.14% | +20.17% |
| frame / wide_tree / gc.collect() ms | 41.87 | 45.90 | +9.62% | +19.15% | +0.58% | +9.26% |
| frame / graph / gc.collect() ms | 45.73 | 43.86 | -4.08% | -1.23% | -6.80% | -0.58% |
| frame / layered / gc.collect() ms | 38.79 | 39.36 | +1.46% | -1.01% | +3.94% | +3.20% |
| frame / independent / gc.collect() ms | 38.43 | 40.97 | +6.63% | +5.16% | +8.14% | +9.00% |
| frame / ai_workload / gc.collect() ms | 37.93 | 39.11 | +3.11% | -1.38% | +7.70% | +1.41% |
| frame / web_server / gc.collect() ms | 45.69 | 49.11 | +7.50% | +6.19% | +8.76% | +6.35% |
| module / chain / gc.collect() ms | 55.70 | 58.64 | +5.28% | -1.56% | +12.26% | +8.65% |
| module / tree / gc.collect() ms | 66.59 | 73.76 | +10.76% | +6.25% | +15.63% | +12.85% |
| module / wide_tree / gc.collect() ms | 61.90 | 67.30 | +8.73% | +5.23% | +12.29% | +10.11% |
| module / graph / gc.collect() ms | 67.77 | 72.41 | +6.84% | +3.80% | +9.78% | +7.61% |
| module / layered / gc.collect() ms | 60.74 | 61.83 | +1.79% | +3.92% | -0.25% | +0.21% |
| module / independent / gc.collect() ms | 56.39 | 59.14 | +4.88% | +8.07% | +1.82% | +7.47% |
| module / ai_workload / gc.collect() ms | 55.05 | 55.62 | +1.02% | +0.34% | +1.72% | +2.78% |
| module / web_server / gc.collect() ms | 66.62 | 63.64 | -4.47% | -7.92% | -0.81% | -2.16% |

## Frequency and callback-time fraction

The cases with increased mean callback duration generally perform fewer collections per run. That is observed in both modes. It does not establish the heap size of each individual collection, which this dataset does not record. Callback-time fractions are percentages of the run duration; differences between displayed fractions are percentage points, not relative percentages.

| Rooting / workload | Parallel collections: baseline → candidate | Serial collections: baseline → candidate | Parallel callback time: baseline → candidate | Serial callback time: baseline → candidate |
|---|---:|---:|---:|---:|
| frame / mixed | 25684.20 → 21544.30 | 26197.50 → 21890.00 | 63.13% → 68.87% | 62.37% → 68.39% |
| frame / chain | 1574.00 → 1643.50 | 1364.30 → 1637.40 | 99.84% → 99.88% | 99.87% → 99.87% |
| frame / graph | 11111.10 → 8534.80 | 10735.40 → 8316.00 | 89.72% → 92.67% | 90.18% → 92.97% |
| frame / ai_workload | 3740.00 → 2945.40 | 4103.30 → 3217.70 | 98.60% → 99.02% | 98.46% → 98.93% |
| module / mixed | 19287.10 → 17389.90 | 19149.70 → 17916.40 | 72.07% → 74.97% | 72.30% → 74.16% |
| module / chain | 1434.60 → 1565.70 | 1375.60 → 1612.60 | 99.88% → 99.92% | 99.87% → 99.90% |
| module / graph | 12612.20 → 10214.60 | 11664.80 → 9661.50 | 88.52% → 91.28% | 89.58% → 91.86% |
| module / ai_workload | 4189.20 → 3315.50 | 4160.20 → 2831.40 | 98.37% → 98.90% | 98.38% → 99.03% |

## Variation, limitations and next falsifiable steps

Every sample, per-leg standard deviation and range, both halves, serial controls, callback totals, run maxima and actual generated-member sequences are preserved in [gil-source-analysis.json](gil-source-analysis.json). Run maxima are not percentiles. The five runs in one leg share a time window; they are not five independent source-build experiments. There are only two time windows and one PGO binary per source. No significance, noise-floor or acceptance threshold is assigned.

The positive measurements remain in the tables: four throughput increases, two lower mean callback durations and three faster controlled collection cases. Direction disagreements are visible rather than hidden behind an aggregate. Neither positive nor negative observations are a release verdict.

After the scheduled FT and pyperformance campaigns finish, use their controls to select focused repetition. Competing experiments must not be started during those measurements.

- Shared build/system/workload effect: repeated baseline/candidate and same-binary controls should reproduce changes in both serial and parallel arms rather than a stable parallel-only difference. Rebuilding with fresh profiles can distinguish a source pattern from this particular binary pair. No such replication has yet been performed.
- Parallel-specific effect: repeat the module-cache mixed callback case with both source builds and modes. A source-associated parallel difference should recur in both ABBA halves, with an effect not mirrored by serial controls. The current figures alone do not prove it.
- Collection-frequency explanation: record whether longer mean callbacks coincide with fewer collections while throughput and total callback time are separately measured. To claim larger heaps per collection would require additional heap-size evidence, not just the existing frequency correlation.

No collector redesign, threshold change or atomic/barrier change follows from this report. Functional selected tests passed; full hosted Linux/Windows/macOS CI, FT measurements and pyperformance are still separate incomplete requirements.

## Replay

The four complete Git-preserved measurement files and original scratch-file hashes are listed in [project-legs](project-legs/). Git copies add only an EOF newline, with their separate hashes recorded. The machine report fingerprints those preserved inputs. Replay from the parent repository:

```bash
python3 \
  benchmarks/results/investigations/integration-validation-2026-10-16/analyse_project_abba.py \
  benchmarks/results/investigations/integration-validation-2026-10-16/project-legs \
  --mode gil
```

[Analysis method and machinery tests](ANALYSIS.md). No incomplete-build or abandoned-campaign data is used.
