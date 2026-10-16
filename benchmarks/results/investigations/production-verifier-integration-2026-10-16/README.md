# Production marking verifier integration

16 October 2026. Integrated CPython `0fc7b3ccb938e367e23c140995a8f2e4b6757b49`, following cleanup `442a97213f`. Candidate: `be478ea01733664477eed823f5e85a2fbaa0f89f`, including its correction that replaces the timing-dependent work-balance assertion with module-rooted serial equivalence. No rejected propagation/queue experiment was imported.

## Outcome and tested contract

The marking tests now run the production pool through `gc.collect()`, require a parallel pass to have run, and compare its ALIVE marks with serial recomputation. The separate test-only page-marking implementation, its thread creation, unused state fields and always-success atomic-test stub are removed. Repository-wide symbol checks found no surviving references. GIL exported GC symbols are unchanged; FT release loses only `_PyGC_ParallelMarkAlive`, and FT debug additionally loses the two retired test exports. No active atomics, barriers, queue operations, traversal loops, adaptation policy or startup-failure semantics were changed.

The verifier is debug-only and explicitly enabled with `gc._test_set_parallel_mark_verify(True)`. It snapshots the parallel ALIVE set while the world remains stopped, clears ALIVE, runs the same root-marking implementation with parallel dispatch disallowed, and records missing/extra marks. It keeps the serial result. Default-off and toggle/reset tests verify that recomputation is opt-in; release objects contain no verifier functions. Per-worker propagation counts are copied after dispatch because the later MARK_HEAP phase resets the working counters. Counts are diagnostic, not a work-balance requirement.

## Test-first failures and corrections

Loading the candidate tests before its hook ran ten test cases with nine skips. An explicit hook-availability assertion failed. Skips were not counted as production-marking evidence.

The first unmutated scratch matrix reported a module-rooted test failure, but the driver recorded only FAIL, not its assertion. The driver was changed to retain failure details. Thirty same-process repeats, eighty fresh-process repeats and five hundred further fresh-process runs with additional difference diagnostics did not reproduce that failure. The original matrix is retained as `mutations/none.tsv`; its precise cause remains unknown. An attempted repeat run launched while relinking failed to locate build extensions; those invocations were discarded and rerun after the build completed.

An independent, deterministic case found a verifier defect: 1,000 dynamically constructed three-level tuples begin with tracked outer/middle tuples. Parallel marking untracks the middle tuples. Serial replay can then untrack the outer tuples. The original verifier reports `(missing, extra) == (0, 1000)` although collection coverage is correct. A new regression test failed with that exact assertion before the repair.

The repair changes only debug comparison accounting: snapshot objects that become untracked during replay are reported separately as `verify_untracked`, not called extra marks. Raw parallel and serial counts remain available. With no missing/extra marks, the checked relation is `parallel_alive - verify_untracked == serial_alive`. The nested-tuple test requires at least its 1,000 replay-untracked tuples and checks their tracking state. No production untracking/traversal logic was changed. This demonstrates a false-positive mechanism, but does not prove it caused the earlier undetailed failure.

After extending the diagnostic structure, an incremental build returned an invalid participant count (64 instead of 4), then crashed in a lifecycle test. The five parallel-GC headers are absent from Makefile dependencies: pretending `pycore_gc_ft_parallel.h` changed does not rebuild the GC object, while the existing `pycore_gc.h` dependency does. Stale layout-dependent objects were discarded by cleaning only the owned scratch builds; complete rebuilds passed. The dependency repair is a separate build-system unit. Do not interpret the mixed-object run as evidence about the clean commit.

## Final clean-build results

ARM64 Linux, GCC 11.5.0. Four feature-on builds: `--with-parallel-gc`, optionally `--disable-gil` and/or `--with-pydebug`. No PGO/LTO. The entire tracked source content used by the final builds matches `0fc7b3ccb9`; the detached scratch worktree's version stamp still names its dirty baseline, not that clean commit. All four focused unused-function/variable GC-object gates exit 0. Full build logs report fourteen unavailable optional modules and configure-disabled SQLite; this is not dependency-complete validation.

| Configuration | Runner summary: run / skipped | Result |
|---------------|-------------------------------|--------|
| GIL release | 349 / 88 | SUCCESS |
| FT release | 377 / 77 | SUCCESS |
| GIL debug | 349 / 85 | SUCCESS |
| FT debug | 377 / 40 | SUCCESS |
| GIL feature-off debug control | 314 / 125 | SUCCESS |
| FT feature-off debug control | 377 / 160 | SUCCESS |
| GIL ASan debug | 349 / 85 | SUCCESS, no diagnostic |
| FT ASan debug | 377 / 40 | SUCCESS, no diagnostic |
| GIL TSan debug | 242 / 78 | SUCCESS, no diagnostic |
| FT TSan debug | 158 / 25 | SUCCESS, no diagnostic |

Normal/ASan selections include GC, lifecycle/fork, deque, marking/properties, PGO-workload, configuration and embedding tests; FT adds its upstream GC tests. TSan uses the bounded selections in `sanitizers.sh`, not the full suite. ASan disables leak detection. TSan uses `halt_on_error=1 die_after_fork=0 handle_segv=0` and the checked-in suppression file, which currently contains no active suppressions. A locally extracted GCC 11.5 runtime was selected through linker search/rpath because the system linker script names a missing library. Its SHA-256 is `196a2b1509f218ecd908154430d0e3e6808495edcf9a06b3643d4a7cb0640556`. No system library was replaced.

The corrected thirteen-case marking suite also passed thirty same-process repeats: 390 runner cases, thirty expected ctypes skips, no failures/errors. ctypes is unavailable locally; its production traversal test needs hosted dependency-complete builds. Final regular binary SHA-256 values:

```text
GIL release 1b45366264fc8b5f0f00d0c94c8e7c667b51c7a2fe9987352a0230b708b1571c
FT release  a676e92ca9a62d156c024c09010d5a1aecd88a74fbe8215d41b29fad52afa53f
GIL debug   1e6586c4dd5d1e5608b77c79a46ff62747f3152ba906ce21301fbb9042996e1b
FT debug    1d475c8a6bdcbe08612908d9e3de3f2934b3f6d1203339d75bc7c355a3a05edf
```

## Mutation sensitivity

Mutations were made only in a separate scratch source/build. The final pristine suite passes except ctypes. Both first-root and last-root omission cause all nine coverage-asserting tests plus toggle/reset to fail; the opt-in-only and untracked-visit tests pass. Omitting one generic edge at atomic counter value 1000 is detected by repeated-collection and toggle/reset tests in the final run; other tests pass because an omitted edge may not remove an object's last marking path. The untracked-visit test checks excessive visits, not missing edges, and is not expected to fail these mutations. Worker distribution is not asserted.

The four final matrix files include failure details. These mutations show sensitivity to those defects, not all possible marking errors. `marking_matrix.py` records outcomes; `check.sh` and `sanitizers.sh` retain the commands. Reproduction requires fresh isolated source/build directories and the selected source commit; change the scripts' explicit scratch root. The added nested-tuple, opt-in and reset tests are checked in with the implementation.

Not established: verifier allocation-failure injection, all custom traversal behaviour, full CPython regression suites, Clang, Windows/macOS, or performance neutrality. Snapshot allocation failure records no verifier run; tests require the run count to advance. Existing collection rollback/unique-ID/join-failure audit items remain open. New source-pair hosted CI and matched-harness PGO/LTO campaigns remain pending; this record is not a landing-readiness claim.
