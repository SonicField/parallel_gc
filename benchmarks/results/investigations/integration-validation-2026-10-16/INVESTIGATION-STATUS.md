# Investigation: integrated-source CI and performance

**Status:** Four corrected optimized builds and supplementary local tests passed. All eight project legs and both source analyses are complete. Fresh 100-program default pyperformance environments are prepared on all four binaries; corrected full campaigns are the next step. Hosted CI dispatched by Alex, run IDs pending.
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

### Goal continuation: completion requirements and current evidence

The handoff objective remains all planned tests and benchmark campaigns, followed by evidence commits and a core-developer discussion starting point. The preceding status turn was a verified wait: the specific old measurement and queued build/campaign processes are still live. No completed requirement is inferred from a plan or a successful older run.

| Requirement | Current state | Evidence needed for completion |
|-------------|---------------|--------------------------------|
| Corrected baseline/current GIL/FT PGO+LTO builds | Complete; supplementary local tests also passed | Four-build evidence preserved below; full CPython and hosted platform requirements remain separate |
| Linux four-configuration matrix | Parent push reported; outcomes unknown | Run source pair, four job outcomes, focused collector/parent tests and feature-off skips |
| GCC/Clang object checks | Parent push reported; outcomes unknown | Eight compiler/mode/build job outcomes and diagnostics; this is an unused-code gate, not every-warning acceptance |
| Linux full CPython suite | Manual dispatch reported; outcomes unknown | Both GIL/FT feature-on full default suites, exact source pair, failures/reruns/skips |
| Windows regression workflow | Manual dispatch reported; outcomes unknown | Both x64 GIL/FT feature-on jobs, focused collector/parent tests and full CPython suites |
| macOS regression workflow | Manual dispatch reported; outcomes unknown | Four build modes/controls; focused collector/parent tests; full GIL/FT feature-on suites; runner architecture |
| Project full ABBA | Complete: all four GIL and four FT legs preserved and analysed; old attempt kept separate | Eight-leg data, hashes and complete analyses are preserved; negative observations still require follow-up rather than a neutrality claim |
| pyperformance full comparisons | Fresh 100-program default preparation complete on all four targets; interrupted attempt separately preserved | Four rigorous enabled/disabled × GIL/FT binary-ABBA campaigns; all raw legs, attestation, program set, failures and source/binary provenance |
| Analysis and handoff commits | GIL and FT data/writeups preserved; pyperformance and hosted-CI reconciliation pending | Remaining pyperformance changes/controls and uncertainty; final VALIDATION/PERFORMANCE links; tracked worktrees clean; publication commands for local commits |

Direct GitHub read access returned a destination-filter denial. Alex was asked to capture the current run listing in `/tmp/alex-ci-current.json`; no remote status is inferred while waiting. `git diff ff6710f HEAD` confirms the published checkpoint's collector tests, benchmark implementation and workflows are unchanged by the subsequent local preflight/evidence commits; its CPython gitlink is the intended `388fd5bb46`. Job-specific source artifacts still need verification.

Result-schema inspection uses the abandoned first leg only as a format specimen, not performance evidence. Sustained results contain five run-level means per serial/parallel arm; controlled collections contain individual times and generated counts. Analysis will preserve those run-level units instead of pooling collections. The latency tracker measures the interval between a collection's `start` and `stop` callbacks, not between successive collections, and not FT stopped-world duration.

Build provenance also distinguishes the version tag from source cleanliness. CPython's generated Makefile invokes `git --git-dir <source>/.git describe ... --dirty` from the build directory. In the baseline build this reports `-dirty`; adding `--work-tree <source>` removes it while `git -C <source> diff` is clean. The runtime JSON independently records the source commit and clean tracked content. Preserve the original version stamp and this explanation; do not relabel a binary or modify collector code to hide metadata.

## Verdict

GIL and FT project measurements and analyses are complete, with negative observations and unresolved attribution documented. Full-default pyperformance preparation is complete, but completed campaigns and current hosted CI remain unverified. Handoff is not complete.
