# Corrected optimized-build evidence

Baseline source: `c67363fa59543ef5d572383af927f1cff88514a1`.
Candidate source: `388fd5bb46fdda6b464db566faf818505c3d6eef`.

Four fresh out-of-tree GCC 11.5.0 AArch64 builds use `--with-parallel-gc --enable-optimizations --with-lto`; FT also uses `--disable-gil`. The native dependency prefix belongs to this campaign. No source tree, collector logic or benchmark parameters changed during the builds.

The corrected root's source paths are symlink aliases to the original clean worktrees under `/tmp/parallel-gc-benchmarks-20261016-6gpt8U`; they are not separately copied source trees or different revisions. Later [full local tests](../local-full-suite/README.md) expose alias/physical path sensitivity in pydoc and unittest discovery. The original source identities, executable hashes and performance records are retained; the failed tests are not masked or recast as collector failures.

Each build directory contains:

- `preflight.json`: native decimal identity, libmpdec version, compiled configuration and runtime GIL/FT mode after importing dependencies. The preflight also requires the collector to be available and initially disabled.
- `build-tests.txt`: six-file build selection, including decimal and parallel profile tests.
- `collector-tests.txt`: supplementary collector, C-API, configuration and embedding tests. GIL includes the mark-alive tests; FT includes free-threaded GC tests. Neither selection is the complete CPython suite.
- `parent-tests.txt`: all 67 tests across the four parent benchmark-harness modules, using an isolated test virtual environment with bundled pip 26.2.1 and pyperf 2.10.0.
- `binary.sha256`: executable hash recorded after build tests and verified again after supplementary tests and before measurement.
- `parallel-profile-check.txt`: post-build training-workload check, which fails if the parallel path was not used.
- `profile-use-evidence.txt`: build-log line recording the actual parallel PGO task, an actual profile-use/LTO compiler command, and the full build log's SHA-256. Complete build logs remain under `/tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW`.

The `-dirty` runtime version label is preserved. The investigation explains why the build-directory git invocation generates it despite clean tracked source worktrees. It must not be read as proof of modified collector source.

Both FT collector logs preserve the existing expected failure for shared extension-module state in subinterpreters. All four complete supplementary selections report success. Original failed dependency-setup attempts are retained in the scratch directory and explained in the investigation; they are not collector test failures and are not hidden by the passing reruns.

This evidence establishes the local optimized-build and selected-test prerequisites. It does not establish completed ABBA, performance neutrality, full CPython coverage or current Linux/Windows/macOS CI results.
