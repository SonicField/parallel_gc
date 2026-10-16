# Unreferenced-code integration checks

16 October 2026. Baseline: CPython `c67363fa59543ef5d572383af927f1cff88514a1`. Integrated cleanup: `442a97213fb1cc6faef34a2f362d0b6dcf970e2e`, derived from candidate `b3b5557ed5afdb88e3a01f4fcc244a87fab0fcfe`.

## Hypothesis and falsifiers

The removed implementation is unreferenced. Removing it does not change the active collectors. A surviving caller, active-path edit, changed exported GC symbol set or unexplained focused-test outcome would block integration. This is not a performance claim.

Reviewed all four source-file diffs. Repository-wide whole-word searches covered eighteen removed function names and three removed types, including platform build files. References occurred only inside the removed implementations or their declarations/comments. Repeating the search after removal returned no matches. Active marking, deque, barrier and atomic operations were not edited. The candidate additionally places a debug-only counter and debug test cleanup under `Py_DEBUG`. Integration removes empty preprocessor pairs and orphan coordinator headings left by the candidate; no additional function bodies change.

## Fresh local builds

ARM64 Linux, GCC 11.5.0, four out-of-tree feature-on builds: `--with-parallel-gc`, optionally `--disable-gil` and/or `--with-pydebug`. No PGO or LTO. The source was a fresh detached baseline worktree; the cleanup was then applied to it. Its complete working diff against integrated commit `442a97213f` was empty for the four modified files. Other source remained at the baseline. The resulting binaries report the detached baseline's dirty source stamp, not a clean-commit stamp.

The focused compilation used `-Werror=unused-function -Werror=unused-variable` for the four GC objects. The normal build follows that check. This gate does not detect unused typedefs or unused static inline helpers; repository-wide reference checks address those removals. It does not substitute for compilation on Windows or macOS.

| Build | Baseline warning gate | Cleanup warning gate | Tests before and after: run / skipped | Defined global GC symbols |
|-------|-----------------------|----------------------|---------------------------------------|---------------------------|
| GIL release | exit 2, 3 errors | exit 0 | 346 / 85 | 62, unchanged |
| FT release | exit 2, 12 errors | exit 0 | 374 / 74 | 81, unchanged |
| GIL debug | exit 2, 3 errors | exit 0 | 346 / 82 | 62, unchanged |
| FT debug | exit 2, 10 errors | exit 0 | 374 / 40 | 86, unchanged |

All eight focused test invocations exited 0. They cover GC, deque primitives, lifecycle/fork scenarios, marking/properties, PGO workload, configuration and embedding; FT adds `test_free_threading.test_gc`. GIL skips the two FT-specific module-level suites. The first invocation mistakenly named `test_gc_parallel_profile`, which does not exist; all four failed its import. Correcting the local script to the existing `test_parallel_gc_profile` produced the results above. No project test or collector repair was made for that command error.

Two additional fresh feature-off debug controls passed: GIL 311 tests / 122 skips; FT 374 / 157. These controls are cleanup-only runs, not before/after pairs. Fourteen optional extension modules were unavailable and SQLite was configure-disabled in these local builds. These are focused checks, not full-suite or dependency-complete validation.

Raw warning/test logs and sorted defined-global-symbol lists accompany this report. `check.sh` records the four-build procedure; `controls.sh` records the feature-off procedure. To reproduce, create a fresh detached baseline worktree and isolated build root, change the scripts' explicit `root`, run `check.sh baseline`, apply `git diff c67363fa59 442a97213f` to that source, then run `check.sh cleanup` and `controls.sh`. Do not reuse another checkout's build directories. The gate is intended to compile fresh baseline objects and recompile changed cleanup sources.

Cleanup binary SHA-256:

```text
GIL release 8991f3981c8970b050b4563c4f9161b927bcd182e3dcc1c390efc2be10721793
FT release  a30c15b523c8fb21b6b28af72eae33e2461edc2319621d1dd6768892522a74bb
GIL debug   c0572c32f8f47c0bfa18dfb2bab9db828561c87f8d2dc8a1396757fa18ffd31f
FT debug    3b861471289170a12b2b41251042b015b278c1ac7fd31c81b13f1fbf79a3ee60
```

ASan/TSan, Clang, full CPython suites and hosted platform validation have not been run for this source pair. The next implementation unit is the production marking verifier/test change; sanitizer checks belong to that unit. Fresh hosted tests remain required after publishing the integrated source.
