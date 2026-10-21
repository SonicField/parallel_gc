# Parallel GC validation record

## What this record means

This is the single entry point for validation evidence, not a claim that the
latest branch tip is green. The parent repository's `cpython/` gitlink selects
the source. A branch name or an earlier successful run does not identify what
was tested in a later checkout.

From the parent repository, identify the checkout with:

```bash
git rev-parse HEAD
git ls-tree HEAD cpython
git -C cpython rev-parse HEAD
git -C cpython status --short
```

The gitlink and checked-out CPython commit must match. A dirty CPython worktree
is not evidence for that clean commit. Do not put the parent commit's own hash
inside this record: CI identifies its parent revision through the run's
`headSha` and checkout evidence.

Benchmark and local-test reports retain their measured revisions permanently.
Documentation-only commits do not change those measurements or the CPython
gitlink. Collector changes need new evidence; a claim that older results still
apply requires an explicit account of the intervening changes.

## Latest status: 21 October 2026

All sixteen repaired-dependency rigorous source-comparison suites are complete:
100 original programs and 127 named results per leg. [Campaign and checks](PYPERFORMANCE_CAMPAIGN_2026-10-19.md).
Individual increases, performance neutrality and causation remain unresolved.
The [four-block GIL follow-up](investigations/gil-build-effects/INVESTIGATION-STATUS.md)
did not reproduce the earlier large BTree/NetworkX increases using recovered
GIL binaries in a reconstructed shared runtime. Its selected same-host custody
checks do not recover the original complete runtime or establish all FT assets.

The five [19 October workflow successes](ci-results-2026-10-19.md) are reported
conclusions, not independently inspected source/job artifacts, counts or skips.
No new remote query was made. Dated pending statements below are checkpoints;
use this overview and [VP current state](../vp/STATE.md) for what remains now.

## CI repair follow-up: 19 October 2026

The new Linux matrix, compiler checks, full Linux CPython suite, Windows and macOS workflows are all reported successful in Alex's supplied listing. [Run IDs, original failures and evidence limits](ci-results-2026-10-19.md). Job-level source artifacts, skips and counts remain to be inspected; workflow conclusions must not be expanded into unsupported test-by-test claims.

Automatic runs `39248590193` and `39248590252` failed for two independently reproduced causes: the parent hook test chose runtime-disabled mode on feature-off builds, and Clang rejected an uncalled GIL wrapper. Parent `d448e16` repairs the probe and passes all 76 harness tests in all four feature-on/off GIL/FT configurations. CPython `b91445e0b9` removes only that wrapper; all 32 GCC/Clang GIL/FT debug/release GC-object compilations pass with the strict unused-code errors intact. Fresh GIL/FT debug builds pass the focused collector and parent harness selections. [Compiler/runtime evidence and limits](../benchmarks/results/investigations/ci-unused-wrapper-2026-10-19/README.md). Subsequent hosted workflow successes are reported above; source/job verification remains outstanding. The benchmark results below retain their original tested source identities.

## Dependency follow-up: 19 October 2026

The [dependency repair plan](../benchmarks/dependency-repair/PLAN.md) records six separately committed repairs in new isolated environments: Cloudpickle, Genshi, Coverage, Dulwich, MarkupSafe and Greenlet. All original benchmark programs and CPython sources remain unchanged. Native extensions are verified; FT runtime attestation is not bypassed. Coverage retains CTracer rather than accepting the newest release's different default engine.

The original Dask, Genshi XML/text, Coverage, Sphinx and Dulwich programs pass targeted short checks in all eight baseline/current GIL/FT enabled/disabled contexts. Cloudpickle and Genshi correctness tests also pass on all four target binaries and Python 3.12; native dependency probes pass on all four target binaries. These checks are not rigorous performance measurements or a complete repeated default suite.

Alex subsequently approved SQLAlchemy 1.4.19's [supported pure-Python build](../benchmarks/dependency-repair/SQLALCHEMY.md). [Repeated complete readiness](../benchmarks/dependency-repair/full-readiness-evidence/README.md) passes all 100 original programs in all eight contexts, with 127 named results each and no failures. FT remains GIL-disabled and all four fresh complete environments pass `pip check`. At this readiness checkpoint the sixteen rigorous comparisons were outstanding; they are now complete in the linked latest-status record. Diagnostic execution checks are not performance measurements. The historical failure captures below are preserved, not relabelled as repaired suites. Reported CI conclusions are available; detailed source/job evidence remains unverified.

## Integration checkpoint: 17 October 2026

The fixed comparison is baseline CPython `c67363fa59543ef5d572383af927f1cff88514a1` against integrated `388fd5bb46fdda6b464db566faf818505c3d6eef`. Both use the repaired parent benchmark, including ownership correction and module-rooted variants. The [integration validation log](../benchmarks/results/investigations/integration-validation-2026-10-16/INVESTIGATION-STATUS.md) records the protocol, failures, evidence and outstanding requirements. The gitlink above remains the checkout selector; these hashes identify the experiment, not an alternative live pin.

| Evidence | Observed outcome | Scope and limits |
|----------|------------------|------------------|
| [Four corrected optimized builds](../benchmarks/results/investigations/integration-validation-2026-10-16/build-evidence/README.md) | Fresh baseline/current GIL/FT GCC 11.5 AArch64 PGO+LTO builds pass native-decimal/runtime checks, verified parallel PGO training and selected collector/C-API/embedding/profile tests. | The overlapping selected-test counts are recorded per build; not full CPython suites or hosted platform evidence. `_tkinter` remains unavailable. |
| [Worker runtime attestation](../benchmarks/results/investigations/integration-validation-2026-10-16/hook-evidence/README.md) | All 75 parent harness tests pass on each binary; GIL skips one FT-only test, FT skips none. The hook rejects GIL fallback after FT workload imports. | Outside timed values; does not attest arbitrary workload-spawned children. Added parent tests need publication and a subsequent matrix run. |
| [Complete GIL project ABBA](../benchmarks/results/investigations/integration-validation-2026-10-16/GIL-PROJECT-RESULTS.md) | Four complete legs and analysis preserved; lower throughput in four of eight sustained cases, longer controlled collections in thirteen of sixteen. | Serial controls also move; some halves disagree. One PGO binary per source; neutrality and collector-specific causation are not established. |
| [Complete FT project ABBA](../benchmarks/results/investigations/integration-validation-2026-10-16/FT-PROJECT-RESULTS.md) | Four complete legs preserved; all eight module-rooted controlled collections are slower in both halves, +18.72% to +34.81%; module mixed throughput −7.41%. | Requires focused reproduction and diagnosis. Callback duration is not FT stopped-world duration. |
| [Unchanged full FT repeat](../benchmarks/results/investigations/integration-validation-2026-10-16/full-ft-repeat/RESULTS.md) | Four complete legs and 72-row analysis pass; broad module pattern does not reproduce, with every module controlled case showing opposing halves. Seven frame controlled cases increase in both halves; three sustained throughput means decrease. | Same source/binary pair and original full invocation; no code repair. Raw archives, independent arithmetic checks and replay pass. Attribution and neutrality remain unestablished; pyperformance and hosted CI remain separate requirements. |
| [Failed first default pyperformance suite](../benchmarks/results/investigations/integration-validation-2026-10-16/dependency-compatibility/README.md) | Dask/Cloudpickle opcode error and Genshi AST error; full log and partial JSON preserved. Both reproduce on all four binaries with collector disabled and no helpers. | Failed suite, not ABBA. Campaign stopped; no workload omitted or dependency repair made. |
| [Eight all-program compatibility checks](../benchmarks/results/investigations/integration-validation-2026-10-16/default-runtime-compatibility/README.md) | All 100 programs attempted for each baseline/current GIL/FT enabled/disabled combination. GIL fails two programs; FT fails those plus five whose native dependencies enable the GIL. Failure sets match within each mode. | Short diagnostic executions, not performance measurements. Runtime attestation rejects fallback; it was not bypassed. Full sixteen-suite comparison remains outstanding. |
| Current hosted CI | Publication and dispatch reported by Alex; current run IDs, source artifacts and job outcomes have not been captured. | Linux four-build/compilers/full suites, Windows and macOS remain unverified for this source pair. Older outcomes below are not substituted. |
| [Full local release tests](../benchmarks/results/investigations/integration-validation-2026-10-16/local-full-suite/README.md) | Current optimized GIL and FT full selections both failed pydoc/unittest again on rerun; the same four cases fail on baseline GIL/FT. Both complete logs and outcomes are preserved. | Source alias/physical path sensitivity reproduced. Parent-only `PYTHONPATH` fixes pydoc but not the `-E` unittest child. No test or source change; not a clean full-suite pass or hosted debug validation. |
| [First physical-source local debug follow-up](../benchmarks/results/investigations/integration-validation-2026-10-16/local-full-suite/physical-debug/README.md) | All four path-sensitive cases pass in both fresh builds. FT's full default suite passes, exit 0; the first GIL run returns exit 3, `ENV CHANGED`, for a multiprocessing module's temporary files, including rerun. | That GIL run is not green. Isolated baseline/current probes pass both pinned and unrestricted; cause remains unestablished. No source/test change or failure-check relaxation. Local runs do not replace hosted platform evidence. |
| [Matched full GIL debug comparison](../benchmarks/results/investigations/integration-validation-2026-10-16/local-full-suite/gil-full-comparison/README.md) | Baseline and current both pass, exit 0, using the same 509-file default selection and unchanged environment checks. Current reports 52,205 tests and 2,723 skips; baseline 52,202 and 2,715. | The earlier GIL leak did not recur, but remains unexplained. Combined with FT above, both current modes now have passing full local debug runs. Hosted evidence remains separate. |

Dependency compatibility changes require agreement before another full campaign. Preserve every workload, apply agreed changes equally to baseline/current environments, and retain FT runtime-mode checks. Current captures were requested at `/tmp/alex-ci-current.json`; that file remains absent at this checkpoint. No GitHub status is inferred from elapsed time.

## Recorded evidence: 15 October 2026

The source reviewed in the October handoff is CPython
`c67363fa59543ef5d572383af927f1cff88514a1`. This is a dated evidence baseline,
not a second mechanism for selecting the current source. Check the gitlink
above when using a later parent revision.

| Evidence | Source and outcome | Limits |
|----------|--------------------|--------|
| Local lifecycle and failure tests: historical record `git show 724b74b:docs/LAZY_POOL_CREATION_PLAN.md`; current contract in [DESIGN.md](DESIGN.md) §5–6 | Recorded GIL and FT debug, optimized lifecycle, ASan and TSan selections pass. | Exact selections and source revisions remain in the historical record. ASan leak detection was disabled; TSan options and suppressions are recorded. Not a full cross-platform validation. |
| [GIL performance](../benchmarks/results/arm64-316-669ed6b-full-analysis-2026-10-08.md) | Collector `669ed6b17e`, including throughput improvements and callback-interval regressions. | One AArch64 host; no full GIL pyperformance sweep after lazy startup. |
| [FT performance](../benchmarks/results/arm64-316-1958301-ft-lazy-analysis-2026-10-08.md) | Collector `195830171f`, including full project and pyperformance ABBA results. | One host; negative results and exclusions remain in the report. `c67363fa59` subsequently changes release-build test guards only. |
| [Earlier Linux full suite](https://github.com/SonicField/parallel_gc/actions/runs/37615265794) | Recorded success at `d396f837b9`. | Before the current lazy-pool work; not current-source evidence. |
| [Earlier Windows full suite](https://github.com/SonicField/parallel_gc/actions/runs/37615268403) | Recorded success at `d396f837b9`. | Same limitation. |
| [Earlier four-build matrix](https://github.com/SonicField/parallel_gc/actions/runs/37663869128) | Recorded success in all four jobs at the preceding published checkpoint. | The exact source pair has not been recovered into this record; the run predates the current local commits. |

These remote outcomes come from previously captured results. Live GitHub status
was unavailable during reconciliation; it has not been rechecked here.

## Local integration evidence: 16 October 2026

The integration is locally committed; no hosted result below is relabelled as
evidence for the newer source pair. The [integration plan and progress log](CLAUDE_INTEGRATION_PLAN.md)
record adopted candidates, separate destination commits and rejected collector
experiments. The parent's gitlink now selects CPython `388fd5bb46`; check it
with the commands above rather than treating this dated record as a live pin.

| Change and evidence | Tested source and result | Limits |
|---------------------|--------------------------|--------|
| [Unreferenced-code removal](../benchmarks/results/investigations/dead-code-cleanup-2026-10-16/README.md) | `442a97213f`: four fresh feature-on before/after builds and two feature-off debug controls pass; defined global GC symbols unchanged; unused-function/variable gates pass after cleanup. | GCC 11.5 on ARM64; no PGO/LTO; optional-module exclusions. Not an all-warning or performance claim. |
| [Production marking verifier](../benchmarks/results/investigations/production-verifier-integration-2026-10-16/README.md) | `0fc7b3ccb9`: four clean feature-on configurations and two clean feature-off debug controls pass; GIL/FT ASan and TSan selections pass without diagnostics; root/edge mutation sensitivity retained. | Opt-in debug serial replay; ctypes unavailable; TSan selections are bounded; ASan leaks disabled. An initial undetailed scratch failure remains unexplained and is not hidden by later passes. |
| [Benchmark ownership and module rooting](../benchmarks/results/investigations/module-rooting-integration-2026-10-16/README.md) | Parent harness follow-up `5a900b1`, fresh `0fc7b3ccb9` binaries: 24 tests × 20 suites × four configurations = 1,920 tests, no failures/errors. Host suite and planted persistent-reference faults checked. | Test scaffolding, not performance measurements. Sustained workers allow temporary mutation references; controlled collection has a module-only boundary. Cross-thread frame inspection was removed from test instrumentation. |
| [Header dependency repair](../benchmarks/results/investigations/header-dependencies-2026-10-16/README.md) | `388fd5bb46`: five missing prerequisites added; before/after dry-run controls, actual object rebuilds, links and focused tests pass in four feature-on configurations and two feature-off debug controls. | Incremental rebuilds from complete clean verifier builds; no sanitizer rerun for this five-line build-only change. Existing signedness/unused-label warnings remain recorded. |
| Focused compiler workflow | Parent `83e865f`: eight GCC/Clang GIL/FT release/debug object-check jobs added; YAML, shell and source-record fixture checks pass locally. | Clang unavailable locally; hosted workflow has not run for this integration. |

Exact commands, counts/skips, failure records and source/binary provenance are
in the linked reports. The complete clean builds used a detached scratch
worktree whose tracked content matched the stated commits but whose version
stamp still named a dirty baseline. Reused user builds are not represented as
clean-source evidence. These local tests are not full CPython regression
suites, Windows/macOS validation or new performance results.

The subsequent optimized builds and project comparisons are recorded in the 17 October checkpoint above. Publication and hosted dispatch were reported, but current source artifacts and outcomes remain unavailable. The rigorous pyperformance comparisons await agreed dependency work. Older results from a retaining harness cannot isolate a collector change.

## Historical remote coverage and older captured runs

The dated run IDs below precede the integrated CPython source. This is the older checkpoint; newer workflow conclusions are recorded in the 19 October follow-up above, with source/job artifact limits. Required coverage also includes the eight GCC/Clang GIL/FT release/debug object checks added to the Linux matrix. Do not read an older success as current validation.

The first published-run outcomes below were reported on 16 October 2026.
The macOS logs verify parent `724b74b749d942ace6ea05ec3bdab4bd504781d9` and
CPython `c67363fa59543ef5d572383af927f1cff88514a1` in all four jobs. The other
workflow conclusions come from Alex's captured listing; their source artifacts,
job outcomes, skips and rerun details still need examination.

| Platform and workflow | Required coverage | Recorded status |
|-----------------------|-------------------|-----------------|
| Linux, `parallel-gc.yml` | GIL and FT, feature-on and feature-off; focused collector and parent harness tests. | [38730251690](https://github.com/SonicField/parallel_gc/actions/runs/38730251690): success reported; detailed evidence pending. |
| Linux, `full-cpython-tests.yml` | GIL and FT feature-on builds; full default CPython suite. | [38730312362](https://github.com/SonicField/parallel_gc/actions/runs/38730312362): success reported; detailed evidence pending. |
| Windows, `windows-parallel-gc.yml` | GIL and FT feature-on builds; focused collector and parent harness tests, then full default CPython suite. | [38730315605](https://github.com/SonicField/parallel_gc/actions/runs/38730315605): success reported; detailed evidence pending. |
| macOS, `macos-parallel-gc.yml` | GIL and FT builds; focused collector and parent harness tests, feature-off controls, and full default CPython suite in feature-on builds. | [38730319127](https://github.com/SonicField/parallel_gc/actions/runs/38730319127): all four built successfully, then failed at configuration verification before tests. Rerun [38880079592](https://github.com/SonicField/parallel_gc/actions/runs/38880079592): feature-off GIL/FT successes reported; feature-on jobs were running in Alex's last captured listing. Final outcomes and source artifacts unconfirmed. |

The macOS run used ARM64 runners. Each build imported all 116 configured
modules without a missing or failed import, then the workflow attempted
`build-macos/python` and failed with `is a directory` (exit 126). On the runner's
case-insensitive filesystem that path resolves to the build's `Python/`
directory; the executable generated and used during the build is `python.exe`.
All six workflow invocations now use `build-macos/python.exe`. This is a
workflow correction, not a collector change. The next run must pass that
verification step and execute the tests before macOS correctness can be assessed.

The rerun statuses above are captured reports, not a live query. The feature-off
passes do not establish that either active collector passed its tests.

Full default-suite runs begin with parallel policy disabled. Focused tests
explicitly exercise activation and parallel dispatch. Report skipped tests,
rerun failures and dependency exclusions, not just the workflow conclusion.
Linux hosted CI and local AArch64 evidence are different platform records;
record the actual runner architecture rather than inferring it from the OS.

## Recording a run

Each result must identify:

- run URL, attempt number and actual parent `headSha`;
- the parent's recorded CPython gitlink and the checked-out CPython revision;
- OS, architecture, GIL/FT mode, feature-on/off setting and build flags;
- test commands, outcomes, skips, reruns and retained log/artifact links.

Record job-level outcomes even when a workflow has mixed results. Keep failed
attempts when adding a successful repair run. A pass on an older source pair
does not validate a newer pair. Do not call the publication checkpoint
validated until all required jobs for that pair have recorded passes and
remaining coverage limits are stated.

Each workflow now verifies the parent revision and CPython gitlink/checkout
before building and retains `ci-source.txt` as a per-job artifact. It records
requested flags; the subsequent runtime configuration check verifies the build.
Local fixture checks pass, and the captured macOS logs verify hosted source-pair
capture. Source artifacts for the other platform runs still need examination.
[TESTING.md](TESTING.md) gives dispatch
and log commands; the [handoff log](HANDOFF_RECONCILIATION_PLAN.md) tracks
publication work. Updating this evidence record does not require rewriting
the architectural narrative or changing hashes in historical reports.
