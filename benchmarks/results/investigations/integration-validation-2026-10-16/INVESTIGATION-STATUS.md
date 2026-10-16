# Investigation: integrated-source CI and performance

**Status:** Initial builds completed but native decimal was missing. Their campaign launcher is stopped. Corrected fresh builds are queued; hosted CI dispatched by Alex, run IDs pending.
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

## Verdict

Pending. No new performance or hosted-CI result is claimed.
