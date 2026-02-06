# Parallel GC Windows/macOS Portability Plan (Revised v2)

**Date:** 2026-01-14
**Revision:** Uses CPython abstractions + removes auto-detect

## Key Insights

1. CPython already has portable threading abstractions - use them
2. Remove auto-detection of worker count - require explicit parameter
3. Remove dead code (`gc_wait_for_refs_init`, `sched_yield`)

---

## Simplifications (Remove Before Porting)

### 1. Remove Dead Code

| File | Code to Remove | Reason |
|------|----------------|--------|
| `pycore_gc_ft_parallel.h:394-422` | `gc_wait_for_refs_init()` | Never called |
| `pycore_gc_ft_parallel.h:25` | `#include <sched.h>` | Only used by dead code |

### 2. Remove Auto-Detect Worker Count

| File | Code to Remove/Change |
|------|----------------------|
| `gcmodule.c:522-528` | Remove `sysconf(_SC_NPROCESSORS_ONLN)` auto-detect |
| `gcmodule.c:479` | Change `num_workers: int = -1` to required parameter |
| `gcmodule.c:586-588` | Remove GIL-side auto-detect fallback |

**New API:**
```python
# Before
gc.enable_parallel()        # Auto-detect (BAD)
gc.enable_parallel(-1)      # Auto-detect (BAD)
gc.enable_parallel(4)       # Explicit (GOOD)

# After
gc.enable_parallel(4)       # Required - must specify
```

This eliminates the need for portable CPU count detection entirely.

---

## CPython Abstractions to Use

### Threading (Include/internal/pycore_pythread.h)

| Raw API | CPython Abstraction |
|---------|---------------------|
| `pthread_create` / `CreateThread` | `PyThread_start_joinable_thread()` |
| `pthread_join` / `WaitForSingleObject` | `PyThread_join_thread()` |
| `pthread_t` / `HANDLE` | `PyThread_handle_t` |
| `pthread_self()` | `PyThread_get_thread_ident()` |

### Already Portable (No Changes Needed)

- `PyMutex`, `_PyRWMutex` - locks
- `_Py_atomic_*` - atomics
- `PyMUTEX_T`, `PyCOND_T` - condition variables
- `_Py_cpu_relax()` - spin-wait hint

---

## Change Matrix

### 1. gcmodule.c - API Changes

**Make num_workers required:**

```c
// Before (line 479)
gc.enable_parallel
    num_workers: int = -1

// After
gc.enable_parallel
    num_workers: int
```

**Remove auto-detect (FTP path, lines 522-531):**
```c
// DELETE THIS:
if (num_workers == -1 || num_workers == 0) {
    long ncpus = sysconf(_SC_NPROCESSORS_ONLN);
    if (ncpus < 1) ncpus = 1;
    actual_workers = (int)(ncpus / 2);
    if (actual_workers < 2) actual_workers = 2;
    if (actual_workers > 8) actual_workers = 8;
} else {
    actual_workers = num_workers;
}

// REPLACE WITH:
if (num_workers < 2) {
    PyErr_SetString(PyExc_ValueError, "num_workers must be >= 2");
    return NULL;
}
int actual_workers = num_workers;
```

**Remove auto-detect (GIL path, lines 586-588):**
```c
// DELETE THIS:
if (num_workers == -1) {
    num_workers = 4;
}

// REPLACE WITH:
if (num_workers < 2) {
    PyErr_SetString(PyExc_ValueError, "num_workers must be >= 2");
    return NULL;
}
```

### 2. pycore_gc_ft_parallel.h - Remove Dead Code

**Remove lines 21-26 (POSIX includes):**
```c
// DELETE:
#ifdef _POSIX_THREADS
#include <pthread.h>
#include <unistd.h>  // sysconf for CPU count
#include <sched.h>   // sched_yield for spin-wait
#endif
```

**Remove lines 394-422 (unused function):**
```c
// DELETE entire gc_wait_for_refs_init() function
```

### 3. gc_parallel.c - Use CPython Threading

**Replace includes (lines 18-23):**
```c
// Before:
#ifdef _POSIX_THREADS
#include <pthread.h>
#include <unistd.h>
#elif defined(NT_THREADS)
#include <windows.h>
#endif

// After:
#include "pycore_pythread.h"
```

**Replace thread creation (lines 644-667):**
```c
// Before:
#ifdef _POSIX_THREADS
        int rc = pthread_create(&worker->thread, NULL,
                               _parallel_gc_worker_thread, worker);
#elif defined(NT_THREADS)
        worker->thread = CreateThread(...);
#endif

// After:
        PyThread_ident_t ident;
        int rc = PyThread_start_joinable_thread(
            _parallel_gc_worker_thread, worker, &ident, &worker->thread);
```

**Replace thread join (lines 703-708):**
```c
// Before:
#ifdef _POSIX_THREADS
        pthread_join(worker->thread, NULL);
#elif defined(NT_THREADS)
        WaitForSingleObject(worker->thread, INFINITE);
        CloseHandle(worker->thread);
#endif

// After:
        PyThread_join_thread(worker->thread);
```

**Change worker struct:**
```c
// Before:
#ifdef _POSIX_THREADS
    pthread_t thread;
#elif defined(NT_THREADS)
    HANDLE thread;
#endif

// After:
    PyThread_handle_t thread;
```

**Change thread function signature:**
```c
// Before:
static void* _parallel_gc_worker_thread(void *arg)
{
    ...
    return NULL;
}

// After:
static void _parallel_gc_worker_thread(void *arg)
{
    ...
    // No return statement
}
```

### 4. gc_free_threading_parallel.c - Use CPython Threading

Same pattern as gc_parallel.c:
- Replace `pthread_t` with `PyThread_handle_t`
- Replace `pthread_create()` with `PyThread_start_joinable_thread()`
- Replace `pthread_join()` with `PyThread_join_thread()`
- Replace `pthread_self()` with `PyThread_get_thread_ident()`
- Change thread function signatures from `void*` to `void`

**Locations:**
- Thread type: lines 774, 854, 1051, 1792, 2310, 2663, 3067
- Thread create: lines 796, 1072, 1841, 2337, 2690, 3092
- Thread join: lines 816, 1090, 1854, 1899, 2354, 2704, 3103
- Thread self: line 1689

### 5. Build System (PCbuild)

| File | Change |
|------|--------|
| `PCbuild/pythoncore.vcxproj` | Add `gc_parallel.c`, `gc_free_threading_parallel.c` |
| `PCbuild/pyproject.props` | Add `Py_PARALLEL_GC` preprocessor define |

---

## Implementation Order

### Phase 1: Simplify (Before Porting)
1. Remove `gc_wait_for_refs_init()` dead code
2. Remove `#include <sched.h>`
3. Make `num_workers` required in `gc.enable_parallel()`
4. Remove auto-detect code
5. **Verify tests pass on Linux**

### Phase 2: Use CPython Abstractions
1. Update `gc_parallel.c` to use `PyThread_*`
2. Update `gc_free_threading_parallel.c` to use `PyThread_*`
3. Update header files
4. **Verify tests pass on Linux**

### Phase 3: Build System
1. Add files to PCbuild
2. Add preprocessor defines
3. **Verify Windows build (if available)**

---

## Revised Effort Estimate

| Component | Estimate |
|-----------|----------|
| Remove dead code & auto-detect | 1 hour |
| GIL parallel GC threading | 2 hours |
| FTP parallel GC threading | 4 hours |
| Build system | 1 hour |
| Testing | 2 hours |
| **Total** | **~10 hours (1.5 days)** |

---

## Files to Modify

```
Modules/gcmodule.c                        # Required num_workers, remove auto-detect
Include/internal/pycore_gc_ft_parallel.h  # Remove dead code
Python/gc_parallel.c                      # Use PyThread_*
Python/gc_free_threading_parallel.c       # Use PyThread_*
Include/internal/pycore_gc_parallel.h     # Change thread handle type
PCbuild/pythoncore.vcxproj                # Add source files
PCbuild/pyproject.props                   # Add Py_PARALLEL_GC
```

---

## What We No Longer Need

By simplifying first:
- ❌ Portable CPU count detection (removed auto-detect)
- ❌ `sched_yield()` / `_Py_yield()` (removed dead code)
- ❌ Platform-specific thread code (use CPython abstractions)

---

## Verification

**Falsifiable claims:**
1. "Dead code can be removed" - verify `gc_wait_for_refs_init` has zero callers ✓
2. "PyThread_* is sufficient" - verify it supports joinable threads ✓
3. "Tests pass after changes" - run test suite after each phase
