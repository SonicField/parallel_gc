# Parallel GC Windows/macOS Portability Report

**Generated:** 2025-01-14
**Analysed by:** 6 parallel Opus agents

## Executive Summary

The parallel GC implementation is **well-prepared for portability**. The GIL-based parallel GC (`gc_parallel.c`) already has Windows threading abstractions in place. The FTP parallel GC needs more work. The main gaps are in:

1. **FTP threading** - Uses raw pthreads without Windows equivalents
2. **Build system** - MSBuild/PCbuild files need updates
3. **CPU detection** - `sysconf()` needs Windows equivalent
4. **Test suite** - One test uses `requires_fork()`, ANSI colours need fixing

**macOS requires no changes** - it's POSIX-compliant.

---

## Priority Matrix

### BLOCKING (Won't compile on Windows)

| Issue | File | Fix Required | Effort |
|-------|------|--------------|--------|
| Missing source files in PCbuild | pythoncore.vcxproj | Add gc_parallel.c, gc_free_threading_parallel.c | 1 hour |
| Missing Py_PARALLEL_GC define | pyproject.props | Add preprocessor definition | 30 min |
| pthread_t in FTP header | pycore_gc_ft_parallel.h | Add HANDLE abstraction | 2 hours |
| sysconf() CPU count | gcmodule.c, pycore_gc_ft_parallel.h | Use GetSystemInfo | 1 hour |
| sched_yield() | pycore_gc_ft_parallel.h | Use SwitchToThread | 30 min |
| pthread.h in test | test_ws_deque.c | Use PyThread or #ifdef | 2 hours |

### HIGH (Will crash or fail at runtime)

| Issue | File | Fix Required | Effort |
|-------|------|--------------|--------|
| FTP pthread_create (6 sites) | gc_free_threading_parallel.c | Add CreateThread paths | 4 hours |
| FTP pthread_join (6 sites) | gc_free_threading_parallel.c | Add WaitForSingleObject | 2 hours |
| pthread_self/equal pattern | gc_free_threading_parallel.c | Alternative worker ID approach | 2 hours |

### MEDIUM (Suboptimal or partial functionality)

| Issue | File | Fix Required | Effort |
|-------|------|--------------|--------|
| GIL thread function signature | gc_parallel.c | Add DWORD wrapper | 1 hour |
| pthread_cancel usage | gc_free_threading_parallel.c | Use cooperative shutdown | 2 hours |
| Cache line size | pycore_ws_deque.h | Add ARM64 128-byte case | 30 min |
| Vista+ requirement | pycore_gc_barrier.h | Document or add XP fallback | 2 hours |
| Missing headers in PCbuild | pythoncore.vcxproj | Add .h files | 30 min |

### LOW (Cosmetic or documentation)

| Issue | File | Fix Required | Effort |
|-------|------|--------------|--------|
| ANSI colours in benchmark | gc_benchmark.py | Add Windows detection | 30 min |
| requires_fork() in test | test_gc_ws_deque.py | Change to requires_threading | 30 min |
| Documentation | configure.rst | Add --with-parallel-gc docs | 1 hour |
| .vcxproj.filters | pythoncore.vcxproj.filters | Add filter entries | 15 min |

---

## What Already Works

### GIL Parallel GC (gc_parallel.c)
- Thread creation/join with Windows `CreateThread`/`WaitForSingleObject`
- Thread handle type (`pthread_t`/`HANDLE`)
- Barrier sync with `SRWLOCK`/`CONDITION_VARIABLE`
- CPU relax with `_mm_pause()`/`__yield()`
- Prefetch with `_mm_prefetch()`
- All atomic operations via `_Py_atomic_*`

### Shared Infrastructure
- Work-stealing deque (pycore_ws_deque.h) - fully portable
- Barrier (pycore_gc_barrier.h) - fully portable
- Memory fences - portable via CPython atomics

### Test Suite (mostly)
- test_gc_parallel.py - fully portable
- test_gc_ft_parallel.py - fully portable
- test_gc_parallel_mark_alive.py - fully portable

---

## Detailed Findings by Component

### 1. GIL Parallel GC Core
**Agent finding:** "Remarkably well-prepared for Windows portability"

Already implemented:
- `#ifdef _POSIX_THREADS` / `#elif defined(NT_THREADS)` guards
- Platform-specific thread creation
- Platform-specific thread handles
- Portable atomics throughout

Minor fixes needed:
- Thread function returns `void*` but Windows expects `DWORD`
- Vista+ documented requirement for SRWLOCK

### 2. FTP Parallel GC Core
**Agent finding:** "Heavily POSIX-centric, needs substantial work"

Missing Windows paths for:
- 6x `pthread_create()` calls
- 6x `pthread_join()` calls
- `pthread_self()`/`pthread_equal()` pattern
- `sched_yield()` spin-wait
- `sysconf(_SC_NPROCESSORS_ONLN)` CPU count

Estimated effort: 2-3 days focused work

### 3. Shared Infrastructure
**Agent finding:** "LOW RISK - well abstracted"

- pycore_ws_deque.h: All portable
- pycore_gc_barrier.h: Already has Windows SRWLOCK path
- test_ws_deque.c: BLOCKING - uses raw pthreads

### 4. Build System
**Agent finding:** "Main gaps are in Windows MSBuild"

Required for Windows:
1. Add source files to pythoncore.vcxproj
2. Add Py_PARALLEL_GC preprocessor define
3. Add UseParallelGC build option
4. Update PC/pyconfig.h

macOS: No changes (uses autoconf)

### 5. Python API
**Agent finding:** "API layer is correct, underlying impl needs fixes"

The Python-facing API is properly guarded:
```c
#ifdef Py_GIL_DISABLED
    // FTP path
#elif defined(Py_PARALLEL_GC)
    // GIL path
#else
    // Not available
#endif
```

### 6. Test Suite
**Agent finding:** "Substantially portable with two specific issues"

Issues:
1. `test_gc_ws_deque.py` uses `requires_fork()` - skipped on Windows
2. `gc_benchmark.py` ANSI colours - garbled on Windows

All other tests will pass on Windows/macOS.

---

## Recommended Porting Order

### Phase 1: GIL Parallel GC on Windows (1-2 days)
1. Add source/header files to PCbuild
2. Add Py_PARALLEL_GC preprocessor define
3. Fix thread function signature (DWORD wrapper)
4. Test and verify

### Phase 2: FTP Parallel GC on Windows (2-3 days)
1. Create thread handle abstraction type
2. Create portable thread creation/join wrappers
3. Add GetSystemInfo for CPU count
4. Add SwitchToThread for yield
5. Update all 12 threading call sites
6. Test and verify

### Phase 3: Test Suite (1 day)
1. Port test_ws_deque.c to Windows threads
2. Change requires_fork() to requires_working_threading()
3. Add ANSI colour detection to benchmark
4. Run full test suite on Windows

### Phase 4: Documentation (0.5 days)
1. Document --with-parallel-gc in configure.rst
2. Update README with Windows build instructions
3. Document Vista+ requirement

---

## macOS Status

**No changes required.** macOS is POSIX-compliant and all existing code works.

Verified:
- pthread APIs supported
- sysconf() supported
- sched_yield() supported
- All tests pass

---

## Total Estimated Effort

| Platform | GIL Parallel GC | FTP Parallel GC | Tests | Docs | Total |
|----------|-----------------|-----------------|-------|------|-------|
| Windows | 1-2 days | 2-3 days | 1 day | 0.5 days | **4-6.5 days** |
| macOS | 0 | 0 | 0 | 0 | **0 days** |

---

## Files Requiring Changes

### Windows Only

```
PCbuild/pythoncore.vcxproj          # Add sources
PCbuild/pythoncore.vcxproj.filters  # Add filters
PCbuild/pyproject.props             # Add Py_PARALLEL_GC
PCbuild/python.props                # Add UseParallelGC option
PC/pyconfig.h                       # Add Py_PARALLEL_GC handling
```

### Cross-Platform C Code

```
Python/gc_parallel.c                # Minor: DWORD wrapper
Python/gc_free_threading_parallel.c # Major: All threading
Include/internal/pycore_gc_ft_parallel.h  # pthread_t abstraction
Include/internal/pycore_ws_deque.h  # Minor: cache line size
Modules/gcmodule.c                  # sysconf -> GetSystemInfo
Modules/_testinternalcapi/test_ws_deque.c  # pthread -> portable
```

### Python Test Code

```
Lib/test/test_gc_ws_deque.py       # requires_fork -> requires_threading
Lib/test/gc_benchmark.py           # ANSI colour detection
```

### Documentation

```
Doc/using/configure.rst            # Add --with-parallel-gc
```
