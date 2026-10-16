# Investigation: integrated-source CI and performance

**Status:** Initial builds completed but native decimal was missing. Their campaign launcher is stopped and its last running leg has finished. Corrected fresh builds have started; hosted CI dispatched by Alex, run IDs pending.
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
3. Record every raw leg, per-workload means, both ABBA halves, build/driver provenance, source/harness hashes and skips/failures. Report program throughput, collection time and callback interval distinctly. Do not call an FT callback interval a stopped-world pause.
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

### Goal continuation: completion requirements and current evidence

The handoff objective remains all planned tests and benchmark campaigns, followed by evidence commits and a core-developer discussion starting point. The preceding status turn was a verified wait: the specific old measurement and queued build/campaign processes are still live. No completed requirement is inferred from a plan or a successful older run.

| Requirement | Current state | Evidence needed for completion |
|-------------|---------------|--------------------------------|
| Corrected baseline/current GIL/FT PGO+LTO builds | Both GIL builds checked; baseline FT building, candidate FT queued | Four clean-source builds; native decimal/runtime-mode checks; actual profile-use/LTO flags and parallel training; focused/decimal tests; executable hashes |
| Linux four-configuration matrix | Parent push reported; outcomes unknown | Run source pair, four job outcomes, focused collector/parent tests and feature-off skips |
| GCC/Clang object checks | Parent push reported; outcomes unknown | Eight compiler/mode/build job outcomes and diagnostics; this is an unused-code gate, not every-warning acceptance |
| Linux full CPython suite | Manual dispatch reported; outcomes unknown | Both GIL/FT feature-on full default suites, exact source pair, failures/reruns/skips |
| Windows regression workflow | Manual dispatch reported; outcomes unknown | Both x64 GIL/FT feature-on jobs, focused collector/parent tests and full CPython suites |
| macOS regression workflow | Manual dispatch reported; outcomes unknown | Four build modes/controls; focused collector/parent tests; full GIL/FT feature-on suites; runner architecture |
| Project full ABBA | Old incomplete attempt preserved; replacement not started | Eight corrected-build invocations, each with original and module-rooted variants, all run-level data and consistent configuration/object counts |
| pyperformance full comparisons | Not started | Four rigorous enabled/disabled × GIL/FT binary-ABBA campaigns; all raw legs, attestation, program set, failures and source/binary provenance |
| Analysis and handoff commits | Pending complete results | Per-workload negative and positive changes, both ABBA halves, serial controls and uncertainty; evidence linked from VALIDATION/PERFORMANCE; tracked worktrees clean; publication commands for local commits |

Direct GitHub read access returned a destination-filter denial. Alex was asked to capture the current run listing in `/tmp/alex-ci-current.json`; no remote status is inferred while waiting. `git diff ff6710f HEAD` confirms the published checkpoint's collector tests, benchmark implementation and workflows are unchanged by the subsequent local preflight/evidence commits; its CPython gitlink is the intended `388fd5bb46`. Job-specific source artifacts still need verification.

Result-schema inspection uses the abandoned first leg only as a format specimen, not performance evidence. Sustained results contain five run-level means per serial/parallel arm; controlled collections contain individual times and generated counts. Analysis will preserve those run-level units instead of pooling collections. The latency tracker measures the interval between a collection's `start` and `stop` callbacks, not between successive collections, and not FT stopped-world duration.

Build provenance also distinguishes the version tag from source cleanliness. CPython's generated Makefile invokes `git --git-dir <source>/.git describe ... --dirty` from the build directory. In the baseline build this reports `-dirty`; adding `--work-tree <source>` removes it while `git -C <source> diff` is clean. The runtime JSON independently records the source commit and clean tracked content. Preserve the original version stamp and this explanation; do not relabel a binary or modify collector code to hide metadata.

## Verdict

Pending. No new performance or hosted-CI result is claimed.
