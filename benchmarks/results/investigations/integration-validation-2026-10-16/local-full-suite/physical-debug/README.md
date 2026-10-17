# Physical-source debug suites and multiprocessing environment probes

## Outcome

Current FT's full default local suite passed, exit 0. Current GIL's full default suite returned exit 3, `ENV CHANGED`, because `test.test_multiprocessing_spawn.test_processes` left three temporary files on its first run and again on rerun. No assertion failure is reported in that GIL summary. This is not a clean GIL pass.

| Check | Outcome |
|-------|---------|
| Current GIL, four existing path-sensitive cases | Four pass |
| Current FT, same four cases | Four pass |
| Current GIL, full default suite | 52,388 tests; 2,759 skips; `run=501/509 env_changed=1 skipped=23 resource_denied=9 rerun=1`; exit 3; 13 min 2 sec |
| Current FT, full default suite | 52,306 tests; 2,714 skips; `run=500/509 skipped=21 resource_denied=9`; exit 0; 12 min 34 sec |
| Baseline GIL, isolated multiprocessing module pinned to CPU 32 | 183 tests, 15 skips; exit 0 |
| Current GIL, same pinned module | 183 tests, 15 skips; exit 0 |
| Baseline GIL, same module without affinity restriction | 183 tests, 15 skips; exit 0 |
| Current GIL, same unrestricted module | 183 tests, 15 skips; exit 0 |

The four path cases are listed in [the preceding experiment](../README.md). Configuring fresh debug builds directly from the physical source path makes those cases pass, including the child interpreter that ignores `PYTHONPATH`. Existing optimized binaries and performance data were not replaced or altered. The previous release-suite failures remain recorded separately.

The isolated module does not reproduce the environment leak on either source, with or without pinning. This does not prove the leak harmless, fixed or specific to either source. Full invocation context and timing remain unisolated. A matched full baseline/current GIL comparison was launched after these checks; its results are not included in this completed-evidence set.

## Source, builds and scope

Baseline is `c67363fa59543ef5d572383af927f1cff88514a1`; current is `388fd5bb46fdda6b464db566faf818505c3d6eef`. Both physical source worktrees were checked clean after these runs. The launch parent is `6d66ac3`; the precise revision is retained in `parent-revision.txt`. GCC 11.5 AArch64 builds use `--with-pydebug --with-parallel-gc`, with `--disable-gil` for FT. They are test builds, not optimized measurements. Native decimal, ctypes, SQLite and SSL imports pass; current preflights verify compiled/runtime GIL mode, physical standard-library paths and disabled policy with no helper pool. Full suites start with parallel policy disabled; their existing focused tests can activate it. This is not an always-enabled full suite.

Scratch paths:

- First failed build: `/tmp/parallel-gc-physical-debug-full-20261017-4V11HI/builds/gil`.
- Successful current builds and full runs: `/tmp/parallel-gc-physical-debug-full-retry-20261017-b8yL54/builds/{gil,ft}`.
- Baseline GIL debug build and probes: `/tmp/parallel-gc-baseline-debug-env-probe-20261017-LOc4mJ`.
- Native dependency prefix: `/tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW/deps`.

Current GIL full testing began at 08:52:16 UTC on 17 October. FT began at 09:05:50 UTC; the controller completed at 09:18:24 UTC, returning 1 because GIL was non-green. All three debug binary hashes passed after testing. Version strings still contain `-dirty`; clean source revisions were checked independently, as explained in the [integration status](../../INVESTIGATION-STATUS.md). No CPython source or tests changed, no skip was added, and `--fail-env-changed` remained enabled.

## Reproduction

From the parent repository root, use an empty owned build directory and a physical checkout at the recorded current revision:

```bash
debug_root=$(mktemp -d /tmp/parallel-gc-physical-debug-reproduction-XXXXXX)
bash benchmarks/results/investigations/integration-validation-2026-10-16/local-full-suite/run_physical_debug_suites.sh \
    "$debug_root" \
    /tmp/parallel-gc-benchmarks-20261016-6gpt8U/candidate-source \
    /tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW/deps
```

The helper builds GIL then FT, requires native/runtime/path preflights and all four path tests to pass, and runs the full default command from each build directory:

```bash
./python -m test -q -j2 --timeout=600 \
    --fail-env-changed --rerun --verbose3 --randseed=20260929
```

The isolated module command, from each corresponding GIL debug build directory, is:

```bash
./python -m test test.test_multiprocessing_spawn.test_processes \
    -q -j2 --timeout=600 --fail-env-changed \
    --rerun --verbose3 --randseed=20260929
```

Pinned probes prefix that command with `taskset --cpu-list 32`. Regrtest uses one worker for a one-module selection even when `-j2` is requested. The full selection uses two workers. Do not equate those scopes.

## Preparation failure and helper checks

The first actual build failed in `_uuidmodule.c` because `uuid.h` was not found. The initial helper omitted `PKG_CONFIG_SYSROOT_DIR`, which the optimized build preparation already used. The dependency prefix's uuid pkg-config record then supplied `-I/usr/include/uuid` rather than its relocated include directory. The before/after flags are preserved, including pkg-config's trailing spaces, in `uuid-sysroot-probe.log.gz`. Restoring that build-environment variable, then using a fresh directory, allowed both builds to complete. No source workaround or optional-module exclusion was made. The first failed configure/build logs remain in `first-build-failure/`.

An earlier launcher invocation supplied a not-yet-created build directory and stopped before configuration; the directory was created before the actual first attempt. The helper intentionally requires an existing empty directory. Its shell syntax check passes. Rechecked aliased-source and missing-dependency inputs both return nonzero before creating files; `refusal-checks.log` preserves those results. Successful builds exercised its remaining preflights, full-run exit recording and post-test hash checks.

## Preserved evidence and limits

Complete configure/config/build logs, path checks, selections, preflights, full test logs, four module probes and actual exits are retained. Gzip archives use deterministic compression and decompress byte-for-byte to their scratch originals. `SHA256SUMS` covers the archived files; `ORIGINAL-SHA256SUMS` records decompressed content. No scratch originals were removed.

These local checks do not replace hosted Linux, Windows or macOS evidence. GIL's environment failure still needs investigation. Full pyperformance remains dependency-blocked, and project ABBA's negative measurements remain unresolved. Handoff is not complete.
