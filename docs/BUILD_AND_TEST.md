# Build and Test Guide

How to build, configure, and test the parallel garbage collector for CPython.

## Build Configurations

### GIL Build (With Parallel GC)

The standard CPython build with the GIL enabled. Pass `--with-parallel-gc` to enable the parallel garbage collector. This defines `Py_PARALLEL_GC`.

```bash
cd cpython
./configure --with-parallel-gc
make -j$(nproc)
```

### Free Threaded Build (With Parallel GC)

Free Threaded Python (PEP 703) with `--disable-gil`. Pass `--with-parallel-gc` to enable the parallel garbage collector. This build uses a completely separate parallel GC implementation.

```bash
cd cpython
./configure --with-parallel-gc --disable-gil
make -j$(nproc)
```

### Optimised Build (For Benchmarking)

PGO + LTO for maximum performance. Use this for benchmark runs.

```bash
cd cpython
./configure --with-parallel-gc --disable-gil --enable-optimizations --with-lto
make -j$(nproc)
```

**Note:** PGO may fail on `test_sqlite3`. If so, use:

```bash
make -j$(nproc) PROFILE_TASK="-m test --pgo -x test_sqlite3"
```

### Debug Build

For development with assertions enabled:

```bash
cd cpython
./configure --with-parallel-gc --disable-gil --with-pydebug
make -j$(nproc)
```

### Sanitiser Builds

**AddressSanitizer** (requires clang):

```bash
cd cpython
CC=clang ./configure --with-parallel-gc --disable-gil --with-address-sanitizer
make -j$(nproc)
```

**ThreadSanitizer** (requires clang):

```bash
cd cpython
CC=clang ./configure --with-parallel-gc --disable-gil --with-thread-sanitizer
make -j$(nproc)
```

### Switching Between Builds

**Switching between build configurations requires `make distclean`** — object files, generated headers, and `config.status` are incompatible between GIL/FTP and parallel-gc/serial modes:

```bash
make distclean
./configure --with-parallel-gc --disable-gil
make -j$(nproc)
```

Note: `make clean` does not remove `pyconfig.h` or `config.status`. Use `make distclean` when adding or removing `--with-parallel-gc` or `--disable-gil` to ensure a clean configuration.

### Verifying Your Build

Check which build you have:

```bash
# Check if free-threading is enabled
./python -c "import sys; print('FTP' if hasattr(sys, '_is_gil_enabled') and not sys._is_gil_enabled() else 'GIL')"

# Check parallel GC availability
./python -c "import gc; print(gc.get_parallel_config())"

# Check build flags
./python -c "import sysconfig; print(sysconfig.get_config_var('PY_CORE_CFLAGS'))"
```

---

## Test Suites

### Core GC Tests

These must pass in **both** build modes:

```bash
./python -m test test_gc -v
```

### Parallel GC Tests

#### test_gc_parallel (FTP build only)

Comprehensive tests for parallel GC API, enabling/disabling, phase timing, abandoned threads, persistent threads, and mixed scenarios. 35 tests.

```bash
./python -m test test_gc_parallel -v
```

**Test classes:**
- `TestParallelGCAPI` — API existence and return types
- `TestParallelGCEnable` — enable/disable, invalid arguments
- `TestParallelGCBuildConfig` — availability in free-threading
- `TestParallelGCCompatibility` — existing GC still works
- `TestParallelGCPhaseTiming` — phase instrumentation correctness
- `TestAbandonedSerial` / `TestAbandonedParallel` — GC with dead threads
- `TestPersistentThreads` — GC with long-lived threads
- `TestMixedAndConfig` — mixed scenarios, config queries

#### test_gc_ft_parallel (FTP build only)

Tests FTP-specific parallel GC internals: page counting, page assignment, real page enumeration, parallel marking, atomic bit operations, cross-thread references, and concurrent marking. 30 tests.

```bash
./python -m test test_gc_ft_parallel -v
```

**Test classes:**
- `TestPageCounter` — page counting across thread heaps
- `TestPageAssignment` — page-to-bucket distribution
- `TestRealPageEnumeration` — live mimalloc page enumeration
- `TestParallelMarking` — parallel mark correctness
- `TestBasicGCCorrectness` — basic GC with parallel enabled
- `TestCrossThreadReferences` — cross-thread object references
- `TestConcurrentMarking` — concurrent marking correctness

#### test_gc_parallel_mark_alive (GIL build only)

Tests correctness of the mark_alive optimisation — root marking pipeline, known roots preserved, unreachable objects collected, finaliser interaction. Skips on FTP builds. 22 tests.

```bash
./python -m test test_gc_parallel_mark_alive -v
```

**Test classes:**
- `TestBasicCycleCollection` — simple cycles, self-refs, long chains
- `TestKnownRootsPreserved` — sysdict, builtins, module globals
- `TestThreadStacksPreserved` — main thread and other thread locals
- `TestUnreachableCollected` — unreachable cycles, mixed reachable/unreachable
- `TestRaceConditions` — weakref callbacks during collection
- `TestFinalizers` — `__del__` calls, resurrection
- `TestLargeHeaps` — 500K objects, deep nesting
- `TestParallelCorrectness` — shared objects marked once, concurrent allocation
- `TestTypeObjects` — class cycles, orphaned classes
- `TestExtensionModules` — datetime, regex objects
- `TestPerformance` — mark_alive not >30% slower than baseline

#### test_gc_ws_deque

Tests the Chase-Lev work-stealing deque. 11 tests.

```bash
./python -m test test_gc_ws_deque -v
```

**Test classes:**
- `TestWorkStealingDeque` — init/fini, push/take, push/steal, LIFO/FIFO order
- `TestWorkStealingDequeEdgeCases` — empty take/steal, resize, buffer fallback
- `TestWorkStealingDequeConcurrent` — concurrent push/steal (requires fork)

#### test_gc_parallel_properties (FTP build only)

Property-based tests that actively seek counterexamples. 16 tests.

```bash
./python -m test test_gc_parallel_properties -v
```

**Test classes:**
- `TestPropertyCyclicGarbageCollected` — any cyclic garbage is collected (100 iterations)
- `TestPropertyReachableObjectsSurvive` — any reachable object survives (100 iterations)
- `TestPropertyWorkerStatisticsConsistency` — stats sum correctly (2, 4, 8, 16 workers)
- `TestBoundaryValues` — min/max workers, empty/single/two-object collections
- `TestPropertyMixedGarbageAndReachable` — random garbage + reachable (100 iterations)
- `TestPropertyThreadedGarbageCollection` — abandoned/persistent threads (10-20 iterations)

Set `GC_TEST_SEED` to reproduce a specific failure:

```bash
GC_TEST_SEED=12345 ./python -m test test_gc_parallel_properties -v
```

### Running All Tests

```bash
# All parallel GC tests (FTP build)
./python -m test test_gc test_gc_parallel test_gc_ft_parallel test_gc_ws_deque test_gc_parallel_properties -v

# All parallel GC tests (GIL build)
./python -m test test_gc test_gc_parallel_mark_alive test_gc_ws_deque -v

# Full CPython test suite (slow, ~30 min)
./python -m test -j$(nproc)
```

### Test Matrix

Before considering a change complete, run the test suite in both build modes:

| Test | GIL Build | FTP Build |
|------|-----------|-----------|
| test_gc | Must pass | Must pass |
| test_gc_parallel | Skipped (FTP only) | Must pass |
| test_gc_ft_parallel | Skipped (GIL only) | Must pass |
| test_gc_parallel_mark_alive | Must pass | Skipped (GIL only) |
| test_gc_ws_deque | Must pass | Must pass |
| test_gc_parallel_properties | Skipped (FTP only) | Must pass |

---

## Helper Scripts

### tools/run_tests.sh

Quick test runner for development:

```bash
./tools/run_tests.sh [build_config] [test_filter]

# Examples:
./tools/run_tests.sh debug test_gc_parallel
./tools/run_tests.sh release test_gc_parallel_mark_alive
```

Logs to `logs/test_${BUILD_CONFIG}_$(date).log`.

### tools/setup_environment.sh

Initial development environment setup — clones CPython, checks dependencies, creates the `parallel-gc-dev` branch, and builds a serial baseline.

### tools/build_all_configs.sh

Builds all configurations for comprehensive testing:
1. **serial** — baseline
2. **release** — release build
3. **debug** — debug with assertions
4. **asan** — AddressSanitizer (if clang available)
5. **tsan** — ThreadSanitizer (if clang available)

Builds go to `builds/{config}/python`, logs to `logs/build_*.log`.

---

## Common Issues

### `make distclean` required when switching build modes

GIL and FTP builds produce incompatible object files and configuration state. Always run `make distclean` (not just `make clean`) when switching between `--with-parallel-gc` / no flag or `--disable-gil` / GIL modes. `make clean` does not remove `pyconfig.h` or `config.status`, which can retain stale values.

### PGO fails on test_sqlite3

Use `PROFILE_TASK="-m test --pgo -x test_sqlite3"` to skip it during PGO training.

### test_gc_parallel skipped

This test requires a free-threaded build (`--disable-gil`). It correctly skips on GIL builds.

### Assertion failure in PyThreadState_Delete

If you see an assertion about `bound_gilstate` during `gc.disable_parallel()`, ensure the fix at cpython commit `3ca334a` is applied — worker thread states must have `bound_gilstate` cleared before deletion.

### Segfault in test_gc_ft_parallel after test_gc

Fixed in cpython commit `1b47a48`. The test API's `parallel_worker_thread()` spawned bare pthreads without a `PyThreadState`. When ctypes (or any extension whose `tp_traverse` calls `Py_INCREF`) was loaded, the worker thread dereferenced NULL from `_PyThreadState_GET()`. Fix: pre-create thread states before stop-the-world, pass via TLS, clean up on the main thread after restart.

### --with-parallel-gc flag

Pass `--with-parallel-gc` to `./configure` to enable the parallel GC. This defines `Py_PARALLEL_GC` and compiles the parallel collector for both GIL and free-threaded builds. Without this flag, only the serial GC is available. Enable parallel collection at runtime with `gc.enable_parallel(N)`.
