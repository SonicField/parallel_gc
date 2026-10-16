# Investigation: integrated-source CI and performance

**Status:** Four corrected optimized builds and supplementary local tests passed. Three of eight corrected project legs are complete; closing baseline GIL leg 4 is running. Hosted CI dispatched by Alex, run IDs pending.
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
| Project full ABBA | GIL legs 1–3 complete; closing baseline leg 4 running; old attempt kept separate | Eight corrected-build invocations, each with original and module-rooted variants, all run-level data and consistent configuration/object counts |
| pyperformance full comparisons | Not started | Four rigorous enabled/disabled × GIL/FT binary-ABBA campaigns; all raw legs, attestation, program set, failures and source/binary provenance |
| Analysis and handoff commits | Pending complete results | Per-workload negative and positive changes, both ABBA halves, serial controls and uncertainty; evidence linked from VALIDATION/PERFORMANCE; tracked worktrees clean; publication commands for local commits |

Direct GitHub read access returned a destination-filter denial. Alex was asked to capture the current run listing in `/tmp/alex-ci-current.json`; no remote status is inferred while waiting. `git diff ff6710f HEAD` confirms the published checkpoint's collector tests, benchmark implementation and workflows are unchanged by the subsequent local preflight/evidence commits; its CPython gitlink is the intended `388fd5bb46`. Job-specific source artifacts still need verification.

Result-schema inspection uses the abandoned first leg only as a format specimen, not performance evidence. Sustained results contain five run-level means per serial/parallel arm; controlled collections contain individual times and generated counts. Analysis will preserve those run-level units instead of pooling collections. The latency tracker measures the interval between a collection's `start` and `stop` callbacks, not between successive collections, and not FT stopped-world duration.

Build provenance also distinguishes the version tag from source cleanliness. CPython's generated Makefile invokes `git --git-dir <source>/.git describe ... --dirty` from the build directory. In the baseline build this reports `-dirty`; adding `--work-tree <source>` removes it while `git -C <source> diff` is clean. The runtime JSON independently records the source commit and clean tracked content. Preserve the original version stamp and this explanation; do not relabel a binary or modify collector code to hide metadata.

## Verdict

Pending. No new performance or hosted-CI result is claimed.
