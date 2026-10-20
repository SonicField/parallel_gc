# Performance: method, evidence and acceptance rules

How to measure parallel GC, what has been measured, and the limits a change
must meet. Design context: [DESIGN.md](DESIGN.md). Validation status:
[VALIDATION.md](VALIDATION.md). Superseded detail:
`BENCHMARKING.md` (removed; `git show 724b74b:docs/BENCHMARKING.md`) and
`PERFORMANCE_INVESTIGATION_PLAN.md` (removed; `git show 724b74b:docs/PERFORMANCE_INVESTIGATION_PLAN.md`).

Historical campaign summaries retain their original interpretations. The
retention qualification and rejected-experiment discussion here supersede
claims that all earlier collection-shape heaps were fully live or that the
quick rebuild comparison established a universal noise floor.

## 1. Two benchmark systems, both required

General suites such as `pyperformance` detect whole-interpreter regressions
but mostly create little cyclic garbage, run few substantial collections and
report only program time. A neutral `pyperformance` result does not show that
parallel GC ran, scaled or kept pause behaviour. The project suite controls
heap size and topology, alternates serial and parallel runs, records collection
and callback intervals and throughput, and observes the adaptive controller.
It lives in this repository because it is large, specialist infrastructure.

A significant `pyperformance` regression is a release blocker even when the
GC-specific benchmarks improve.

## 2. Running the benchmarks

Always use optimized builds (`--enable-optimizations --with-lto`) in separate
directories. Debug builds distort results. The root `Makefile` and `tools/`
target an older workflow; do not use them for measurements.

```bash
(cd build-benchmark-gil && ../cpython/configure \
    --with-parallel-gc --enable-optimizations --with-lto)
make -C build-benchmark-gil -j"$(nproc)"
(cd build-benchmark-ft && ../cpython/configure \
    --with-parallel-gc --disable-gil --enable-optimizations --with-lto)
make -C build-benchmark-ft -j"$(nproc)"
```

### 2.1 pyperformance ABBA

The `pyperformance/` submodule is unmodified upstream. Activation lives in
`benchmarks/pyperformance_support/`, applied by a project-owned pyperf hook in
each measurement worker, which verifies `gc.get_parallel_config()` and records
a PID-bound attestation; the runner rejects results lacking it.

```bash
python3 -m venv .venvs/pyperformance-driver
.venvs/pyperformance-driver/bin/python -m pip install \
    --requirement pyperformance/pyperformance/requirements/requirements.txt
.venvs/pyperformance-driver/bin/python -m pip install --no-deps \
    --editable ./pyperformance --editable ./benchmarks/pyperformance_support

# smoke test (machinery only, not evidence)
.venvs/pyperformance-driver/bin/python benchmarks/run_pyperformance.py abba \
    --python build-benchmark-gil/python --benchmarks telco \
    --run-style debug --output-dir benchmarks/results/pyperformance/gil-smoke
# full comparison
.venvs/pyperformance-driver/bin/python benchmarks/run_pyperformance.py abba \
    --python build-benchmark-gil/python --benchmarks default \
    --run-style rigorous --output-dir benchmarks/results/pyperformance/gil-full
```

The order is disabled, enabled, enabled, disabled, which cancels first-order
linear drift but not random variance. All four raw suites, the combined runs,
the comparison and `campaign.json` provenance are kept. The target build needs
its normal optional modules (at least `zlib`). Runtime ABBA does not measure
the cost of compiling the feature in; that needs matched optimized builds with
and without `--with-parallel-gc`.

For the Python 3.16 dependency repairs, supply the already verified virtual environments. The runner checks that each environment uses the requested executable, requires `pip check`, records dependencies before and after execution, and refuses a changed environment. It calls the original upstream `Benchmark.run` with upstream rigorous options, retaining the original scripts, data and workload parameters. Every saved result must attest to the requested collector mode and compiled/runtime GIL state. No dependency installer runs in this mode.

```bash
"$driver_python" benchmarks/run_pyperformance.py binary-abba \
    --baseline-python "$baseline_python" \
    --candidate-python "$candidate_python" \
    --baseline-source "$baseline_source" \
    --candidate-source "$candidate_source" \
    --baseline-prepared-python "$baseline_venv_python" \
    --candidate-prepared-python "$candidate_venv_python" \
    --mode enabled --benchmarks default --run-style rigorous \
    --affinity 0-31 --timeout 300 \
    --work-root "$work_directory" --output-dir "$new_output_directory"
```

This is source ABBA: baseline, integrated, integrated, baseline with the runtime mode held fixed. Repeat with `--mode disabled` as the serial control, and separately for GIL and FT. It does not replace enabled/disabled ABBA within one binary. Single-suite and runtime ABBA commands accept `--prepared-python`. A failed program stops the campaign but retains earlier per-program results; it does not produce a passing partial suite. [Prepared-execution tests](../benchmarks/test_prepared_pyperformance.py) run in the pyperformance driver environment.

### 2.2 Project suite: `gc_perf_benchmark.py`

```bash
build-benchmark-ft/python benchmarks/gc_perf_benchmark.py --quick   # sanity only
build-benchmark-ft/python benchmarks/gc_perf_benchmark.py           # mixed workload
build-benchmark-ft/python benchmarks/gc_perf_benchmark.py --full --include-synthetic
```

Options: `--quick` (2 runs, 10 s), `--full` (5 runs, 60 s; synthetic tests
still need `--include-synthetic`), `--duration`, `--runs` (3), `--threads` (4),
`--heap-size` (500,000), `--json`, `--output`. With the module-rooted additions,
`--full --include-synthetic` took about 95 minutes per invocation in the
recorded AArch64 campaigns; budget separately for each ABBA invocation.

- **Mixed workload:** application threads choose randomly among deltablue,
  deepcopy, pickle_copy, async_tree (high cycles), richards, nbody (minimal)
  and comprehensions (none); one combined result.
- **Collection shapes (8):** chain, tree, wide_tree, graph, layered,
  independent, ai_workload (finalizers), web_server. Each timed collection
  keeps 80% of clusters live (`COLLECTION_SURVIVOR_RATIO`), held in a function
  local.
- **Module-rooted variants** (integrated from benchmark candidate `306644b`):
  the same collection shapes and sustained heaps with long-lived data held in
  module state, plus the mixed workload with a static 500,000-object
  module-rooted cache. Sustained shuffle/churn may temporarily hold stack
  references. Controlled collections release frame keep-set references before
  collecting. In FT, thread stacks are scanned as roots directly,
  while module state is reached through `sys.modules`. The two placements
  exercise known-root propagation differently (OPEN_ISSUES.md §2). Results
  appear under separate JSON keys. The
  [rooting integration report](../benchmarks/results/investigations/module-rooting-integration-2026-10-16/README.md)
  records the contract, positive controls and correction of the candidate's
  unsafe cross-thread frame-inspection test. No new performance measurements
  are claimed by the integration tests.
- **Creation-pool fix:** before benchmark commit `6c8bf14`, creation-pool
  threads kept their last generated clusters as frame locals. The "dropped"
  fraction could therefore remain reachable, with extra stack roots affecting
  propagation. A worker can process several tasks and retains only its last
  result, so the fraction retained depends on scheduling. **Historical
  collection-shape runs did not establish the intended 20% garbage fraction;
  their actual retained fraction is unknown.** The repair is integrated with
  deterministic scheduling and survivor checks; see the
  [ownership verification record](../benchmarks/results/investigations/creation-pool-retention-2026-10-16.md).
  Mixed and sustained workloads do not use this creation pool.
- **Metrics:** throughput; one collection's callback start-to-stop duration (mean and maximum); GC callback-active time (not additive in FT); controlled `gc.collect()` duration; parallel/serial speedup; geometric means. Callback duration is not the interval between successive collections or FT stopped-world duration.

Heaps come from deterministic per-worker streams seeded from 42; a pair is
rejected if object counts differ. Modes alternate within one binary with
equivalent rebuilt heaps. JSON records generated counts and dirty-tree
fingerprints.

### 2.3 Adaptive versus fixed workers: `gc_adaptive_benchmark.py`

Each invocation is one arm in a fresh process. A fixed arm sets the count
through `_testinternalcapi` before every recorded collection; this is test
infrastructure, not a runtime option. Run arms in ABBA order with the same
binary, seed, affinity and parameters; repeat for fixed 2, 4, 8 and 16:

```bash
run_arm() {
    "$PYTHON" benchmarks/gc_adaptive_benchmark.py --workers "$1" \
        --cycles 3 --collections-per-phase 20 --seed 42 --json > "$RESULTS/$2.json"
}
run_arm adaptive adaptive-a1; run_arm 4 fixed-4-b1
run_arm 4 fixed-4-b2;         run_arm adaptive adaptive-a2
```

Compare `elapsed_ns` and `parallel_ns_per_candidate` distributions per phase;
do not infer effectiveness from the endpoint. `workers_used` and a dispatch
counter prove parallel machinery ran (GIL counts attempts, FT counts phase
dispatches). GIL `small_cycles` is below threshold and expected to show zero.

### 2.4 Root-placement scaling matrix

**Diagnostic only.** These are single-collection timings on synthetic heaps.
They locate a weakness but are not evidence of application benefit; use the
project suite (§2.2) and the rules in §6 for that.

[`benchmarks/results/investigations/claude-scaling-2026-10-15/`](../benchmarks/results/investigations/claude-scaling-2026-10-15/)
contains `scale.py`, `cpu.py`, `run.sh` and `summarise.py`. They build a live
1M-object heap (graph, tree, lists or chain), hold it from a module global or a
frame local, re-pin the worker count before each collection and report the
wall time and per-phase timings from `gc.get_parallel_stats()`:

The recorded results used a **release build without PGO**
(`--disable-gil --with-parallel-gc`, no `--with-pydebug`); the single-thread
`mark_alive` behaviour also reproduces on PGO+LTO builds. From the parent
repository root, with a build in `build-scaling-ft/`:

```bash
D=benchmarks/results/investigations/claude-scaling-2026-10-15
# arguments: shape {graph,tree,lists,chain}, objects, workers {serial,2..16}, holder {global,local}
taskset -c 0-31 build-scaling-ft/python -I $D/scale.py graph 1000000 16 global
taskset -c 0-31 build-scaling-ft/python -I $D/scale.py graph 1000000 16 local
```

### 2.5 Other scripts

`gc_creation_analysis.py` (effect of creation-thread count, chain versus
clusters, abandoned threads versus pool), `gc_locality_benchmark.py`
(contiguous chains at one worker count; not a NUMA benchmark) and
`gc_production_experiment.py` (classifies 14 workloads by cyclic-garbage
volume).

## 3. Methodology

- Use at least five runs; pin affinity and NUMA (`numactl --cpunodebind=0
  --membind=0`); run on a quiet machine; warm up.
- Report every run and raw samples, never a favourable subset or a geometric
  mean alone.
- Record the exact command, parent and CPython revisions, dirty state,
  compiler, flags, executable hash, affinity, and observed worker counts.
- A `gc.callbacks` start-to-stop duration covers one collection call. Historical reports call it a callback interval; it is not time between collections. In FT it includes work outside the stopped-world sections and is not a stopped-world pause measurement. Controlled collection time, callback duration and throughput are distinct metrics.
- Do not compare across machines without recording the hardware.

## 4. Current evidence

### 4.1 Integration comparison, 16–17 October 2026

Baseline `c67363fa59543ef5d572383af927f1cff88514a1` and integrated `388fd5bb46fdda6b464db566faf818505c3d6eef` each have a fresh GIL and FT GCC 11.5 AArch64 PGO+LTO build with native decimal and verified parallel PGO training. Both sources use the same repaired ownership/module-rooted harness. Four complete ABBA legs per mode use unchanged `--full --include-synthetic`: five runs per arm, 60-second sustained phases, four application threads, nominal 500,000-member heaps, affinity 0–31 and NUMA node 0. This is a comparison between source builds, not the historical same-binary serial/parallel comparison below.

| Mode | Negative measurements | Interpretation limit |
|------|-----------------------|----------------------|
| [GIL](../benchmarks/results/investigations/integration-validation-2026-10-16/GIL-PROJECT-RESULTS.md) | Throughput decreases in four of eight sustained cases; mean callback duration increases in six; thirteen of sixteen controlled collections take longer. Frame mixed callback mean +30.04%, with serial control +31.42%; module mixed callback mean +15.49%, with serial control +9.04%. | Several controls move too; some halves disagree. Performance neutrality and collector-specific causation are not established. |
| [FT](../benchmarks/results/investigations/integration-validation-2026-10-16/FT-PROJECT-RESULTS.md) | All eight module-rooted controlled collections take longer in both halves (+18.72% to +34.81%). Module-cache mixed throughput −7.41% and mean callback duration +14.36%; serial controls +0.54% and −0.85%, respectively. | Consistent negative pattern in this binary pair; requires focused reproduction and diagnosis. Do not infer worker-count or heap-size causes that were not recorded. |

Both reports preserve positive measurements too, all samples, variation, both halves, serial controls, counts and raw hashes. There is one PGO binary per source and two paired time windows. No statistical-significance, universal noise-floor or acceptance cutoff is assigned. The null baseline/current ratio is one; performance neutrality is not established. [Protocol and full status](../benchmarks/results/investigations/integration-validation-2026-10-16/INVESTIGATION-STATUS.md).

A subsequent [focused FT controlled-case ABBA](../benchmarks/results/investigations/integration-validation-2026-10-16/focused-collections/RESULTS.md) uses the same binaries, parameters and generated-member sequences but omits preceding sustained workloads. It does not reproduce the broad module slowdown: five module means decrease, three increase +0.34% to +1.32%, only web-server in both halves. It imports the benchmark as a normal module rather than `__main__`; process/heap context and adaptation exposure also differ. This is inconclusive about cause, not a neutrality claim or an invalidation of the full data.

The subsequent [unchanged full FT repeat](../benchmarks/results/investigations/integration-validation-2026-10-16/full-ft-repeat/RESULTS.md) restores the original full `__main__` invocation and preceding sustained phases, using the same binaries. All four legs completed at 16:18 UTC on 17 October. The broad module pattern still does not reproduce: every module controlled case has a positive first-half and negative second-half change. Four overall module means increase, four decrease. Seven frame controlled cases increase in both halves (+2.43% to +5.91%). Frame mixed throughput decreases −1.11%, frame AI-shaped −3.93%, and module mixed −1.97%; the last has opposing halves. All 72 rows, serial controls, maxima, counts and callback totals are preserved and independently checked. No collector change, causal explanation or acceptance claim follows. The three experiments remain separate rather than pooling their contexts and time windows.

**Full-default pyperformance remains incomplete.** The first corrected suite failed Dask/Cloudpickle and Genshi on Python 3.16 API errors. Eight subsequent [all-program diagnostic checks](../benchmarks/results/investigations/integration-validation-2026-10-16/default-runtime-compatibility/README.md) find the same two failures in GIL and seven in FT, matching both source revisions and collector policies. The five additional FT programs load extensions that enable the GIL; worker attestation correctly rejects them. No workload was omitted or unsafe GIL override introduced. These short checks are not ABBA measurements.

Dependency repairs were approved and executed on 19 October in isolated environments. [All seven repairs](../benchmarks/dependency-repair/PLAN.md) and [complete readiness](../benchmarks/dependency-repair/full-readiness-evidence/README.md) pass: all 100 original programs execute in all eight contexts, with 127 named results each and no failures. Benchmark programs remain unchanged. Coverage retains CTracer; its extension and those of Dulwich, MarkupSafe and Greenlet remain native. FT runtime checks stay active and FT execution remains GIL-disabled. Alex approved SQLAlchemy 1.4.19's supported pure-Python build consistently across both sources and build modes. All four fresh complete environments pass `pip check`, including Dulwich's required urllib3 2.2.2 upgrade. These diagnostic execution checks are not performance evidence; at that readiness checkpoint all sixteen rigorous suites were outstanding. Different dependency implementations must not be mixed with historical measurements. [Hosted workflow successes](ci-results-2026-10-19.md) are user-reported; source/job-level artifacts remain unverified.

#### Rigorous repaired-dependency source comparisons, 19–20 October

Both full GIL source-ABBA campaigns and FT disabled now retain 100 original programs and 127 named results per leg, with unchanged rigorous settings and frozen sources/binaries from §4.1. FT enabled remains pending. Positive time change below means slower execution; null is 0%. These compare sources with runtime policy held fixed, not enabling/disabling one binary. They do not measure GC pauses.

| Runtime policy | Geometric-mean time change | Largest observed increases and uncertainty |
|---|---:|---|
| [GIL disabled](../benchmarks/results/pyperformance/repaired-source-abba-2026-10-19/gil-disabled/README.md) | −0.21% | `bench_mp_pool` +6.98% (halves +12.80%, +1.03%); `shortest_path` +3.15%. |
| [GIL enabled](../benchmarks/results/pyperformance/repaired-source-abba-2026-10-19/gil-enabled/README.md) | +0.33% | `subparsers` +15.29% and `dask` +13.86% have sharply unequal halves; `btree_gc_only` +12.70% increases in both halves (+17.25%, +8.16%); `connected_components` +6.48% also increases in both. |
| [FT disabled](../benchmarks/results/pyperformance/repaired-source-abba-2026-10-19/ft-disabled/README.md) | +0.23% | `dask` +4.55% and `html5lib` +2.21% increase in both halves; `k_core` +2.51% has opposing halves. |

All rows, leg variation, raw results, input fingerprints, pooled comparisons and arithmetic checks are retained. The summaries do not establish neutrality, causation or acceptance. Sequential disabled/enabled campaigns are not a controlled activation-cost estimate. [Protocol and remaining work](PYPERFORMANCE_CAMPAIGN_2026-10-19.md).

### 4.2 Historical serial/parallel measurements, 7–15 October 2026

PGO+LTO Python 3.16 on one 72-logical-CPU AArch64 host; parallel phases were
included in PGO training. GIL collector `669ed6b17e` (7 October); FT collector
`195830171f` after lazy startup (8 October). `c67363fa59` changes
release-build test guards only.

| Build | Mixed throughput | Eight 500,000-object shapes | Sustained |
|-------|------------------|-----------------------------|-----------|
| GIL | effectively unchanged; mean interval +3%, max +21% | 1.08× geomean; graph unstable and negative | throughput +7.6% geomean; AI mean interval +8% |
| FT | +23.5%; mean interval −26%, max −60% | all eight faster; 1.24× geomean (1.12× ai_workload … 1.51× layered) | throughput +7.0% geomean; **AI −9.9%, mean interval +116%, max 3.38 → 14.39 s**; chain mean interval +13% |

**FT pyperformance** (rigorous ABBA, 93 programs, 119 measurements): 24
significant improvements, one significant regression. `gc_traversal` 41.8%,
`create_gc_cycles` 22.7%, `btree_gc_only` 16.8% faster; **`float` 10.5%
slower**; `sqlite_synth` (+0.013%) and startup not significant. Seven programs
were excluded (four dependency incompatibilities, three `networkx` variants
lacking `_bz2`); not a complete default suite.

**GIL pyperformance:** the full sweep predates lazy startup. Focused rigorous
`sqlite_synth` after it: 1.421316 µs disabled, 1.429422 µs armed (0.57%, not
significant), one OS thread throughout. A new full sweep is pending.

**FT adaptive versus fixed** (three cycles, 20 collections per phase): adaptive
beats fixed 2 and 4 (by 2.6–56%) and is close to fixed 8, but **fixed 16 is
faster in all three phases** (by 6.8–38.6%). Adaptive arms start at four and do
not reach 16 within three cycles. This establishes neither convergence time nor
optimality.

**FT root-placement scaling** (release build, 15 October,
[review](reviews/2026-10-15-claude-scaling-review.md) §7): at 16 workers on a
live 1M-object random graph, parallel was 0.61–0.83× serial with the heap held
by a module global and 3.39× held by a frame local; `mark_alive` was 94–99% of
collection time. A binary tree was 1.22× for both holders; fine-grained lists
were 1.11× (global) and 0.62× (local); a linked chain 0.88–0.91×. The older project suite held its collection-shape heaps in function locals and therefore measured that placement. The current suite also includes module-rooted variants; do not apply the older placement limitation to the new comparison.

Reports:
[GIL and pre-lazy FT](../benchmarks/results/arm64-316-669ed6b-full-analysis-2026-10-08.md),
[FT lazy-pool analysis](../benchmarks/results/arm64-316-1958301-ft-lazy-analysis-2026-10-08.md),
[FT raw report](../benchmarks/results/arm64-316-1958301-ft-lazy-full-2026-10-08.md),
[PGO controls and earlier runtime ABBA](../benchmarks/results/pyperformance/pgo-runtime-abba-arm64-2026-10-07.md),
[GIL lazy SQLite ABBA](../benchmarks/results/pyperformance/investigations/gil-lazy-pool-sqlite-abba-2026-10-07/README.md).
September results
([GIL](../benchmarks/results/arm64-316-gil-adaptive-threshold-full-2026-09-30.md),
[FT full](../benchmarks/results/arm64-316-ft-92f-full-2026-09-30.md),
[FT standard](../benchmarks/results/arm64-316-ft-92f-standard-2026-09-30.md))
belong to earlier sources (`92f992042c`, and a dirty GIL tree) and must not be
attributed to current code.

## 5. Investigation record

| Date | Finding | Status |
|------|---------|--------|
| 2026-10-05 | `bench_mp_pool` (+27.6% GIL, +134.3% FT) came from benchmark activation: `sitecustomize` keyed on pyperf's `--worker` argument, which the multiprocessing forkserver inherited, so every forked child built a pool (52 vs 382 `clone()` calls per 10 pools). | Harness artefact, excluded. Activation moved into the pyperf hook; tests prove arguments and forkserver children cannot alter GC state. |
| 2026-10-05 | FT exact list, tuple and dict traversal: callback and generic `tp_traverse` dispatch dominated propagation (e.g. `propagate_pool_visitproc` 37.8% of samples). Direct traversal of exact containers, each with mutation-sensitivity tests and binary ABBA. | Retained: lists `06f1d674a4`, tuples `0205d62bcb` (1.59–1.64×), dicts `3459fbefd8` (1.14–1.29× by layout). Forced inlining of `_PyGC_TryMarkAlive` was falsified and reverted. |
| 2026-10-07 | Parallel-aware PGO training (`d396f837b9`): candidate/control geomean 0.993831 (GIL), 0.998143 (FT) with parallel GC disabled; no slowdown reproduced in both builds. | Retained. |
| 2026-10-07 | `sqlite_synth` (38.1% GIL, 10.4% FT slower) performed no collections. One unrelated thread reproduced it; glibc's `__libc_single_threaded` stays 0 after the first thread. | Cause: first-thread transition triggered by eager pool creation. Lazy startup (`7ec0874a7d`, `195830171f`) removed it (GIL 0.57%, FT 0.013%, both not significant). |
| 2026-10-08 | FT sustained `ai_workload` −9.9% and `float` −10.5%. | **Open.** On 15 October, per-collection latency was about 1.5–2× serial in both baseline and candidate builds, with only 3–8 adaptive workers. Serial runs were bimodal (about 40 collections at about 1.5 s, or about 25 at about 2.6 s). Candidate explanations: finalizers (the only shape with `__del__`); BRC queue traffic; cache-line ownership moving to helper cores; mimalloc abandonment versus cross-thread free. None tested. |
| 2026-10-15 | FT known-root propagation scaling depends on root placement and heap shape (§4). | **Open**; [OPEN_ISSUES.md](OPEN_ISSUES.md) §2. |
| 2026-10-15/16 | Creation-pool threads retained their last generated batch, adding unintended roots and compromising the intended garbage fraction. | Fix from `6c8bf14` integrated with controlled one-worker/four-worker and 80%-survivor tests. The historical retained fraction is unknown, not necessarily 100%. |
| 2026-10-15/16 | Four experimental propagation changes: helpers wait until all work is finished; busy workers publish to idle ones; large lists split into index ranges; release stores in the work queue. Project-suite ABBA with module-rooted variants: realistic module-cache workload +6.4% throughput and −13.4% mean latency; module-rooted collection shapes 12–26% faster; frame-rooted workloads mostly neutral. Sustained `ai_workload` mean latency +11.1%, flagged in three campaigns. | **Dropped.** The benefit is confined to module-rooted heaps, the list splitting is container-specific, and there is a regression. [Raw data and analysis](../benchmarks/results/investigations/root-placement-campaigns-2026-10-15/README.md). |

**Finalizer/BRC hypothesis (FT `ai_workload`).** Serial finalization and
deletion on the collecting thread decrement objects owned by other threads,
which cannot use the owner-local biased path and fall back to shared atomic or
queued processing. Test: hold topology, survivors, finalizer work and
candidates constant; build the finalizer graph on the collecting thread versus
other threads; count each BRC path during the serial tail. Rejected if the
cross-thread case does not show both more shared or queued BRC work and a
longer serial tail. Changing BRC is outside the proposal.

Raw evidence for each row is linked from
`PERFORMANCE_INVESTIGATION_PLAN.md` (removed; `git show 724b74b:docs/PERFORMANCE_INVESTIGATION_PLAN.md`)
and `FT_CONTAINER_TRAVERSAL_OPTIMIZATION_PLAN.md` (removed; `git show 724b74b:docs/FT_CONTAINER_TRAVERSAL_OPTIMIZATION_PLAN.md`).

## 6. Proposed acceptance rules from the review work

The review work used the following numerical rules. They are recorded for
discussion, not silently adopted as new authorisation or universal limits by
the documentation merge. Agree criteria with Alex before the next campaigns.
Micro-benchmarks (§2.4) locate problems but cannot satisfy these rules.

- **Correctness:**
  - the serial-equivalence verifier is clean;
  - ASan and TSan are clean on the focused selection;
  - fork tests pass;
  - no hang in 1,000 randomised collections at 2–16 workers, including empty
    and tiny heaps, each under a 10 s watchdog.
- **No harm (project suite, `--full --include-synthetic`, PGO+LTO, ABBA
  across builds):** for every workload, parallel-mode throughput and
  collection latency must not be worse than baseline by more than the larger
  of 3% and twice the same workload's serial-mode change. The serial mode is a
  control. Identical serial source need not produce identical PGO machine
  code, so movement in that control is evidence to examine, not an automatic
  correction for every parallel-mode difference.
- **Benefit:** collection latency at least 10% lower, or throughput at least
  5% higher. The improvement must exceed twice the serial-control change,
  and both ABBA halves must point the same way.
- **pyperformance ABBA:** no new statistically significant regression.
- **Comparisons:** use per-run means, not pooled samples. Pooled samples made
  identical serial code appear "significant".
- **Build comparison limits:** the quick PGO+LTO comparison of `c67363fa59`
  with the cleanup candidate differed by about 6% on some workloads and
  triggered several rule flags. Those observations do not establish a general
  noise floor or exclude regressions of a particular size. Use independent
  identical-source builds and an uncertainty analysis before claiming such a
  bound; report unresolved flags rather than assuming equivalence.

**Evidence required for a proposed design change:**

- a falsification test demonstrates a defect on current code;
- it passes the correctness requirements above;
- it shows a benefit on realistic workloads without breaking the no-harm
  rule.

Container-specific special cases need evidence from real applications that
the container shape matters. Evidence does not itself authorise a change to
atomics, barriers, phase structure, thresholds or adaptive policy; discuss
those changes with Alex first. The current integration keeps those unchanged.

## 7. Pending measurements

- Focused reproduction of negative integration measurements, then fresh-profile/generated-code investigation if the differences recur. Completed GIL/FT project ABBA is linked in §4.1; no cause or repair is assumed.
- The remaining four rigorous FT-enabled default pyperformance suites across baseline/current sources. All eight GIL suites and four FT-disabled suites are complete and recorded in §4.1; that does not establish neutrality or close the observed increases. Diagnostic runs and partial failed suites do not satisfy this requirement.
- Optimized feature-off controls for compile-time overhead.
- First-use pool startup latency, reported separately; pool memory use.
- Per-worker phase counters in FT `get_parallel_stats()` (today FT reports no
  per-worker list) to attribute the open regressions.
- Other hardware and core counts.
