# Matched GIL full-suite comparison

## Result

Both baseline and current GIL debug builds passed the full default local CPython suite, without exclusions or relaxing environment checks.

| Source | UTC start/end, 17 October 2026 | Regrtest result |
|--------|------------------------------|-----------------|
| Baseline `c67363fa59543ef5d572383af927f1cff88514a1` | 09:18:34–09:29:43 | Exit 0; 52,202 tests; 2,715 skips; `run=500/509 skipped=23 resource_denied=9`; 11 min 8 sec |
| Current `388fd5bb46fdda6b464db566faf818505c3d6eef` | 09:29:43–09:40:36 | Exit 0; 52,205 tests; 2,723 skips; `run=500/509 skipped=23 resource_denied=9`; 10 min 52 sec |

Neither run reports an environment change or rerun. Both select the exact same 509 test files, preserved in `shared-default-selection.txt`. Resource restrictions and skips remain part of the outcome; this is the default suite, not every optional-resource test.

The [earlier current GIL full run](../physical-debug/README.md) failed its environment check because the multiprocessing spawn process module left three temporary files initially and again on rerun. Four isolated baseline/current module probes passed, with and without CPU pinning. The new full comparison also passes. Therefore the earlier leak was not reproduced here; it is not explained or repaired. Do not discard that failed log or call the leak harmless. One passing full run per source does not establish its frequency or cause.

Current FT's full default debug suite passed in the preceding experiment. Together these provide passing full local debug runs for both current modes, not hosted-platform confirmation or proof that the earlier intermittent GIL failure is resolved.

## Build and execution identity

These are the same fresh GCC 11.5 AArch64 physical-source debug builds described in the [preceding record](../physical-debug/README.md), not rebuilt performance binaries:

- Baseline: `/tmp/parallel-gc-baseline-debug-env-probe-20261017-LOc4mJ`.
- Current: `/tmp/parallel-gc-physical-debug-full-retry-20261017-b8yL54/builds/gil`.

Both use `--with-pydebug --with-parallel-gc` and the same relocated native dependency prefix. Recorded probes verify native decimal, ctypes, SQLite and SSL imports, compiled/runtime GIL mode, debug mode, physical source/stdlib paths, and available but disabled parallel policy with no active helper pool. Both source worktrees were checked clean after testing. Binary hashes passed before and after each full run and again before archiving. Version strings' `-dirty` suffix is not used as the source-cleanliness check; exact revisions are recorded independently.

Run baseline then current sequentially. From each corresponding build directory:

```bash
./python -m test -q -j2 --timeout=600 \
    --fail-env-changed --rerun --verbose3 --randseed=20260929
```

No affinity restriction was added. Both executions use two regrtest workers. Parallel policy is initially disabled; existing collector tests can enable it. This is not an always-enabled full-suite run. No CPython source, test, skip or benchmark changed. The comparison launched before evidence commit `cf7b7f2`; that parent-only commit was made while the tests ran. It did not change either tested source worktree or executable.

The controller completed at 09:40:36 UTC with exit 0. Its execution session was 95982; the launch/controller processes are gone. Timings describe test execution only, not collector performance.

## Evidence and remaining scope

Both complete logs, actual exit files, native/runtime probes, shared selection, source revisions and executable hashes are preserved here. Compressed logs decompress byte-for-byte to scratch originals. `SHA256SUMS` covers archived files; `ORIGINAL-SHA256SUMS` records decompressed log content. Scratch originals remain intact.

The earlier environment leak remains an open observation. Current hosted Linux, Windows and macOS evidence is still unavailable. Full pyperformance requires agreed dependency compatibility work and all sixteen rigorous suites. Project ABBA's negative measurements require follow-up. These local passes do not complete the handoff goal.
