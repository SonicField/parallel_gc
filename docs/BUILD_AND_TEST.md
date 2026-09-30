# Build and Test Guide

The active port is the checked-in `cpython/` submodule at
`SonicField/cpython` commit `323d3cc90adcc5dcc799f79812edd339b347a46c`.
The root `Makefile` and scripts under `tools/` target the older project workflow
and must not be cited as current-port build or test evidence.

Run the commands below from the outer `parallel_gc/` repository. Install the
normal CPython build dependencies first; missing optional modules produce the
usual CPython skips. See [GETTING_STARTED.md](GETTING_STARTED.md) for the
parent-repository checkout layout.

## Build matrix

GIL and free-threaded builds are both first-class configurations. A change is
not ready for review merely because it works in one of them.

The current implementation requires a 64-bit target and either POSIX or
Windows threads. Native validation has so far been performed only on Linux
AArch64.

| Directory | Configuration | Purpose |
|-----------|---------------|---------|
| `build-port-gil/` | `--with-pydebug --with-parallel-gc` | Parallel collector with the GIL |
| `build-port-ft/` | `--disable-gil --with-pydebug --with-parallel-gc` | Free-threaded parallel collector |
| `build-baseline-gil/` | `--with-pydebug` | GIL feature-off baseline |
| `build-baseline-ft/` | `--disable-gil --with-pydebug` | Free-threaded feature-off baseline |

Create or refresh the builds out of tree:

```bash
mkdir -p build-port-gil build-port-ft \
    build-baseline-gil build-baseline-ft

(cd build-port-gil && \
    ../cpython/configure --with-pydebug --with-parallel-gc)
make -C build-port-gil -j"$(nproc)"

(cd build-port-ft && \
    ../cpython/configure \
        --disable-gil --with-pydebug --with-parallel-gc)
make -C build-port-ft -j"$(nproc)"

(cd build-baseline-gil && \
    ../cpython/configure --with-pydebug)
make -C build-baseline-gil -j"$(nproc)"

(cd build-baseline-ft && \
    ../cpython/configure --disable-gil --with-pydebug)
make -C build-baseline-ft -j"$(nproc)"
```

Before changing configure options in an existing build directory, run
`make -C <build-directory> distclean`. Do not share object files between the
four configurations.

The generated `cpython/configure` and `cpython/pyconfig.h.in` were regenerated
with CPython's pinned Autoconf container. A second canonical regeneration
produced byte-identical files. Their Git blob IDs also match the files produced
by CPython's `regen-configure` CI job for the preceding fork revision.

## Continuous integration

The parent repository's `parallel-gc.yml` workflow builds and tests all four
configurations above on Ubuntu. The feature-on jobs set
`PYTHON_PARALLEL_GC=4`; the controls compile without `--with-parallel-gc` and
verify that the runtime reports the feature as unavailable. Both GIL modes run
the common affected-area tests, and both free-threaded modes additionally run
the relevant free-threading tests.

This project workflow complements CPython's standard workflow. The standard
workflow provides broad platform and configuration coverage but normally
builds with parallel GC disabled; it is not evidence that either active
collector was exercised.

## Focused tests

Run the common focused set in both parallel builds:

```bash
PYTHON_PARALLEL_GC=4 build-port-gil/python -m test -v \
    test_gc test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_properties test_capi.test_config test_embed

PYTHON_PARALLEL_GC=4 build-port-ft/python -m test -v \
    test_gc test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_properties test_capi.test_config test_embed \
    test_gc_ft_parallel test_free_threading.test_gc
```

Tests for the other build mode skip at module or class level. Unexpected skips
in the active mode should be investigated.

Run both feature-off controls when a result may come from the port rather than
the parallel collector itself:

```bash
build-baseline-gil/python -m test -v \
    test_gc test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_properties test_capi.test_config test_embed

build-baseline-ft/python -m test -v \
    test_gc test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_properties test_capi.test_config test_embed \
    test_free_threading.test_gc
```

These feature-off tests also verify that nonzero startup requests through
`-X parallel_gc`, `PYTHON_PARALLEL_GC`, and `PyConfig.parallel_gc_workers` are
rejected. A zero value remains valid and leaves the collector disabled.

## Broad regression runs

Run the CPython suite separately in both feature-on, first-class builds. A
representative command is:

```bash
PYTHON_PARALLEL_GC=4 build-port-gil/python -m test -q -j4 \
    --timeout=300 --fail-env-changed --randseed=20260929 \
    -x test_cext test_multiprocessing_fork \
       test_multiprocessing_forkserver test_multiprocessing_spawn

PYTHON_PARALLEL_GC=4 build-port-ft/python -m test -q -j4 \
    --timeout=300 --fail-env-changed --randseed=20260929 \
    -x test_cext test_free_threading test_multiprocessing_fork \
       test_multiprocessing_forkserver test_multiprocessing_spawn
```

Preserve the complete command, random seed, summary, failures, and skips for
each run. Missing optional dependencies and the known upstream multiprocessing
issue are environmental results, not parallel-GC regressions, but should
remain visible in the record.
`test_cext` requires unavailable build dependencies. The three multiprocessing
modules hit an upstream `NameError` reproduced by the feature-off build. The
free-threaded `test_free_threading` umbrella package imports the unavailable
optional `_ctypes` module. Individual tests may still report ordinary resource
or dependency skips; retain those in the test log.

### Current validation status

The affected-area matrix on the current fork commit passes in all four debug
configurations:

- Parallel GIL: 540 tests run, 17 skipped, 7 files passed.
- Parallel free-threaded: 557 tests run, 24 skipped, 9 files passed.
- Feature-off GIL: 529 tests run, 30 skipped, 7 files passed, 1 file skipped.
- Feature-off free-threaded: 539 tests run, 36 skipped, 8 files passed,
  1 file skipped.

Parent workflow run `36631372624` reproduced this four-configuration matrix on
Ubuntu 26.04 and passed every job. Standard CPython workflow run `36631682622`
also passed: 43 jobs succeeded and 2 inapplicable jobs were skipped. That run
includes generated-file checks, Autoconf regeneration, Linux, Windows, macOS,
Android, iOS, WASI, Emscripten, and sanitizer configurations. The standard
workflow builds parallel GC disabled, so it is cross-platform compatibility
evidence rather than active-collector coverage.

The broader results below were recorded on predecessor commit `9da963f754`.
Subsequent changes are limited to generated configuration files,
cross-platform test-harness behavior, and safe reporting of object assertions
from GIL collector helpers. The broad suites must nevertheless be rerun before
these numbers can be attributed to the current fork commit.

- Free-threaded: 47,914 tests passed across 481 files, including
  `test_external_inspection`.
- GIL: 48,103 tests passed across 483 files, including `test_capi`,
  `test_pickle`, and `test_external_inspection`.
- Feature-off focused controls: 203 tests in the GIL build and 211 tests in
  the free-threaded build.

These results are snapshots rather than permanent guarantees. Rerun every
affected configuration after collector, runtime, configuration, or
shared-concurrency changes.

## Sanitizers

At the currently recorded development state, AddressSanitizer builds passed
213 affected-area GIL tests and 229 affected-area free-threaded tests with leak
detection disabled and no sanitizer diagnostics.

Use separate out-of-tree directories and preserve configure and test commands,
for example:

```bash
mkdir -p build-port-gil-asan build-port-ft-asan

(cd build-port-gil-asan && \
    CC=clang CXX=clang++ ../cpython/configure \
        --with-pydebug --with-parallel-gc --with-address-sanitizer)
make -C build-port-gil-asan -j"$(nproc)"

(cd build-port-ft-asan && \
    CC=clang CXX=clang++ ../cpython/configure \
        --disable-gil --with-pydebug --with-parallel-gc \
        --with-address-sanitizer)
make -C build-port-ft-asan -j"$(nproc)"
```

Run the affected-area tests with leak detection disabled:

```bash
ASAN_OPTIONS=detect_leaks=0 PYTHON_PARALLEL_GC=4 \
    build-port-gil-asan/python -m test -j4 --timeout=180 \
    test_gc test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_properties test_capi.test_config test_embed

ASAN_OPTIONS=detect_leaks=0 PYTHON_PARALLEL_GC=4 \
    build-port-ft-asan/python -m test -j4 --timeout=180 \
    test_gc test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_properties test_capi.test_config test_embed \
    test_gc_ft_parallel test_free_threading.test_gc
```

ThreadSanitizer is currently blocked because `libtsan` is unavailable in the
environment; no TSan pass should be claimed until that runtime is installed
and both build modes have been exercised.

The focused commands above also pass debug reference-leak checks with
`-R 3:3`: 213 tests in the GIL build and 229 tests in the free-threaded build,
with no positive leaked references or memory blocks.
