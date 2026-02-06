# Cleanup Plan: Remove BRC/DECREF Optimizations and cw1+

## Date: 2026-01-20

## Summary

Remove three features that showed no benefit in realistic benchmarks:
1. **cw1+ (cleanup workers)** - parallel cleanup showed no improvement
2. **BRC sharding** - adds overhead without measurable benefit
3. **Fast decref** - same issue

Keep: Parallel GC scanning (proven 21% throughput improvement)

---

## Files to Modify

### 1. Remove cw1+ (Cleanup Workers)

**File: `Python/gc_free_threading_parallel.c`**
- Remove `cleanup_workers` parameter handling
- Remove async cleanup worker thread infrastructure
- Remove TID-based sorting (was added for cw optimization)
- Keep serial cleanup (cw0 behaviour)
- Simplify `cleanup_unreachable_parallel()` to always do serial cleanup

**File: `Lib/test/gc_throughput_benchmark.py`**
- Remove `--cleanup-workers` argument
- Remove cw comparison logic

**File: `Lib/test/gc_realistic_benchmark.py`**
- Remove `--cleanup-workers` argument
- Remove cw comparison logic

### 2. Remove BRC Sharding

**File: `Include/internal/pycore_brc.h`**
- Remove `#define Py_BRC_SHARDED 1`
- Remove `#define _Py_BRC_NUM_SHARDS 11`
- Remove `struct _brc_shard`
- Remove sharded `struct _brc_bucket` (keep non-sharded version)
- Remove sharded `struct _brc_thread_state` (keep non-sharded version)

**File: `Python/brc.c`**
- Remove all `#ifdef Py_BRC_SHARDED` blocks
- Keep only the `#else` (non-sharded) implementation

### 3. Remove Fast Decref

**File: `Include/internal/pycore_brc.h`**
- Remove `#define Py_BRC_FAST_DECREF 1`

**File: `Objects/object.c`**
- Remove `#if Py_BRC_FAST_DECREF` block in `_Py_DecRefSharedIsDead()`
- Keep only the CAS loop path (the "slow path" which is now the only path)

---

## Verification Steps

1. Build: `make clean && make -j`
2. Basic test: `./python -c "print('OK')"`
3. GC test: `./python -m test test_gc`
4. Benchmark: Verify parallel GC still provides speedup

---

## Order of Operations

1. Remove fast decref (smallest change)
2. Remove BRC sharding (medium change)
3. Remove cw1+ (largest change)
4. Clean up benchmarks
5. Verify and commit

---

## Expected Outcome

- Simpler codebase
- Parallel GC still provides 21% throughput improvement
- No measurable performance regression (already verified)
