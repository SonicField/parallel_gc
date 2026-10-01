# Testing Strategy

This document describes the evidence needed for the authoritative `cpython/`
submodule. See [BUILD_AND_TEST.md](BUILD_AND_TEST.md)
for commands and [BENCHMARKING.md](BENCHMARKING.md) for performance work.

## Four-build policy

The GIL and free-threaded collectors are first-class implementations. Every
collector, runtime, shared-primitives, configuration, or public-API change must
be checked in both feature-on out-of-tree debug builds:

- `build-port-gil/`: `--with-pydebug --with-parallel-gc`
- `build-port-ft/`: `--disable-gil --with-pydebug --with-parallel-gc`

The matrix also includes both feature-off controls:

- `build-baseline-gil/`: `--with-pydebug`
- `build-baseline-ft/`: `--disable-gil --with-pydebug`

These serial-GC debug baselines help distinguish upstream behavior from port
regressions, but do not replace either feature-on build.

The `cpython/` submodule records the current fork revision. The root `Makefile`
and scripts under `tools/` target the older project workflow and are not valid
shortcuts for this matrix.

## Verification layers

### Focused functional tests

Run these modules in both parallel builds:

```bash
<build>/python -m test -v \
    test_gc test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_fork test_gc_parallel_properties \
    test_capi.test_config test_embed

# Add these in the free-threaded build:
build-port-ft/python -m test -v \
    test_gc_ft_parallel test_free_threading.test_gc
```

| Test module | Applicable build | Main evidence |
|-------------|------------------|---------------|
| `test_gc` | All four builds | Existing cyclic-GC behavior and integration |
| `test_gc_ws_deque` | All four builds | Shared deque, barrier, and local-buffer primitives |
| `test_gc_parallel` | All four builds | Public API, unavailable-build behavior, configuration, lifecycle, and process/thread scenarios |
| `test_gc_parallel_fork` | POSIX feature-on builds | Parent preservation, child pool replacement and reset, ordinary fork, and finalizer fork |
| `test_gc_ft_parallel` | Free-threaded | End-to-end free-threaded graph and pool behavior |
| `test_gc_parallel_properties` | Both feature-on builds | Deterministic reachability, split-boundary, helper-participation, and threaded properties |
| `test_capi.test_config` | All four builds | Public configuration layout and defaults |
| `test_embed` | All four builds | Embedded-runtime regression coverage |
| `test_free_threading.test_gc` | Free-threaded | Existing free-threaded GC regression coverage |

Build-specific modules skip in the other configuration. Tests may also skip
for unavailable platform facilities. Treat an unexplained skip in the active
mode as a result to investigate.

### Broad CPython suite

Run the broad suite independently in each feature-on, first-class build. This catches
integration failures in areas such as startup, extension traversal, object
lifetime, and threading that focused GC tests may miss.

The `Full CPython test suite` GitHub Actions workflow provides a manual gate
for the authoritative `cpython/` submodule revision. It builds both the GIL and
free-threaded configurations with `--with-parallel-gc`, runs the complete
default regression set without module exclusions, and retains each job's test
log as an artifact. It runs only through `workflow_dispatch`; ordinary pushes
continue to use the faster four-configuration focused matrix.

The broad workflow verifies the supported default state, in which parallel GC
is compiled but not enabled at runtime. The focused matrix separately enables
the collector and exercises its GIL and free-threaded behavior.

To start the workflow in the GitHub UI, open **Actions**, select
**Full CPython test suite**, choose **Run workflow**, select the `main` branch,
and confirm **Run workflow**.

Alternatively, trigger it from the command line after pushing the parent
repository commit:

```bash
gh workflow run full-cpython-tests.yml \
    --repo SonicField/parallel_gc \
    --ref main
```

Find the resulting run and follow it to completion with:

```bash
gh run list \
    --repo SonicField/parallel_gc \
    --workflow full-cpython-tests.yml \
    --limit 1

gh run watch RUN_ID \
    --repo SonicField/parallel_gc \
    --exit-status
```

Missing optional dependencies and the known upstream multiprocessing issue
must be recorded, not silently converted into a clean result.
Use these exact broad-suite command shapes on the current host:

```bash
build-port-gil/python -m test -q -j4 \
    --timeout=300 --fail-env-changed --randseed=20260929 \
    -x test_cext test_multiprocessing_fork \
       test_multiprocessing_forkserver test_multiprocessing_spawn

build-port-ft/python -m test -q -j4 \
    --timeout=300 --fail-env-changed --randseed=20260929 \
    -x test_cext test_free_threading test_multiprocessing_fork \
       test_multiprocessing_forkserver test_multiprocessing_spawn
```

The exclusion reasons are recorded in [BUILD_AND_TEST.md](BUILD_AND_TEST.md).

Historical broad status from predecessor commit `9da963f754`:

- The free-threaded broad active run passed 47,914 tests across 481 files,
  including `test_external_inspection`.
- The GIL broad active run passed 48,103 tests across 483 files, including
  `test_capi`, `test_pickle`, and `test_external_inspection`.
- Focused feature-off controls passed 203 tests in the GIL build and 211 tests
  in the free-threaded build.

Test counts are snapshots rather than a contract. Always retain the runner's
summary, seed, failures, skips, and exact command.

At `92f992042c`, a fresh optimized free-threaded build completed its PGO
training suite (9,724 tests) and passed the focused selection with 194 tests
and 33 expected skips. The broad GIL and free-threaded results above must be
repeated before they can be attributed to the current revision.

### Sanitizers

At an earlier recorded development state, AddressSanitizer builds passed
213 affected-area GIL tests and 229 affected-area free-threaded tests with leak
detection disabled and no sanitizer diagnostics. These results must be tied to
a published commit for submission.

The exact affected-area commands are:

```bash
ASAN_OPTIONS=detect_leaks=0 \
    build-port-gil-asan/python -m test -j4 --timeout=180 \
    test_gc test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_fork test_gc_parallel_properties \
    test_capi.test_config test_embed

ASAN_OPTIONS=detect_leaks=0 \
    build-port-ft-asan/python -m test -j4 --timeout=180 \
    test_gc test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_fork test_gc_parallel_properties \
    test_capi.test_config test_embed \
    test_gc_ft_parallel test_free_threading.test_gc
```

ThreadSanitizer is currently blocked by the absence of `libtsan`. This is a
verification gap, not a pass. Once the runtime is available, run the same
focused suite against separate GIL and free-threaded TSan builds.

The same focused suites pass debug reference-leak checks with `-R 3:3` in both
feature-on builds: 213 tests in the GIL build and 229 tests in the
free-threaded build, with no positive leaked references or memory blocks.

For every sanitizer run, record:

- CPython commit and working-tree state;
- compiler and sanitizer versions;
- configure flags and build directory;
- exact test command and seed;
- expected skips and complete sanitizer output.

### Configure regeneration

The checked-in `configure` and `pyconfig.h.in` were regenerated with CPython's
pinned Autoconf container. A second canonical regeneration was byte-identical,
and CPython's generated-file CI check passed on the predecessor fork revision.
Any later configure-input change requires the same canonical regeneration.

### Performance

Concurrency and collector changes require controlled benchmark comparison in
addition to functional and sanitizer evidence. Follow
[BENCHMARKING.md](BENCHMARKING.md) and record hardware, commits, configure
flags, worker counts, seeds, warmups, samples, and raw results.

## Evidence required by change type

| Change | Required evidence |
|--------|-------------------|
| Documentation only | Link, command, and consistency review |
| Test-only change | Focused tests in every applicable build |
| Build-system change | All four GIL/free-threaded, feature-on/feature-off builds plus focused tests |
| Collector or concurrency change | Both parallel builds, focused and broad suites, both-mode sanitizers, and benchmarks |
| Public API change | Both parallel builds, focused API tests, broad suites, documentation, and compatibility rationale |
| Submission candidate | Current dual-build functional results, both-mode sanitizer evidence, reproducible benchmarks, and explicit limitations |

## Open verification gaps

- ThreadSanitizer cannot run until `libtsan` is available.
- The parent CI enforces all four GIL/free-threaded and
  feature-on/feature-off configurations on Ubuntu.
- Native feature-on Linux x86-64, Windows, and macOS validation has not been
  run. The standard feature-off CPython workflow has passed on the fork.
