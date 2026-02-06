# TDD Plan: Parallel GC Portability

Each commit is atomic and independently testable. Tests must pass after each step.

---

## Commit 1: Remove dead code from FTP header

**Change:**
- Remove `gc_wait_for_refs_init()` function (lines 394-422)
- Remove `#include <sched.h>` (line 25)

**Test:**
```bash
make -j8 && ./python -m test test_gc test_gc_ft_parallel test_gc_ws_deque -v
```

**Verification:** Function has zero callers (already verified via grep).

**Commit message:**
```
Remove unused gc_wait_for_refs_init() and sched.h include

The function was defined but never called. Removing it eliminates
a POSIX-only dependency (sched_yield) that would need porting.
```

---

## Commit 2: Make num_workers required in gc.enable_parallel()

**Change (gcmodule.c):**
1. Change clinic declaration from `num_workers: int = -1` to `num_workers: int`
2. Remove FTP auto-detect block (lines 522-531)
3. Remove GIL auto-detect block (lines 586-588)
4. Add validation: `if (num_workers < 2) { error }`
5. Regenerate clinic

**Test:**
```bash
make -j8 && ./python -m test test_gc -v
```

**Additional manual test:**
```python
import gc
gc.enable_parallel()  # Should raise TypeError (missing required arg)
gc.enable_parallel(4)  # Should work
gc.enable_parallel(1)  # Should raise ValueError (must be >= 2)
```

**Commit message:**
```
Make num_workers a required parameter for gc.enable_parallel()

Remove auto-detection of worker count. Users must explicitly specify
the number of workers. This eliminates platform-specific CPU count
detection (sysconf) and makes behaviour predictable.
```

---

## Commit 3: Update GIL parallel GC to use PyThread_*

**Changes (gc_parallel.c):**
1. Replace platform includes with `#include "pycore_pythread.h"`
2. Change worker struct: `pthread_t`/`HANDLE` → `PyThread_handle_t`
3. Change thread function signature: `void*` → `void`
4. Replace `pthread_create`/`CreateThread` → `PyThread_start_joinable_thread()`
5. Replace `pthread_join`/`WaitForSingleObject` → `PyThread_join_thread()`

**Changes (pycore_gc_parallel.h):**
1. Remove platform-specific thread handle typedef
2. Use `PyThread_handle_t`

**Test:**
```bash
./configure --with-parallel-gc && make -j8
./python -m test test_gc test_gc_parallel -v
./python -X parallel_gc=4 -c "import gc; print(gc.get_parallel_stats())"
```

**Commit message:**
```
Use CPython thread abstractions in GIL parallel GC

Replace raw pthread/Windows thread APIs with portable PyThread_*
functions. This eliminates platform-specific code paths.

- PyThread_start_joinable_thread() for thread creation
- PyThread_join_thread() for joining
- PyThread_handle_t for thread handles
```

---

## Commit 4: Update FTP parallel GC to use PyThread_*

**Changes (gc_free_threading_parallel.c):**
1. Remove `#include <pthread.h>` (if still present)
2. Add `#include "pycore_pythread.h"`
3. Replace all `pthread_t` → `PyThread_handle_t` (7 locations)
4. Replace all `pthread_create()` → `PyThread_start_joinable_thread()` (6 locations)
5. Replace all `pthread_join()` → `PyThread_join_thread()` (7 locations)
6. Replace `pthread_self()`/`pthread_equal()` → `PyThread_get_thread_ident()` (1 location)
7. Change all thread function signatures: `void*` → `void`

**Changes (pycore_gc_ft_parallel.h):**
1. Remove remaining POSIX includes if any

**Test:**
```bash
./configure --disable-gil && make -j8
./python -m test test_gc test_gc_ft_parallel test_gc_ws_deque -v
./python -c "import gc; gc.enable_parallel(4); print(gc.get_parallel_stats())"
```

**Commit message:**
```
Use CPython thread abstractions in FTP parallel GC

Replace raw pthread APIs with portable PyThread_* functions.
This makes the FTP parallel GC portable to Windows.

- PyThread_start_joinable_thread() for thread creation
- PyThread_join_thread() for joining
- PyThread_handle_t for thread handles
- PyThread_get_thread_ident() for thread identity
```

---

## Commit 5: Add parallel GC files to Windows build

**Changes:**
1. `PCbuild/pythoncore.vcxproj` - Add source files
2. `PCbuild/pythoncore.vcxproj.filters` - Add filter entries
3. `PCbuild/pyproject.props` - Add `Py_PARALLEL_GC` define (if needed)

**Test:** CI will verify Windows build. On Linux, verify files exist:
```bash
grep -l "gc_parallel.c" PCbuild/pythoncore.vcxproj  # Should find it after change
```

**Commit message:**
```
Add parallel GC source files to Windows build

Include gc_parallel.c and gc_free_threading_parallel.c in the
PCbuild project for Windows compilation.
```

---

## Execution Order

```
1. Commit 1 (dead code)     → test on FTP build
2. Commit 2 (required arg)  → test on FTP build
3. Commit 3 (GIL PyThread)  → test on GIL build
4. Commit 4 (FTP PyThread)  → test on FTP build
5. Commit 5 (PCbuild)       → push, let CI test Windows/macOS
```

---

## Test Script

Create `temp_test.sh` for iterative testing:

```bash
#!/bin/bash
set -e

echo "=== Building ==="
make -j8

echo "=== Running GC tests ==="
./python -m test test_gc -v

echo "=== Running parallel GC tests ==="
./python -m test test_gc_ft_parallel test_gc_ws_deque -v

echo "=== Quick functional test ==="
./python -c "
import gc
gc.enable_parallel(4)
stats = gc.get_parallel_stats()
print('Enabled:', stats.get('enabled'))
print('Workers:', stats.get('num_workers'))
gc.collect()
print('Collection succeeded')
"

echo "=== All tests passed ==="
```

---

## Rollback Plan

Each commit is independent. If CI fails on Windows/macOS after push:
1. Identify which commit broke it from CI logs
2. Fix forward with a new commit (preferred)
3. Or revert the specific commit if fix is complex
