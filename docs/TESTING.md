# Testing Strategy

This document describes the evidence needed for the authoritative `cpython/`
submodule. See [GETTING_STARTED.md](GETTING_STARTED.md)
for commands and [PERFORMANCE.md](PERFORMANCE.md) for performance work.

The parent revision's `cpython/` gitlink selects the source to test.
[VALIDATION.md](VALIDATION.md) records local evidence, older CI, required new
runs and the source pair attached to each result. Do not infer current remote
success from a predecessor run or a branch name. The
[repository README](../README.md) gives the reading path and
[DESIGN.md](DESIGN.md) explains the collectors.

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
    test_gc test_gc_ft_parallel test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_fork test_gc_parallel_properties \
    test_capi.test_config test_embed

# Add these in the free-threaded build:
build-port-ft/python -m test -v \
    test_free_threading.test_gc

# Add this in the GIL feature-on build:
build-port-gil/python -m test -v test_gc_parallel_mark_alive

# PGO workload tests apply to both build modes:
<build>/python -m test -v test_parallel_gc_profile
```

| Test module | Applicable build | Main evidence |
|-------------|------------------|---------------|
| `test_gc` | All four builds | Existing cyclic-GC behavior and integration |
| `test_gc_ws_deque` | All four builds | Shared deque, barrier, and local-buffer primitives |
| `test_gc_parallel` | All four builds | Public API, unavailable-build behavior, configuration, lifecycle, and process/thread scenarios |
| `test_gc_parallel_fork` | POSIX feature-on builds | Parent preservation; armed child recovery without thread creation; reset; ordinary, callback, and finalizer forks |
| `test_gc_ft_parallel` | All four builds | GIL and FT lazy-pool lifecycle and injected startup failures; free-threaded graph and pool behavior; explicit feature-off skips |
| `test_gc_parallel_properties` | Both feature-on builds | Deterministic reachability, split-boundary, helper-participation, and threaded properties |
| `test_gc_parallel_mark_alive` | GIL feature-on | Known-root marking, deque drainage and deterministic dispatch integration |
| `test_parallel_gc_profile` | GIL and FT | Supplementary PGO workload and expected collector participation |
| `test_capi.test_config` | All four builds | Public configuration layout and defaults |
| `test_embed` | All four builds | Embedded-runtime regression coverage |
| `test_free_threading.test_gc` | Free-threaded | Existing free-threaded GC regression coverage |

Build-specific modules skip in the other configuration. Tests may also skip
for unavailable platform facilities. Treat an unexplained skip in the active
mode as a result to investigate.

### Focused compiler warnings

The `Parallel GC compiler warnings` workflow compiles the four GC objects in
fresh out-of-tree GIL/FT release/debug configurations with both GCC and Clang.
It applies `-Werror=unused-function -Werror=unused-variable` only to these
object targets, not the full interpreter build. This catches unreferenced
out-of-line helpers and variables; it does not detect every unused inline
helper or typedef and does not replace tests, sanitizers or platform builds.
Compiler versions, configure output, diagnostics and source-pair records are
retained even when a job fails. The existing focused/full workflows continue
to run runtime tests independently.

It runs on pushes and pull requests. To request another run manually:

```bash
gh workflow run parallel-gc-warnings.yml \
    --repo SonicField/parallel_gc \
    --ref main
```

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

CI uses a ten-minute per-test-file timeout because
`test_gc_parallel_mark_alive` deliberately constructs and repeatedly collects
large graphs in a debug build. The timeout remains a bounded deadlock detector;
the workload is not reduced for slower runners.

The full workflows use CPython's standard evidence-preserving rerun mode. An
initial failure is printed and retained in the uploaded log, then the failed
test is rerun verbosely. This is necessary for current upstream intermittent
tests rather than a parallel-GC exception. In particular,
`test_external_inspection.test_tlbc_cache_refresh_after_growth` reproduced its
transient remote-memory read failure locally in both feature-on and feature-off
free-threaded builds.

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

### macOS matrix and full-suite gate

The manual `macOS parallel GC` workflow uses CPython's current macOS runner
label and `Misc/Brewfile`, with the same Homebrew OpenSSL and gdbm configure
setup as its upstream macOS workflow. It runs GIL and FT feature-on and
feature-off debug builds. All four run focused collector and parent benchmark
harness tests; both feature-on builds also run the full default CPython suite.
Full-suite runtime policy starts disabled, as on Linux and Windows. Each job
retains source-pair evidence and any test logs produced before a failure.
The first hosted result is pending; local syntax checks are not portability
evidence.

After pushing the parent commit, trigger it with:

```bash
HTTPS_PROXY=http://fwdproxy:8080 \
HTTP_PROXY=http://fwdproxy:8080 \
gh workflow run macos-parallel-gc.yml \
    --repo SonicField/parallel_gc \
    --ref main
```

Use `gh run list --workflow macos-parallel-gc.yml` and `gh run watch RUN_ID`
with `--repo SonicField/parallel_gc` and the proxy environment above to follow
the run. All platform workflows retain a `ci-source.txt` artifact identifying
the parent/source pair, runner architecture, run attempt and requested flags.
[VALIDATION.md](VALIDATION.md) is the outcome record.

The shared source-record action has local fixture tests, independent of a
CPython build:

```bash
python3 .github/actions/record-source/test_record_source.py -v
```

These check matching and mismatched revisions and dirty tracked CPython source
in temporary repositories. They do not exercise GitHub artifact upload.

### Windows feature-on gate

The `Windows parallel GC` workflow is a manual portability and regression gate.
It builds 64-bit debug CPython with parallel GC enabled in both GIL and
free-threaded modes, verifies that the expected runtime is active, performs an
immediate eligible collection after GIL activation, runs the focused GC tests and parent
benchmark-harness unit tests, and then runs the complete default CPython
regression suite without module exclusions. Each full-suite log is retained as
an artifact. It deliberately starts with x64; Windows ARM64 is the next stage
after the x64 workflow is green. Parallel GC does not support 32-bit targets.

As on Linux, the focused tests explicitly activate parallel GC. The full
CPython suite verifies the supported default runtime state, in which the
feature is compiled in but is not automatically enabled.

Trigger and follow the workflow with:

```bash
gh workflow run windows-parallel-gc.yml \
    --repo SonicField/parallel_gc \
    --ref main

gh run list \
    --repo SonicField/parallel_gc \
    --workflow windows-parallel-gc.yml \
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

The exclusion reasons are recorded in [GETTING_STARTED.md](GETTING_STARTED.md).

Historical broad status from predecessor commit `9da963f754`:

- The free-threaded broad active run passed 47,914 tests across 481 files,
  including `test_external_inspection`.

- The GIL broad active run passed 48,103 tests across 483 files, including
  `test_capi`, `test_pickle`, and `test_external_inspection`.
- Focused feature-off controls passed 203 tests in the GIL build and 211 tests
  in the free-threaded build.

Current GIL lazy-start commit `7ec0874a7d` passed the documented local broad
command: 48,224 tests across 486 files, with 3,518 skips and no failures. The
four exclusions are the dependency-sensitive tests described above; a prior
unexcluded diagnostic reproduced their existing `_ctypes`/ensurepip failures
and the upstream multiprocessing `Value` `NameError`. The unchanged
free-threaded build passed its documented broad command with 48,041 tests
across 484 files, 3,507 skips, and no failures.

GitHub run `37615218042` checked parent revision `45462b0` and CPython revision
`d396f837b9`. All four builds and affected-area selections passed. All four
jobs then failed in the benchmark-harness step because the clean runner did
not contain the pinned `pyperf` dependency. The same command reproduced two
`ModuleNotFoundError` failures locally; installing the pinned pyperformance
requirements in isolated GIL and free-threaded user sites changed both results
to 40 passing tests.
Runs `37615265794` and `37615268403` passed the full Linux and Windows GIL and
free-threaded suites at those older revisions. None of these three runs tests
GIL lazy-pool revision `7ec0874a7d`.

CPython lint run `37655164456` failed because Ruff removed one extra blank
line from `Tools/build/parallel_gc_profile.py`. Ruff 0.15.17 reproduced the
same one-line diff locally and passed after the deletion. The repair is
CPython revision `8eb4af7dbf`; it does not change executable behavior.

Parent matrix run `37655285492` exposed a stochastic adaptive-controller test
that compared the final worker counts of two workloads. Instrumentation showed
that neither workload reached the GIL collector's parallel threshold in a
clean process: both made zero parallel collection attempts and left the worker
count at four. Its result therefore depended on unrelated heap state and could
not establish adaptation. CPython revision `669ed6b17e` replaces that claim
with deterministic controller tests for accept, reject, persistence, bounds,
reset, and invalid measurements; lifecycle tests for enable and re-enable;
and an integration test that verifies every generated collection crosses the
threshold, dispatches parallel work, remains in bounds, and advances the
controller. Timing and workload-optimality claims were removed from the unit
suite and remain benchmark questions.

At `669ed6b17e`, all three affected modules passed in GIL and free-threaded
debug builds: 154 tests with 58 skips in GIL and 119 tests with 22 skips in
free-threaded. The same modules passed under AddressSanitizer in both builds.
The five new or changed GIL tests also passed under ThreadSanitizer without a
diagnostic. A feature-off GIL build compiled the changed internal test module.

The amended local matrix selection explicitly ran `test_gc_ft_parallel` in
all four configurations. The GIL feature-on build ran all 17 lazy lifecycle
and startup-failure tests; the GIL feature-off build skipped those 17 tests
because the feature was unavailable. The complete focused selections passed:
658 tests with 72 skips for GIL feature-on, 614 with 107 skips for GIL
feature-off, 685 with 46 skips for free-threaded feature-on, and 679 with 142
skips for free-threaded feature-off. The GIL builds were fresh builds of
`7ec0874a7d`; the existing free-threaded binaries were `d396f837b9` and
`3459fbefd8`, so the free-threaded runs verify the broadened test selection but
are not current-revision rebuilds. GitHub confirmation of the amended matrix
at one parent and submodule revision remains outstanding.

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
    test_gc test_gc_ft_parallel test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_fork test_gc_parallel_properties \
    test_capi.test_config test_embed

ASAN_OPTIONS=detect_leaks=0 \
    build-port-ft-asan/python -m test -j4 --timeout=180 \
    test_gc test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_fork test_gc_parallel_properties \
    test_capi.test_config test_embed \
    test_gc_ft_parallel test_free_threading.test_gc
```

The GIL build at CPython revision `7ec0874a7d` passed the focused
ThreadSanitizer selection with 222 tests and 59 expected skips. No
ThreadSanitizer diagnostic was emitted. The build used GCC 11.5.0 on AArch64
and was configured with:

```bash
../cpython/configure \
    --with-pydebug \
    --with-parallel-gc \
    --with-thread-sanitizer
```

The focused command was:

```bash
TSAN_OPTIONS='halt_on_error=1 die_after_fork=0 suppressions=cpython/Tools/tsan/suppressions.txt handle_segv=0' \
    build-lazy-gil-tsan/python -m test -v \
    test_gc \
    test_gc_ft_parallel \
    test_gc_parallel_mark_alive \
    test_gc_parallel_fork \
    test_gc_ws_deque
```

GCC ThreadSanitizer requires `die_after_fork=0` for these fork tests because a
later child collection intentionally creates a new helper pool.

The free-threaded lazy-pool implementation at CPython revision `195830171f`
passed `test_gc_ft_parallel`, `test_gc_parallel_fork`, `test_gc_ws_deque`, and
`test_free_threading.test_gc` under GCC 11.5.0 ThreadSanitizer on AArch64: 155
tests run, 25 expected skips, and no ThreadSanitizer diagnostic. Its configure
flags were `--disable-gil --with-pydebug --with-parallel-gc
--with-thread-sanitizer`. `LIBRARY_PATH` and the executable rpath selected the
locally extracted GCC runtime because this host's linker script points at an
unavailable system path.

Earlier focused suites passed debug reference-leak checks with `-R 3:3` in both
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
[PERFORMANCE.md](PERFORMANCE.md) and record hardware, commits, configure
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

- Local GIL and FT ThreadSanitizer selections pass. Collection-phase allocation
  injection and wider race coverage remain incomplete.
- The parent CI enforces all four GIL/free-threaded and
  feature-on/feature-off configurations on Ubuntu.
- Native feature-on Linux x86-64 focused validation runs in the parent matrix.
- Windows x64 feature-on full runs passed at the older `d396f837b9` checkpoint;
  current FT lifecycle repeats and Windows ARM64 remain pending.
- Native feature-on macOS validation has not been run. The standard feature-off
  CPython workflow has passed on the fork.
