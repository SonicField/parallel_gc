# Complete-project-ABBA analysis

Run from the `parallel_gc` parent repository, only after all four legs of the selected build mode finish:

```bash
python3 \
  benchmarks/results/investigations/integration-validation-2026-10-16/analyse_project_abba.py \
  /tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW/results/project \
  --mode gil
```

Repeat with `--mode ft`. Output is JSON on standard output; preserve it with the raw legs when the complete comparison is available. The tool requires the fixed baseline/candidate source pair, standard full-suite parameters, clean CPython source content, recorded matching NUMA policy, CPU affinity 0–31, all workloads and five samples per arm. Missing files or mismatched data exit nonzero without a partial report.

The report covers the original and module-rooted controlled collections, mixed workload and three sustained synthetic workloads. Every metric includes all five samples per arm per leg, mean, sample standard deviation, minimum and maximum. It reports the two whole-leg baseline/candidate means, the signed overall change, the two ABBA-half changes, matching serial-arm controls and within-build parallel/serial changes.

Changes mean `100 × (candidate / baseline − 1)`. The null ratio is 1, hence zero percent change. Negative throughput change is worse; positive collection-time or callback-duration change is worse. A zero denominator yields JSON `null`, not a fabricated zero-percent result. Collection frequency and achieved run duration have no preferred direction by themselves.

Sustained callback means are averaged over runs, not weighted by the number of collections. The maximum-duration metric is the mean of each run's maximum; it is neither a percentile nor the maximum over the entire campaign. Callback timing spans the `start` and `stop` callbacks of one collection and is not FT stopped-world duration. Controlled collection timing spans `gc.collect()`; actual generated object-count sequences must match across serial/parallel arms and source legs. Counts need not equal the nominal requested heap size.

The five within-leg runs share a time window. Their standard deviation is descriptive variation, not a source-effect confidence interval. The two ABBA halves expose disagreement across time windows. Serial arms expose changes that are not confined to enabled parallel traversal, including binary-layout or PGO effects. None proves causation by itself. No statistical-significance, noise-floor or acceptance cutoff is encoded; unresolved differences need repetition and investigation before attribution.

Machinery tests use artificial data and make no performance claim:

```bash
python3 -m unittest discover \
  -s benchmarks/results/investigations/integration-validation-2026-10-16 \
  -p test_analyse_project_abba.py
```

The pyperformance campaigns retain their existing attestation and binary-ABBA comparison machinery. This tool analyses project-suite data only; it does not modify measurements or replace pyperformance result validation.
