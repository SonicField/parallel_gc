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

### 2.2 Project suite: `gc_perf_benchmark.py`

```bash
build-benchmark-ft/python benchmarks/gc_perf_benchmark.py --quick   # sanity only
build-benchmark-ft/python benchmarks/gc_perf_benchmark.py           # mixed workload
build-benchmark-ft/python benchmarks/gc_perf_benchmark.py --full --include-synthetic
```

Options: `--quick` (2 runs, 10 s), `--full` (5 runs, 60 s; synthetic tests
still need `--include-synthetic`), `--duration`, `--runs` (3), `--threads` (4),
`--heap-size` (500,000), `--json`, `--output`. Allow 45–70 minutes per build
for `--full --include-synthetic` on the AArch64 host.

- **Mixed workload:** application threads choose randomly among deltablue,
  deepcopy, pickle_copy, async_tree (high cycles), richards, nbody (minimal)
  and comprehensions (none); one combined result.
- **Collection shapes (8):** chain, tree, wide_tree, graph, layered,
  independent, ai_workload (finalizers), web_server. Each timed collection
  keeps 80% of clusters live (`COLLECTION_SURVIVOR_RATIO`), held in a function
  local.
- **Module-rooted candidate variants** (not yet integrated into this checkout;
  the recorded experiments used benchmark candidate `306644b`): the same
  collection shapes and sustained heaps with live data reachable only from
  module state, plus the mixed workload with a static 500,000-object
  module-rooted cache. In FT, thread stacks are scanned as roots directly,
  while module state is reached through `sys.modules`. The two placements
  exercise known-root propagation differently (OPEN_ISSUES.md §2). Results
  appear under separate JSON keys. With these variants, `--full
  --include-synthetic` took about 95 minutes per invocation in those campaigns.
- **Creation-pool fix:** before benchmark commit `6c8bf14`, creation-pool
  threads kept their last generated clusters as frame locals. The "dropped"
  fraction could therefore remain reachable, with extra stack roots affecting
  propagation. A worker can process several tasks and retains only its last
  result, so the fraction retained depends on scheduling. **Historical
  collection-shape runs did not establish the intended 20% garbage fraction;
  their actual retained fraction is unknown.** The repair is scheduled in the
  [integration plan](CLAUDE_INTEGRATION_PLAN.md). Mixed and sustained workloads
  do not use this creation pool.
- **Metrics:** throughput; callback-to-callback collection interval (mean and
  maximum); GC callback-active time (not additive in FT); parallel/serial
  speedup; geometric means.

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
- A `gc.callbacks` interval covers the whole collection call. In FT it includes
  work outside the stopped-world sections and is not a pause measurement.
  Collection time, callback interval and throughput are not interchangeable.
- Do not compare across machines without recording the hardware.

## 4. Current evidence

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
were 1.11× (global) and 0.62× (local); a linked chain 0.88–0.91×. The project
suite above holds its heaps in function locals and therefore measures the
favourable case.

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
| 2026-10-15 | Creation-pool threads retained their last generated batch, adding unintended roots and compromising the intended garbage fraction. | Candidate fix `6c8bf14`, with a regression test; integration pending. The historical retained fraction is unknown, not necessarily 100%. |
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

- Clean published-revision repeats of both optimized campaigns, plus
  optimized feature-off controls for compile-time overhead.
- A full GIL pyperformance sweep after lazy startup.
- First-use pool startup latency, reported separately; pool memory use.
- Per-worker phase counters in FT `get_parallel_stats()` (today FT reports no
  per-worker list) to attribute the open regressions.
- Other hardware and core counts.
