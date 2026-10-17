# Investigation: integrated-source CI and performance

**Status:** Four corrected optimized builds and supplementary local tests passed. Both current modes also have passing full physical-source debug runs; an earlier GIL environment leak remains unexplained. All eight original project legs and both source analyses are complete. A focused FT collection ABBA does not reproduce the broad slowdown; an unchanged full FT repeat is now running. The first corrected default pyperformance suite failed Dask and Genshi. Eight all-program diagnostic checks show two failing programs in GIL and seven in FT, matching baseline/current and enabled/disabled. Pyperformance is stopped and evidence preserved. Dependency changes await agreement; hosted CI run IDs remain pending.
**Hypothesis:** The integration preserves collection behaviour and has not introduced a reproducible throughput or collection-latency regression.
**Falsification criterion:** A new functional failure, or a reproducible per-workload throughput decrease/latency increase in the matched-source comparisons.
**Decision informed:** What must be investigated before handing this checkpoint to core developers. This is not a release acceptance verdict.

Alex authorised CI and benchmarking after agreeing to retain the opt-in debug verifier for handoff. Measurements use release builds, where that verifier is absent. No active collector redesign or automatic repair of a flagged regression is authorised.

## Fixed comparison

- Baseline CPython: `c67363fa59543ef5d572383af927f1cff88514a1`.
- Integrated CPython: `388fd5bb46fdda6b464db566faf818505c3d6eef`.
- Both use the current repaired parent harness, including creation-pool reference release and the module-rooted variants. Do not compare against the old retaining harness.
- Four fresh out-of-tree GCC builds: baseline/current × GIL/FT, each `--with-parallel-gc --enable-optimizations --with-lto`; FT also `--disable-gil`.
- Check normal optional benchmark dependencies, actual PGO-use/LTO compiler commands, the parallel-GC training task, binary hashes, clean source trees and focused tests before measurement.
- Measurements are sequential, after all builds finish, with CPU affinity `0-31` and NUMA CPU/memory node 0 on this single-node AArch64 host.

## Measurement protocol

1. Project suite: baseline, current, current, baseline for GIL, then the same for FT. Every invocation uses unchanged `--full --include-synthetic --json`: five runs, 60-second sustained phases, four application threads and 500,000-object heaps. Serial and parallel results are produced within each invocation.
2. Rigorous pyperformance binary ABBA for both modes, separately with parallel GC enabled and disabled. Use the full default selection; do not silently exclude failing benchmarks. Preserve failures as well as completed campaigns.
3. Record every raw leg, per-workload means, both ABBA halves, build/driver provenance, source/harness hashes and skips/failures. Report program throughput, collection time and callback start-to-stop duration distinctly. Do not call an FT callback duration a stopped-world pause.
4. The expected null baseline/current throughput and latency ratios are 1. No universal noise floor or new percentage acceptance threshold is adopted. Report changes and uncertainty; repeat unresolved differences before attributing them. Release acceptance criteria remain a separate decision.

The project suite alone is estimated at about thirteen hours for eight invocations, based on historical 95-minute runs. Four PGO+LTO builds and sixteen rigorous pyperformance suites add substantial time; the whole sequence may take multiple days. These are estimates, not new measured durations.

## CI publication

Alex pushes CPython first, then the parent gitlink. Parent pushes trigger the Linux matrix and compiler checks. Manually dispatch Linux full CPython, Windows and macOS workflows. Record each run's exact source pair and job-level outcomes; older green runs do not validate this checkpoint. No assistant remote writes.

## Experiment log

16 October: both tracked repositories were clean. Created isolated clean detached source worktrees and build/dependency/driver directories under `/tmp/parallel-gc-benchmarks-20261016-6gpt8U`. The earlier temporary dependency prefix and pyperformance driver had disappeared. Public-mirror access was denied. Restored development headers/runtime libraries from the host's configured package repositories into the owned prefix, without installing system packages; recreated a private driver using the pinned project requirements. The first configuration finds zlib, ctypes, SQLite, bz2, lzma and SSL. Tk remains outside the benchmark dependency checks.

Builds run sequentially through the retained `builds.sh` in the scratch directory. The measurement launcher `run_campaign.sh` waits for that build process and refuses to measure unless all four builds pass its provenance checks. No benchmark parameter or implementation was changed. Measurements have not started at this record's creation.

Launcher preflight: `bash -n run_campaign.sh` passes. Supplying a completed/nonexistent build PID while the four-build record is incomplete exits 1 and creates no results directory; the actual launcher remains waiting for the live build process. The private Python 3.12 driver imports pyperf 2.10.0, pyperformance 1.14.0 and the `parallel_gc` hook. Its 27 `benchmarks.test_pyperformance_support` tests pass, including ABBA ordering, explicit source-tree provenance, differing-benchmark rejection and activation scope. These are machinery checks, not benchmark results.

### Native decimal preparation correction

All four initial PGO+LTO builds completed and passed their original gates. One GIL baseline project invocation completed; the current GIL invocation was running when review of the build log found two missing modules: `_decimal` and `_tkinter`. The original gate checked other native dependencies but omitted `_decimal`. Configure explicitly selected the pure-Python decimal fallback because the external `libmpdec` header/library was absent. This was a preparation error, not evidence of a collector regression.

The original measurement launcher was terminated before any pyperformance run. Its current Python benchmark process continues unchanged to completion; old binaries, libraries and raw results are preserved. This incomplete ABBA attempt is not a completed comparison and will not be mixed with the replacement build set. The source worktrees remain clean at the stated commits; no build was borrowed from another project.

Obtained `mpdecimal` and `mpdecimal-devel` 2.5.1-3.el9 from the host's configured package repositories. A new owned dependency/build root is `/tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW`. Its build script waits for the current measurement process to finish, then creates a separate prefix and four fresh builds. The new gate explicitly imports `_decimal`, checks `decimal.Decimal is _decimal.Decimal`, verifies compiled and runtime GIL/FT mode after dependency imports, and records the native module path/library version. Decimal tests join the focused suite. Direct native-decimal checks fail on all four initial binaries, as expected. No system package installation, collector change or benchmark-parameter change.

The corrected four-build check must pass before restarting full project and pyperformance ABBA in a new results directory. Tk is not part of the selected benchmark workloads; its absence remains an explicit build limitation rather than an all-optional-modules claim.

The campaign launcher now independently repeats the native-dependency/build-mode check immediately before measurements and fingerprints that check alongside the unchanged benchmark harness. Replacement builds and a new campaign are queued sequentially; neither starts competing CPU work while the old measurement process remains alive. Native-decimal build success and replacement benchmark results are still pending.

At 17:09 UTC, the old current-GIL process finished and saved `results/project/gil-2-candidate.json` under the original scratch root. Its SHA-256 is `0aba72e8a309e27b67161b0d1078ca7c283be30a8efaec27734d906d6a5ce13a`. This completes only two legs of the abandoned attempt, not ABBA, and does not make those builds suitable for the planned pyperformance comparison.

The corrected baseline-GIL build then started automatically, without overlapping the old measurement. Configure's pkg-config lookup for `libmpdec` failed, but its direct header and link checks passed: `mpdecimal.h` and `mpd_version` in `-lmpdec` were found. The generated Makefile records `MODULE__DECIMAL_STATE=yes`; compilation began with `-fprofile-generate` and `-flto`. This proves configuration and build start, not a successful finished build or runtime import. The native-decimal identity check, profile-use build, tests and binary hash remain required before measurement.

### Corrected GIL builds and supplementary tests

Both GIL builds finished their profile-use/LTO compilation and passed the native-decimal/runtime-mode checks, parallel profile workload and six-file build test selection. Baseline ran 948 tests with 85 skips; candidate ran 951 with 88 skips. Native decimal reports libmpdec 2.5.1. These are build checks, not the full CPython suite.

Supplementary local checks use the Linux matrix's collector, configuration, embedding and miscellaneous C-API selection, plus the profile task tests. Both GIL builds passed: baseline ran 682 tests with 91 skips; candidate ran 685 with 94 skips. Each requested eleven files; the FT-only API and property files skipped at file level, leaving nine passed files. These skips do not provide FT evidence. Each build also passed all 67 tests across the four parent benchmark-harness modules. Executable SHA-256 checks still match the post-build records.

The first parent-test attempt on the bare baseline executable failed to import `pyperf`; its failure log remains preserved. Attempting installation using the private Python 3.12 driver's pip 25.0.1 against Python 3.16 then failed inside its vendored `typing_extensions`, which accesses the removed `typing.no_type_check_decorator`. Using each test virtual environment's own bundled pip 26.2.1 succeeded. The environments install pure-Python pyperf 2.10.0 without dependencies for these unit tests; they are separate from the future pyperformance measurement environments. No source, benchmark parameter or runtime collector change.

Stopped the still-waiting original campaign controller before it created results. Its replacement, `finish_tests_and_run.sh`, waits for all four successful build checks, verifies the completed GIL supplementary logs, runs the matching FT collector and parent checks in isolated test environments, and only then invokes the unchanged measurement launcher. A supplementary failure exits before any benchmark starts. Syntax checking passes; supplying a nonexistent build PID while the four-build marker is absent exits nonzero and creates no results directory. The real replacement controller is live and waiting for the FT builds. This prevents supplementary testing from overlapping measurements.

### Four-build gate completed; corrected measurements started

At 17:51 UTC all four optimized builds had passed the build gate. Both FT builds also passed the supplementary eleven-file collector/configuration/embedding selection, including `test_free_threading.test_gc`, and the four parent harness test modules. No supplementary test process remained when measurements began at 17:51:41 UTC. Native decimal was independently checked again in all four binaries; their executable hashes matched the post-build records.

| Build | Six-file build check: tests / skips | Supplementary collector check: tests / skips | Parent harness tests |
|-------|------------------------------------|---------------------------------------------|----------------------|
| Baseline GIL | 948 / 85 | 682 / 91 | 67 passed |
| Candidate GIL | 951 / 88 | 685 / 94 | 67 passed |
| Baseline FT | 948 / 73 | 712 / 79 | 67 passed |
| Candidate FT | 951 / 76 | 715 / 82 | 67 passed |

The selections overlap; these counts must not be summed as unique tests. The GIL supplementary run skips two FT-only files; FT runs all eleven requested files. FT logs retain an `ImportError` emitted by `test_module_state_shared_in_global`: the existing C-API fixture is explicitly marked as an expected failure without the GIL because shared extension-module state is unsupported (upstream issue gh-117649). Both complete test runs report success. This is not a newly discovered parallel-GC crash.

The [build-evidence directory](build-evidence/) preserves the four native-dependency preflights, selected test logs, executable hashes, post-build parallel profile checks and actual profile-use/LTO compiler-command excerpts. Full build logs remain at the scratch root, with their hashes in the excerpts. These prove the stated local build/test scope, not full CPython or hosted-platform completion.

The corrected campaign records parent checkpoint `5440ac284672a631ffcdb5ef6a32544967fd2c45` and the fixed CPython source pair. Its first process is the baseline GIL `--full --include-synthetic` invocation, writing only to the new scratch root's `results/project/gil-1-baseline.json`. No corrected leg was complete when this entry was written. All eight project legs and sixteen pyperformance suites remain required; no performance result or readiness verdict is inferred from passing local tests.

### Analysis machinery prepared during measurement

Added a separate [complete-project-ABBA analysis tool](ANALYSIS.md), without editing either benchmark implementation or its parameters. Twenty-three artificial-data tests pass. They cover source order, GIL/FT configuration, affinity/NUMA consistency, clean CPython content, complete workload coverage, run counts, finite measurements, matched actual object counts, equal leg weighting, run-level rather than collection-weighted callback means, signed changes, undefined zero-denominator ratios and input-file hashes. The command also refuses the actual unfinished campaign with no report. These establish analysis machinery behaviour, not performance neutrality.

Reports retain every run-level sample, descriptive variation, both ABBA halves, serial controls and within-build parallel/serial changes. No percentage-based acceptance rule, significance assertion or noise threshold is adopted. Only the complete corrected campaigns can provide the requested performance evidence. Subsequent parent commits add documentation and analysis machinery; the running benchmark implementation and preflight fingerprints remain unchanged and are checked after each measurement leg.

### Corrected project leg 1 completed

The baseline GIL leg ran from 17:51:41 to 19:13:04 UTC (81 minutes 23 seconds). The launcher parsed its completed JSON, verified all three benchmark/preflight fingerprints, and started candidate GIL leg 2 automatically. The completed document records the clean baseline source, GIL build mode, the unchanged standard parameters and affinity, eight sustained comparisons and sixteen controlled comparisons. All measured arms contain five samples; controlled serial/parallel object-count sequences match within the leg.

Preserved its complete data in [project-legs](project-legs/), including the original scratch-file hash and Git-copy hash. The Git copy adds only a terminal newline; a byte comparison of its original-length prefix matches the scratch file. This is one completed leg, not a complete ABBA comparison. No baseline/current performance conclusion is made, and this corrected data is not mixed with the earlier incomplete-build attempt.

### Corrected project leg 2 completed

Candidate GIL leg 2 ran from 19:13:04 to 20:34:28 UTC (81 minutes 24 seconds). Its complete JSON records clean candidate source `388fd5bb46fdda6b464db566faf818505c3d6eef` and parent checkpoint `cc2a489e937458f2271064fc88e81f8adf1ee517`. The source differs as planned; configuration, CPU affinity and NUMA policy match baseline leg 1. All eight sustained and sixteen controlled comparisons contain five finite, nonnegative samples per arm. Actual controlled object-count sequences match both arms of baseline leg 1.

Preserved leg 2's complete data and original/Git-copy hashes alongside leg 1. The launcher again verified the three unchanged measurement/preflight fingerprints and started candidate leg 3. Two legs provide only the first ABBA half; no source-effect, significance or acceptance verdict is made before the closing two legs and planned controls are available. Hosted CI evidence remains unavailable; the non-blocking capture request is outstanding.

### Corrected project leg 3 completed

The second candidate GIL leg ran from 20:34:28 to 21:55:51 UTC (81 minutes 23 seconds). It records clean candidate source and parent checkpoint `bf5e87076deb8c415ddc5425587aa7a5456c64cf`. Its configuration and placement match leg 1; all eight sustained and sixteen controlled comparisons contain five valid samples per arm, and actual controlled object-count sequences match baseline leg 1. Complete data and both file hashes are preserved alongside the first two legs.

The launcher verified the same three measurement/preflight fingerprints and started closing baseline leg 4. Three completed legs do not supply the closing ABBA half. The analysis tool must continue refusing a full comparison until leg 4 is complete; the FT and pyperformance campaigns still follow. Hosted CI results remain unverified.

### Complete corrected GIL project ABBA

Closing baseline leg 4 ran from 21:55:51 to 23:17:25 UTC (81 minutes 34 seconds). It records clean baseline source and parent checkpoint `da42aa1891d765fe8eef413095bc6f9caa9d805e`. The complete four-leg source-order, configuration, placement, coverage, sample and controlled-count checks pass. All four data files, original/Git-copy hashes, a reproducible 72-row machine analysis and the [full GIL results](GIL-PROJECT-RESULTS.md) are preserved.

This measurement records four of eight lower sustained throughputs, six of eight increased mean callback durations and thirteen of sixteen longer controlled collection times in candidate parallel mode. Several serial controls change similarly; some halves disagree. Performance neutrality and a collector-specific cause are not established. The report retains negative and positive figures, absolute means, both halves, serial controls, frequency/time fractions and descriptive variation. No universal percentage threshold or significance claim is substituted for that evidence.

The launcher rechecked the three measurement/preflight fingerprints and started FT baseline leg 1. No FT project leg or pyperformance campaign is complete at this entry. Hosted CI evidence is still missing. The complete GIL comparison does not finish the handoff objective.

### Runtime-mode attestation before pyperformance

While FT baseline leg 1 remained live, found that the pyperformance hook checked collector activation but not the runtime GIL state after workload imports. Added a teardown-only check and metadata, without forcing a GIL setting or changing timed workloads. Six decision tests failed before implementation; eight added tests now cover decisions and real child-process behaviour. All 75 parent harness tests pass on each of the four binaries (one FT-only skip in GIL). They ran on CPU 32 outside the measurement affinity.

The [hook evidence](hook-evidence/README.md) records commands, passing logs, the initial misspelled-module invocation, exact scope and fingerprint boundary. The hook was frozen before any pyperformance campaign began; it is included in subsequent controller checks. Completed GIL project data and the running FT project invocation do not use this hook. Published parent CI does not cover the new parent tests; another matrix run will be required after publication. No CPython source or collector behaviour changed.

### Corrected FT project leg 1 completed

FT baseline leg 1 ran from 23:17:25 UTC on 16 October to 00:51:50 UTC on 17 October (94 minutes 25 seconds). Its complete data and original/Git-copy hashes are preserved in [project-legs](project-legs/README.md). All eight sustained and sixteen controlled comparisons have five valid samples per arm; standard configuration, clean CPython source, compiled FT flags, placement and within-leg generated-member count checks pass. The recorded parent is dirty during preparation of the preceding GIL evidence; preserve that observation rather than claiming a clean parent checkpoint. The measured project implementation and its original fingerprints remained unchanged.

The controller passed its four current fingerprint checks and started candidate FT leg 2. The analysis command still refuses a source comparison because that leg's JSON is absent. Inspection found that the separate analysis tool's FT fixture uses `ft`, whereas the actual harness emits `free-threaded`. This is an analysis-schema defect to fix test-first, not a benchmark or collector defect; no measurement metadata will be rewritten. Three FT legs and all pyperformance campaigns still remain.

### FT analysis-schema correction

Corrected the analysis tool's expected build metadata to `free-threaded` for launcher mode `ft`, matching the actual first FT document and the unchanged project harness. Before implementation, the corrected FT fixture failed with `wrong build mode`, while a new test showed that the invalid literal `ft` was accepted as harness metadata. After the analysis-only correction all 24 machinery tests pass. Replaying the complete GIL analysis produces a byte-identical report, including all measurements and input hashes. The actual unfinished FT command continues refusing a full comparison because its closing documents are absent. No benchmark, result metadata or collector was modified to accommodate the analyser.

### Corrected FT project leg 2 completed

Candidate FT leg 2 ran from 00:51:50 to 02:27:00 UTC on 17 October (95 minutes 10 seconds). Complete data and original/Git-copy hashes are preserved alongside baseline leg 1. Its source is the clean integrated CPython checkpoint. All eight sustained and sixteen controlled comparisons have five finite, nonnegative samples per arm; standard configuration and placement match baseline, and each controlled generated-member count sequence matches baseline's serial and parallel arms. Recorded parent checkpoint `68e32f522427bf34ab19990c8482e3038d3a5018` is dirty during preceding evidence work; that observation is preserved. The project implementation and four current controller fingerprints remained unchanged.

The controller verified those fingerprints and started candidate leg 3. The analysis command still refuses a source-effect report because that JSON is absent. Two closing FT legs remain; the first source pair is not a full ABBA. No pyperformance campaign has started, and current hosted CI remains unverified.

### Corrected FT project leg 3 completed

Second candidate FT leg 3 ran from 02:27:00 to 04:03:07 UTC on 17 October (96 minutes 7 seconds). Its complete data and original/Git-copy hashes are preserved. All eight sustained and sixteen controlled comparisons contain five valid samples per arm; standard configuration, placement and controlled generated-member count sequences match baseline leg 1. Clean candidate CPython source is recorded. Parent checkpoint `67658cbe7993ad168e98bc6532bf17cb8625a13f` is dirty during preceding evidence work; this observation is retained while the unchanged project implementation and four controller fingerprints provide the measurement-code boundary.

All four fingerprint checks passed and closing baseline FT leg 4 started. The analysis command still refuses a complete comparison because its result is absent. The closing leg, pyperformance campaigns, hosted-CI evidence and final handoff reconciliation remain required. No throughput or latency source-effect conclusion is inferred from three legs.

### Complete corrected FT project ABBA

Closing FT baseline leg 4 ran from 04:03:07 to 05:37:40 UTC on 17 October (94 minutes 33 seconds). All four FT legs, original/Git-copy hashes and the reproducible 72-row machine analysis are preserved. Source-order, build-mode, configuration, placement, complete-workload, five-sample and generated-member count checks pass. The [full FT results](FT-PROJECT-RESULTS.md) record five of eight lower sustained throughputs and ten of sixteen longer controlled collections. Seven mean callback changes are positive; frame mixed is +0.0023%, while the other six increases range from +1.57% to +14.36%. No significance or acceptance threshold is assigned.

The strongest negative pattern is module-rooted controlled collection: all eight shapes are slower in both halves, with overall increases of +18.72% to +34.81%, not generally mirrored by serial controls. Module-cache mixed throughput decreases −7.41% in both halves while its serial control increases +0.54%. These observations require focused follow-up; no collector-specific cause or automatic repair is asserted. All samples, variation, both halves, serial controls, collection counts and callback-time fractions are preserved. Neither source comparison establishes performance neutrality.

### Pyperformance preparation failure

The controller verified all four fingerprints and started GIL enabled rigorous binary ABBA at 05:37:40 UTC. Its baseline environment preparation failed before the first suite. The default selection includes `fastapi==0.121.0`; its allowed dependency resolution selected `pydantic==2.14.1` and `pydantic-core==2.50.1`. No Python 3.16 AArch64 wheel was selected, so pip attempted a source build. Maturin's bootstrap reported Rust absent and tried downloading `rustup-init` from `static.rust-lang.org`; its HTTP client failed with network unreachable. The complete failure remains in scratch `results/pyperformance/gil-enabled.log`. This is a dependency/toolchain preparation failure, not a measured collector regression or completed pyperformance suite.

As designed, the controller records the failed status and continues the remaining enabled/disabled GIL/FT attempts rather than silently excluding that workload. Inspect available toolchains before choosing a repair; do not narrow the promised default suite or claim completion from a partially prepared environment. Current hosted CI capture remains absent.

### Isolated Rust toolchain preparation

The configured package repositories provide Rust and Cargo 1.97.1. Downloaded their matching compiler, Cargo and static standard-library packages into an owned temporary prefix; all RPM digest/signature checks pass. A relocated compiler wrapper fixes its own driver-library lookup without changing Python's loader environment. A simple Rust program compiled on CPU 32 and ran successfully. No system toolchain installation or collector/benchmark change. [Toolchain preparation](TOOLCHAIN-PREPARATION.md) preserves exact versions, package hashes, failed cache-only attempt, successful download and the remaining native-package verification requirement. The original controller still runs; its later partially prepared environment is not a readiness proof. Full dependency preparation and fresh pyperformance campaigns remain required.

### Known-incomplete pyperformance attempt stopped; native failure repaired

The GIL disabled invocation reused the partial environment, marked FastAPI skipped after failed requirements, then began timing other programs. The pinned pyperformance implementation records that missing program as an error and ultimately exits failing. At 05:43:54 UTC stopped the verified dedicated campaign process group and confirmed every member gone. This avoids spending full-run time on coverage already known incomplete. No files were removed. The full initial failure and interrupted logs, their hashes and newline-copy distinction are preserved in [preparation evidence](pyperformance-preparation-evidence/README.md); partial timings are excluded, not reported as a source ABBA. FT pyperformance had not started.

With the isolated Rust toolchain, exact `pydantic-core==2.50.1` wheels now build for GIL and FT, without compatibility forcing or version changes. Native imports and actual FastAPI requests succeed on all four real target binaries in separate environments; both FT runtimes retain GIL-disabled state. Native build logs, the untimed probe and four results are preserved. This repairs the observed preparation failure, not all default dependency or benchmark compatibility. Fresh full preparation and all sixteen rigorous suites still remain; no benchmark implementation or collector behaviour was changed.

### Fresh complete pyperformance preparation

All four fresh default environments prepared successfully under `/tmp/parallel-gc-pyperformance-prepared-20261017-dBFKZD`, using the same four optimized binaries and exact 100-program default selection. The native request probe passes on each actual measurement environment, both FT runtimes remain GIL-disabled, every `pip check` passes, and baseline/candidate package freezes match byte-for-byte within each mode. Editable worker hooks installed. Complete setup logs, package lists, inventory and native results are retained in [full preparation](full-pyperformance-preparation/README.md). The initial parent-directory invocation shadowed the installed pyperformance package and failed before environment creation; its log is retained alongside the corrected invocation.

Added a pyperformance-only restart launcher, with no benchmark implementation changes. Syntax checking passes. Missing preparation records and an isolated copied candidate-FT GIL-enabled record both cause refusal before results or timing. The actual ready records remain unchanged. Launch all four enabled/disabled × GIL/FT binary ABBAs using the fresh root, never the interrupted attempt's partial result tree. Complete preparation does not yet establish benchmark runtime compatibility or completed suites.

### Corrected pyperformance campaigns launched

At 05:55:44 UTC on 17 October, the restart launcher passed all four source/binary, native/runtime, dependency and harness checks and started GIL enabled baseline leg 1 in the fresh prepared root. Preparation checkpoint is parent `fa3bbdc`; the CPython source pair and binaries are unchanged. Controller PID 1711376 and driver PID 1711703 were independently observed live. The unified execution session is 7948. Logs and new results belong only to `/tmp/parallel-gc-pyperformance-prepared-20261017-dBFKZD`, not the interrupted attempt's tree.

The launcher retains the complete four-campaign order: GIL enabled, GIL disabled, FT enabled, FT disabled; each is baseline/candidate/candidate/baseline with unchanged rigorous/default flags, affinity 0–31 and NUMA node 0. No corrected suite is complete at this entry. No competing build, benchmark or collector change is scheduled during measurement. Current hosted-CI capture remains absent.

### Default-suite runtime failures isolated from collector activation

The corrected GIL-enabled baseline attempted the unchanged 100-program default selection and exited nonzero: Dask fails during Cloudpickle import on the missing `DELETE_GLOBAL` opcode; Genshi fails constructing an AST node without its required `body` field. Its JSON retains 124 successful named results, including FastAPI, but is not a completed suite or ABBA comparison. [Dependency compatibility evidence](dependency-compatibility/README.md) preserves the complete failed log, partial JSON, exact hashes, original workloads and four untimed probes.

Both exceptions reproduce on all four real measurement environments with parallel GC explicitly disabled and no helper pool before or after. Both FT runtimes retain a disabled GIL. This falsifies the claim that these exceptions require collector activation; it is not a general correctness verdict. Dependency installation and native readiness checks had passed but did not cover every program's runtime compatibility.

At 07:54 UTC on 17 October, stopped the revalidated dedicated campaign process group and verified every member gone. GIL-disabled baseline was interrupted; no FT pyperformance suite had started. No files were deleted or workloads excluded. Dependency compatibility changes require discussion before restarting the unchanged full campaign. Current hosted CI capture remains absent.

### All-program runtime compatibility diagnostic completed

Eight sequential diagnostic checks ran from 07:56:57 to 08:23:48 UTC on 17 October. Every invocation attempted the exact ordered 100-program default selection with the existing `--run-style debug`; these short executions are compatibility checks, not performance measurements or a replacement ABBA. [Complete runtime evidence](default-runtime-compatibility/README.md) preserves all logs, partial JSONs, exit statuses, archive/original hashes, package inventories and a checked machine summary.

All four GIL checks fail only Dask and Genshi. All four FT checks additionally fail Coverage, dulwich_log, Sphinx and both SQLAlchemy variants. These five additional failures follow native-extension GIL fallback: `coverage.tracer`, `dulwich._objects`, `markupsafe._speedups` and `greenlet._greenlet` enable the GIL, and the worker hook refuses to label the runs FT. Failure sets match between source revisions and collector policies. No check was removed, no unsafe GIL override was introduced, and no dependency compatibility repair has been made.

All 972 saved diagnostic run records passed compiled/runtime mode and collector-policy checks; successful result-name sets match within each build mode. Source trees remain clean and all binary/harness checks pass. Post-run baseline/current package freezes match within each mode. Compared with initial preparation, the standard 2to3 workload installed its vendored `lib2to3` and pip's editable URL reflects the later parent commit; original third-party dependency versions remain unchanged. The execution session completed and its controller is no longer live. Full rigorous comparisons and hosted CI evidence are still required.

### Full local release suite started; source-path failures reproduced

After entry-document reconciliation commit `4545edc`, ran full default local CPython tests on the current optimized GIL and FT binaries with the Linux workflow's regrtest options, sequentially. Both completed with exit 2: pydoc and unittest files failed again on rerun. GIL reports 52,149 tests, six failures and 2,777 skips, including reruns; file totals are `run=502/509 failed=2 skipped=29 resource_denied=9 rerun=2`. FT reports 52,250 tests, six failures and 2,782 skips; `run=502/509 failed=2 skipped=27 resource_denied=9 rerun=2`. The controller finished at 08:47:44 UTC and is gone. These are additional local release checks, not hosted debug/Windows/macOS evidence.

[Full local evidence](local-full-suite/README.md) records the source aliases, both failed full logs and eight four-case probes. Default-path failures reproduce on baseline/current GIL/FT. Using physical `Lib` paths fixes pydoc but not the unittest child, which deliberately ignores `PYTHONPATH` with `-E`. The four-case complete-repair hypothesis is falsified; no tests or source were changed. Both alias paths refer to the same original clean source worktrees at their recorded revisions. Preserve existing binaries and performance data; do not assume source-path preparation defects are collector regressions. A consistently addressed build/test environment and hosted evidence remain pending.

### Physical-source debug follow-up

Fresh GIL/FT debug builds configured directly from the physical current source make all four previously failing path-sensitive cases pass, without CPython changes. The first build attempt failed finding `uuid.h`: the investigation helper omitted the relocated prefix's `PKG_CONFIG_SYSROOT_DIR`. Restoring that build-environment variable and building in a fresh directory succeeds in both modes. The failure and flags comparison are preserved, not discarded.

[Complete debug evidence](local-full-suite/physical-debug/README.md) records the full default outcomes. FT passes, exit 0: 52,306 tests, 2,714 skips; `run=500/509 skipped=21 resource_denied=9`; 12 min 34 sec. GIL returns exit 3, `ENV CHANGED`: 52,388 tests, 2,759 skips; `run=501/509 env_changed=1 skipped=23 resource_denied=9 rerun=1`; 13 min 2 sec. The multiprocessing spawn process module left three temporary files initially and again on rerun. No assertion failure is reported in the GIL summary, but this is not a clean full pass.

The same isolated module passes on fresh baseline and current GIL debug builds, with 183 tests and 15 skips in each. Repeating without the original CPU-32 affinity restriction also passes on both. These observations do not reproduce a source-specific isolated leak and do not explain the full-run failure. The completed GIL/FT controller ended at 09:18:24 UTC on 17 October. A new sequential full baseline/current GIL comparison was launched after completion; it remains separate from the preserved completed outcomes above. No benchmark, collector, test or skip changed. Binary hashes and clean source checks pass. Current hosted CI and dependency approval remain unavailable.

### Matched full GIL comparison completed

Ran full default GIL suites sequentially on the fresh physical baseline/current debug builds, without an affinity restriction or any source/test change. Both pass, exit 0. Baseline ran 09:18:34–09:29:43 UTC: 52,202 tests, 2,715 skips; `run=500/509 skipped=23 resource_denied=9`; 11 min 8 sec. Current ran 09:29:43–09:40:36 UTC: 52,205 tests, 2,723 skips; the same file totals; 10 min 52 sec. Neither reports an environment change or rerun. [Complete matched evidence](local-full-suite/gil-full-comparison/README.md) includes logs, exits, identical 509-file selections, native/runtime/path probes, clean source revisions and unchanged binary hashes.

The earlier GIL temporary-file leak did not reproduce in this full comparison. It remains unexplained and is not declared repaired. Combined with the preceding FT full pass, both current modes have passing full local debug runs; these do not substitute for hosted-platform results. The comparison controller completed and its processes are gone. No benchmark is running. Dependency compatibility changes and current CI capture still await Alex; no workload was excluded or runtime check bypassed.

### Focused FT controlled-collection reproduction completed

Prepared an external diagnostic wrapper and validator test-first, committed separately as `f9924bc`. All nineteen machinery tests pass, including planted disabled/inactive pool, invalid source/order/placement/parameters, incomplete cases and bad samples/counts. Twenty-four existing full-analysis tests also pass. Real GIL, debug FT and wrong-affinity invocations refuse before a case or JSON result. The benchmark implementation and CPython source/tests remain unchanged.

[Four complete focused FT legs](focused-collections/RESULTS.md) ran 09:49:04–09:52:47 UTC on 17 October, baseline–current–current–baseline, with the same optimized binaries, all sixteen controlled cases and unchanged per-case parameters. All checks and final source/binary/driver fingerprints pass; generated-member sequences match both arms, all focused legs and the original full comparison. A separate arithmetic calculation verifies both source means, overall change and both halves in both arms for every case.

The broad module-rooted slowdown did not reproduce: five module means decrease, three increase +0.34% to +1.32%, and only web-server increases in both halves. Frame layered changes −4.82%, with opposing halves, rather than repeating its original both-halves increase. Five frame cases still have higher overall means and are reported. This diagnostic omits preceding sustained workloads and imports the benchmark as a normal module rather than `__main__`. It is inconclusive about cause and does not erase the full suite's negative observations or establish neutrality. The controller completed, with no benchmark left running. Next is an unchanged full FT repeat, not a collector change. Dependency approval and current hosted CI capture remain missing.

### Unchanged full FT repeat launched

After committing the focused outcome as `ebdba89`, launched a new full FT baseline–current–current–baseline sequence at 09:58:22 UTC on 17 October. It uses the same original `gc_perf_benchmark.py` entry point and unchanged `--full --include-synthetic --json` parameters, including the preceding mixed and sustained phases omitted by the focused diagnostic. This tests whether the original negative pattern recurs in the original invocation context. No collector or benchmark source changed; no threshold, worker-count pin or workload exclusion was introduced.

Both existing FT binaries pass their original hashes and complete native/runtime preflights; both source worktrees are clean at the fixed source pair. Baseline leg 1 is independently observed live. Execution session is 74721; separate scratch root is `/tmp/parallel-gc-ft-full-repeat-20261017-NZLRWT`. No repeat leg is complete at this entry. Preserve this campaign separately from the original full results and focused results; do not infer completion or performance from its launch.

Each leg runs from the parent root with affinity 0–31 and NUMA CPU/memory node 0, followed by source/binary/benchmark/analysis fingerprint checks. The controller calls the existing complete-project analyser only after all four JSONs exist. Parent/native/host provenance is retained; a process-name/CPU snapshot is an observation at launch, not proof of continuous host isolation. No other project measurement was observed at launch. Previous full FT legs took six hours twenty minutes; this is a timing estimate for the repeat, not a result.

Core measurement command within the four-source loop:

```bash
numactl --cpunodebind=0 --membind=0 taskset -c 0-31 \
    "$repeat_build_root/$repeat_revision-ft/python" \
    benchmarks/gc_perf_benchmark.py \
    --full --include-synthetic --json \
    --output "$repeat_out/ft-$repeat_leg-$repeat_revision.json"
```

The actual controller redirects each complete stdout/stderr stream to its matching `.log`. `repeat_build_root` is `/tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW`; `repeat_out` is the separate root above; the source loop is baseline, candidate, candidate, baseline. The existing analyser runs with `--mode ft` against that root after four complete legs. Remaining pyperformance and hosted-platform requirements are unchanged; this repeat does not replace them.

### Full FT repetition baseline leg completed

Baseline leg 1 finished at 11:32:48 UTC on 17 October after 94 minutes 26 seconds. All original source, binary and benchmark/analysis fingerprints pass; candidate leg 2 then started in the same controller. [Repeat evidence](full-ft-repeat/README.md) preserves the complete first JSON/log and provenance. Standard configuration, clean baseline source, compiled FT mode, affinity/NUMA, all eight sustained and sixteen controlled cases, five valid samples per arm and generated-member sequences matching the original full experiment pass their checks.

The first document records parent `ebdba89d428d1b0ff53a396edff22390c40b9ae2` dirty with unrelated untracked files; measured source/benchmark content remains unchanged. This observation is retained. Numerical validation runs use spare CPU 32; lightweight artifact copying and hash checks were not affinity-pinned. No builds or competing benchmark campaigns ran. The complete-project analyser refuses the actual unfinished campaign with no JSON because leg 2 is absent. No baseline-only source effect is reported. Three closing legs, pyperformance compatibility agreement and current hosted CI evidence remain required.

### Full FT repetition current leg 2 completed

Current leg 2 ran 11:32:48–13:07:08 UTC on 17 October, 94 minutes 20 seconds. Its complete JSON and log are preserved in [repeat evidence](full-ft-repeat/README.md), byte-identical to the scratch originals. Standard configuration, source/compiled mode, affinity/NUMA, eight sustained comparisons, sixteen controlled cases and five valid samples per arm pass. Every controlled generated-member sequence matches both the original full experiment and repeat leg 1. Post-leg source, binary and benchmark/analysis fingerprints pass; leg 3 started on the existing controller at 13:07:08 UTC. The four-leg source comparison remains incomplete. No collector or benchmark changed.

### Full FT repetition current leg 3 completed

Current leg 3 ran 13:07:08–14:41:54 UTC on 17 October, 94 minutes 46 seconds. Its complete JSON and log are preserved byte-identically in [repeat evidence](full-ft-repeat/README.md). Standard configuration, source/compiled mode, affinity/NUMA, eight sustained comparisons, sixteen controlled cases and five valid samples per arm pass. Every controlled generated-member sequence matches both the original full experiment and repeat legs 1 and 2. Post-leg source, binary and benchmark/analysis fingerprints pass. The closing baseline leg started at 14:41:54 UTC on the existing controller. The complete source comparison is not yet available; no collector or benchmark changed.

### Goal continuation: completion requirements and current evidence

The handoff objective remains all planned tests and benchmark campaigns, followed by evidence commits and a core-developer discussion starting point. The pyperformance campaign is stopped pending dependency agreement; the separate unchanged full FT repetition is live, with legs 1–3 complete and closing baseline leg 4 running. Earlier process entries are dated observations, not evidence of current state. No completed requirement is inferred from a plan or a successful older run.

| Requirement | Current state | Evidence needed for completion |
|-------------|---------------|--------------------------------|
| Corrected baseline/current GIL/FT PGO+LTO builds | Complete; supplementary local tests also passed | Four-build evidence preserved below; full CPython and hosted platform requirements remain separate |
| Linux four-configuration matrix | Parent push reported; outcomes unknown | Run source pair, four job outcomes, focused collector/parent tests and feature-off skips |
| GCC/Clang object checks | Parent push reported; outcomes unknown | Eight compiler/mode/build job outcomes and diagnostics; this is an unused-code gate, not every-warning acceptance |
| Linux full CPython suite | Manual dispatch reported; outcomes unknown | Both GIL/FT feature-on full default suites, exact source pair, failures/reruns/skips |
| Windows regression workflow | Manual dispatch reported; outcomes unknown | Both x64 GIL/FT feature-on jobs, focused collector/parent tests and full CPython suites |
| macOS regression workflow | Manual dispatch reported; outcomes unknown | Four build modes/controls; focused collector/parent tests; full GIL/FT feature-on suites; runner architecture |
| Project full ABBA | Complete: all four GIL and four FT legs preserved and analysed; old attempt kept separate | Eight-leg data, hashes and complete analyses are preserved; negative observations still require follow-up rather than a neutrality claim |
| pyperformance full comparisons | First corrected suite failed; eight all-program diagnostic checks identify two GIL and seven FT failing programs, independent of source revision and collector activation; full campaign stopped | Agreed dependency compatibility work, repeat all-program readiness checks without FT GIL fallback, then all sixteen rigorous suites across four enabled/disabled × GIL/FT binary-ABBA campaigns; raw legs, attestation, program set, failures and source/binary provenance |
| Analysis and handoff commits | GIL and FT data/writeups preserved; pyperformance and hosted-CI reconciliation pending | Remaining pyperformance changes/controls and uncertainty; final VALIDATION/PERFORMANCE links; tracked worktrees clean; publication commands for local commits |

Direct GitHub read access returned a destination-filter denial. Alex was asked to capture the current run listing in `/tmp/alex-ci-current.json`; no remote status is inferred while waiting. `git diff ff6710f HEAD` confirms the published checkpoint's collector tests, benchmark implementation and workflows are unchanged by the subsequent local preflight/evidence commits; its CPython gitlink is the intended `388fd5bb46`. Job-specific source artifacts still need verification.

Result-schema inspection uses the abandoned first leg only as a format specimen, not performance evidence. Sustained results contain five run-level means per serial/parallel arm; controlled collections contain individual times and generated counts. Analysis will preserve those run-level units instead of pooling collections. The latency tracker measures the interval between a collection's `start` and `stop` callbacks, not between successive collections, and not FT stopped-world duration.

Build provenance also distinguishes the version tag from source cleanliness. CPython's generated Makefile invokes `git --git-dir <source>/.git describe ... --dirty` from the build directory. In the baseline build this reports `-dirty`; adding `--work-tree <source>` removes it while `git -C <source> diff` is clean. The runtime JSON independently records the source commit and clean tracked content. Preserve the original version stamp and this explanation; do not relabel a binary or modify collector code to hide metadata.

## Verdict

Original GIL and FT project measurements and analyses are complete, with negative observations and unresolved attribution documented. The unchanged full FT repetition is live: three legs complete, closing baseline leg 4 running, no complete source comparison yet. Both current modes have passing full local debug runs; an earlier GIL environment leak remains unexplained. Full-default pyperformance installation passed, but runtime dependency failures prevent a complete comparison; both API failures occur without collector activation, and five further FT programs enable the GIL through native dependencies. That pyperformance campaign is stopped, evidence is preserved, and dependency changes remain unapproved. Current hosted CI remains unverified. Handoff is not complete.
