# Full repaired-dependency pyperformance comparisons

## Question and protocol

Do the integrated changes alter execution time for the original default pyperformance workloads, in GIL or FT, with parallel GC enabled or disabled? The terminal outcome is a complete, reproducible comparison that names regressions and uncertainty, not a passing smoke or a favourable geometric mean.

Four sequential source-ABBA campaigns run GIL disabled, GIL enabled, FT disabled, FT enabled. Each executes baseline, integrated, integrated, baseline: sixteen rigorous suites, each retaining all 100 original programs and the expected 127 named results. Upstream calibration, processes, warmups, values, data and workload options remain unchanged. Workers use CPUs 0–31 and NUMA node 0; unrelated host services are not stopped. Initial host activity is recorded, but continuous exclusive ownership of those cores is not claimed.

The verified GCC 11.5 ARM64 PGO+LTO binaries include parallel-GC PGO training. Their actual sources are baseline `c67363fa59543ef5d572383af927f1cff88514a1` and integrated `388fd5bb46fdda6b464db566faf818505c3d6eef`. They are not rebuilt or relabelled as the latest CI-tested source `b91445e0b95454e32b982770f6e3c864beb5a528`; that later commit removes an uncalled wrapper. Frozen builds avoid introducing another PGO rebuild difference into this comparison.

All four prepared environments use the same dependency versions and repairs. Baseline/integrated package inventories must match within each ABI. SQLAlchemy 1.4.19 uses the approved supported pure-Python implementation on both sides; Coverage uses native CTracer and the other required native extensions remain native. Do not pool these results with historical native-SQLAlchemy measurements. [Complete dependency readiness](../benchmarks/dependency-repair/full-readiness-evidence/README.md) and [runner verification](../benchmarks/dependency-repair/prepared-execution-evidence/README.md) precede measurements.

## Falsifiers and reporting

A changed binary, source, original benchmark file, hook or prepared dependency invalidates the affected comparison. The controller verifies input fingerprints before and after each campaign; the runner validates executable identity and dependencies before and after each suite. Wrong worker GIL/collector state, missing hook entries, a failed program, mismatched named results or changed recorded work stops the campaign. Earlier raw program results remain available; no incomplete campaign is declared successful.

For each named result, report baseline and integrated leg means and both ABBA half-comparisons, alongside the pooled upstream comparison. Execution-time ratio integrated/baseline has a null value of 1; above 1 is slower, below 1 is faster. Report serial controls beside parallel results. A geometric mean is a summary, not evidence that individual regressions disappeared. Retain variance and upstream stability warnings. Do not infer benefit from a small difference without support from repeated legs; name inconclusive results and rerun disputed ones rather than inventing a universal noise floor.

These are comparisons between sources with runtime policy fixed. They do not directly establish the effect of enabling parallel GC within one unchanged binary, or feature compilation cost against a feature-off build. Those are separate experiments.

## Execution and progress

The CI evidence was committed separately as `2528c5c`. Prepared execution, tests, documentation and smoke evidence were committed as `589ba0c`. The ten new runner tests pass; existing 76-test parent selections pass in GIL and FT. All four original `telco` smoke ABBA campaigns pass. Their short-run timings are not performance evidence. These local checks do not imply that the new runner option has already passed hosted CI.

The full launch command, from `parallel_gc`, is:

```bash
bash benchmarks/dependency-repair/run_rigorous_campaigns.sh \
    /data/users/alexturner/parallel_gc \
    /tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW \
    /tmp/parallel-gc-pyperformance-repaired-20261019-ZKtZmg \
    /tmp/parallel-gc-pyperformance-rigorous-6a93Gj/full-v4
```

The output root must not exist. `controller.log` records campaign starts and completions; each mode log names the active program and its index. Per-program JSON survives a failure. `campaign.json` is written only after all four source legs complete. The parent revision, fingerprints, dependencies, raw suites and comparisons are retained for the final report. No performance outcome is asserted by this prospective protocol. The sixteen full suites require substantial time; completion is determined by those records, not an assumed overnight deadline.

The first launch stopped before any benchmark: the tracked `pyperformance/benchmarks` entry is a symlink to a directory, which the file-only fingerprint command rejected. The controller now fingerprints symlink targets explicitly and hashes ordinary tracked files. The failed launch evidence remains in the original `full/` output; measurements use fresh `full-v2/` output. This correction changes provenance collection only.

The second launch revalidated all eight complete readiness contexts and dependency inventories, then stopped before measurements: fingerprint loop variables were global shell variables and changed the outer campaign mode. The function now declares those variables local. The failed evidence remains in `full-v2/`; actual measurements use fresh `full-v3/`. Neither failed launch produced performance results.

The third launch completed the first rigorous `2to3` invocation but its validator rejected varying hook-entry metadata. The 41 original runs have four hook entries in calibration and three in each measured run. pyperf's common metadata deliberately omits fields that differ between runs; absence there does not mean the hook was absent. The corrected validator checks every saved run individually, including calibration, and still rejects any missing/nonpositive entry count or incorrect GIL/collector state. Twelve tests pass, including a varying-entry positive control and a single bad-run negative control; the retained original `2to3` result passes revalidation. No collector, hook, workload or rigorous parameter changed. Failed attempts, logs and the raw result are preserved in [per-run validation evidence](../benchmarks/dependency-repair/per-run-validation-evidence/README.md). The complete source-ABBA campaigns restart in fresh `full-v4/`; the isolated result is not pooled into them.

## Reproduce the descriptive analysis after completion

The [analysis tool](../benchmarks/analyse_pyperformance_abba.py) implements the leg-weighted calculation declared above. It requires a completed rigorous default campaign, four matching source legs, 100 preserved original-program outputs per leg, 127 matching named results, recorded digests, matching recorded work and per-run runtime attestation. It rejects short smokes and incomplete campaigns. Its JSON retains each leg's mean, within-leg standard deviation, measured-process count, value count and both half-comparisons; Markdown lists every result. These statistics describe the measurements, not independent source replications or automatic acceptance.

For each of `gil-disabled`, `gil-enabled`, `ft-disabled`, `ft-enabled`, using a new output prefix:

```bash
"$driver_python" benchmarks/analyse_pyperformance_abba.py \
    "$campaign_root/gil-disabled" \
    --output-prefix "$new_analysis_directory/gil-disabled"
```

Eight analysis tests pass using real pyperf fixture files. Positive controls check the arithmetic and preserve opposing half-directions; negative controls reject missing legs, changed digests/names, missing original-program output, debug campaigns and a partial inventory. A direct CLI check against the currently incomplete live campaign exits 2 and creates no analysis output. [Verification evidence](../benchmarks/dependency-repair/analysis-verification-evidence/README.md). This analysis preparation does not modify collector code, the measurement runner, hooks, workloads or prepared environments.

## Completed-suite checkpoint — 19 October, 23:33 UTC

The first GIL disabled baseline suite completed all 100 programs and 127 named results. Its saved per-run runtime/hook checks pass. It contains 5,004 measured run records and 15,852 values; these are within-leg measurements, not independent source replications. The combined suite, all per-program files and provenance have been [preserved and verified](../benchmarks/results/pyperformance/repaired-source-abba-2026-10-19/first-complete-leg/README.md). The first integrated-source leg is running. No four-leg comparison or complete sixteen-suite outcome is claimed by this checkpoint.
