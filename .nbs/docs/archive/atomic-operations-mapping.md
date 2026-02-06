# CinderX → CPython Atomic Operations Mapping

Extracted from DEVLOG.md Session 4 (2025-11-28).

Maps C11 atomics used in the CinderX work-stealing deque to CPython's
portable `pyatomic.h` wrappers.

```
CinderX                          → CPython
────────────────────────────────────────────────────
atomic_load_acquire              → _Py_atomic_load_uintptr_acquire
atomic_load_consume              → _Py_atomic_load_ptr_acquire (consume N/A)
atomic_load_relaxed              → _Py_atomic_load_uintptr_relaxed
atomic_store_relaxed             → _Py_atomic_store_uintptr_relaxed
atomic_compare_exchange_strong   → _Py_atomic_compare_exchange_ssize
atomic_thread_fence(seq_cst)     → _Py_atomic_fence_seq_cst
atomic_thread_fence(release)     → _Py_atomic_fence_release
```

## Notes

- `consume` ordering is not available in CPython; `acquire` is used as a
  safe substitute (stronger but portable).
- CPython's atomics are defined in `Include/cpython/pyatomic.h` and
  `Include/cpython/pyatomic_gcc.h` (GCC builtins) /
  `Include/cpython/pyatomic_msc.h` (MSVC intrinsics).
