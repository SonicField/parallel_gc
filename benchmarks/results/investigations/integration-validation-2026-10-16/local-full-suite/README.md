# Full local CPython regression run and source-path failures

## Scope and current state

Ran both current optimized binaries' full default CPython suite using the Linux workflow's regrtest options, sequentially. Both completed with exit 2, not success. These are local GCC 11.5 AArch64 release builds, not the hosted debug builds or cross-platform CI evidence.

GIL ran from 08:31:22 to 08:39:09 UTC on 17 October. Regrtest reports 7 minutes 46 seconds, 52,149 tests, six failures and 2,777 skips, including rerun accounting. File totals: `run=502/509 failed=2 skipped=29 resource_denied=9 rerun=2`. FT ran from 08:39:09 to the closing controller timestamp 08:47:44 UTC: 8 minutes 35 seconds, 52,250 tests, six failures and 2,782 skips; `run=502/509 failed=2 skipped=27 resource_denied=9 rerun=2`. Both modes fail the same files again on rerun: `test.test_pydoc.test_pydoc` and `test_unittest`. Complete logs are preserved, not passing subsets. Execution session 43276 completed and its controller is gone.

Source is current `388fd5bb46fdda6b464db566faf818505c3d6eef`, parent checkpoint `4545edc`. Binary hashes passed before and after testing in both modes. Native/runtime preflights passed. The full command, from the relevant optimized build directory, is:

```bash
./python -m test -q -j2 \
    --timeout=600 \
    --fail-env-changed \
    --rerun \
    --verbose3 \
    --randseed=20260929
```

Scratch root: `/tmp/parallel-gc-full-local-20261017-MbrhDO`. No collector code or tests were changed, no skip added, and no failure treated as success.

## Falsification experiment: source path spelling

The corrected build root's `baseline-source` and `candidate-source` are symlink aliases to the original clean worktrees under `/tmp/parallel-gc-benchmarks-20261016-6gpt8U`. They are not different source revisions. Both physical worktrees were checked clean; their HEADs are baseline `c67363fa59543ef5d572383af927f1cff88514a1` and current `388fd5bb46fdda6b464db566faf818505c3d6eef`.

The Makefile and raw build-time sysconfig use the alias, but runtime sysconfig canonicalizes `srcdir` to the physical path. The initial standard-library imports use the alias. This supplies a concrete hypothesis for pydoc's standard-library classification failures and unittest's “Path must be within the project” assertion, rather than attributing them to GC.

**Claim tested:** Choosing the physical source-library path fixes all four observed path-sensitive test cases.

Ran the exact same four existing tests on all four optimized binaries, first with the default path and then with `PYTHONPATH` set to the physical source's `Lib`. Every default invocation fails three assertions and one error. Every physical-path invocation fixes the three pydoc cases but still fails the unittest case. This falsifies the claim that a parent-process environment change is a complete repair.

The remaining unittest case explicitly starts `sys.executable -E -m unittest`, ignoring `PYTHONPATH` in that child. Its trace still mixes the physical discovery directory and aliased standard-library support directory. Failures reproduce on baseline and current, in GIL and FT, before collector activation. No source repair or compiler/path change follows automatically from these probes.

The probe command selects these existing cases:

```bash
python -m unittest \
    test.test_pydoc.test_pydoc.PydocDocTest.test_mixed_case_module_names_are_lower_cased \
    test.test_pydoc.test_pydoc.PydocDocTest.test_online_docs_link \
    test.test_pydoc.test_pydoc.TestInternalUtilities.test__get_version \
    test.test_unittest.test_program.TestCommandLineArgs.testSelectedTestNamesFunctionalTest
```

The actual four optimized executables and default/physical probes are recorded in the eight logs, `path-probe-exits.tsv` and [source-paths.json](source-paths.json). Complete default selections and preflight files accompany both full failed logs. Compressed logs decompress byte-for-byte to scratch originals; archive integrity and matching content were checked. No original scratch output was removed. `SHA256SUMS` records the archives; `ORIGINAL-SHA256SUMS` records their decompressed originals.

## What remains

The [physical-source debug follow-up](physical-debug/README.md) makes all four path-sensitive cases pass in both modes without source changes. FT's full default suite passes; the first GIL full run returns `ENV CHANGED` for temporary files left by a multiprocessing module. Isolated baseline/current probes pass with and without CPU pinning. The subsequent [matched full GIL comparison](gil-full-comparison/README.md) passes on both sources. The earlier leak remains unexplained, not repaired. Existing performance binaries and raw data remain untouched. Do not hide the environment failure or rewrite stdlib tests. Genuine hosted CI outcomes and the dependency-blocked full pyperformance comparisons remain independent requirements.
