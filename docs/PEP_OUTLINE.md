# PEP XXXX -- Parallel Garbage Collection for CPython

## Preamble

```
PEP: XXXX
Title: Parallel Garbage Collection for CPython
Author: Alex Turner
Status: Draft
Type: Standards Track
Requires: PEP 703 (for free-threaded build variant)
Python-Version: 3.15
Created: TBD
```

---

## Abstract

- Propose adding **optional parallel garbage collection** to CPython's cyclic garbage collector.
- Two implementations: one for GIL-enabled builds (`gc_parallel.c`), one for free-threaded builds (`gc_free_threading_parallel.c`).
- Parallelises the mark phase using persistent worker thread pools, work-stealing deques, and atomic marking operations.
- Opt-in via `gc.enable_parallel(num_workers=N)` — serial collection remains the default.
- Sweet spot: heaps with **500K+ tracked objects**; typical collection speedup **1.2–2.3x** with 8 workers depending on heap topology. STW pause reduction **54–67%** on realistic workloads.
- No changes to the public `gc` module API semantics; no changes to reference counting behaviour.

---

## Motivation

- **GC pause times scale linearly with heap size.** CPython's cyclic GC is single-threaded. At 1M+ tracked objects, full-generation collections take hundreds of milliseconds.
- **AI/ML workloads are disproportionately affected.** Training loops create millions of tensor wrappers, autograd graph nodes, and intermediate objects. Users call `gc.collect()` manually at GPU synchronisation points. All CPU cores are idle during GC while the GPU computes.
- **Free-threaded Python amplifies the problem.** Without the GIL, applications create more objects across more threads. GC pauses during stop-the-world become a scaling bottleneck.
- **Modern hardware has idle cores during GC.** Single-threaded GC wastes available parallelism on machines with 8–128 cores.
- **Existing mitigations are insufficient:**
  - `gc.disable()` risks unbounded memory growth from reference cycles.
  - Generational collection reduces frequency but not worst-case pause duration for full collections.
  - Incremental GC (CPython 3.12+) reduces pause latency but does not reduce total GC work for manual `gc.collect()`.

---

## Rationale

### Why parallel marking?

- The **mark phase dominates GC cost** for large heaps. `update_refs`, `subtract_refs`, and `move_unreachable` all walk the object graph; these are the phases worth parallelising.
- Marking is **embarrassingly parallel** on wide/layered object graphs: independent subtrees can be traversed by different workers without coordination.
- Finalisation and deallocation are **inherently serial** in CPython (weak reference callbacks, `__del__` methods, `tp_clear`). Attempting to parallelise cleanup was investigated and rejected (see Rejected Alternatives).

### Why this approach?

- **Persistent thread pool**: Workers are created once at `gc.enable_parallel()` and reused across collections. Avoids per-collection thread creation overhead.
- **Work-stealing deques (Chase-Lev)**: Each worker has a local deque for discovered objects. When a worker's deque empties, it steals from others. Provides automatic load balancing with low contention.
- **Atomic marking via fetch-and / fetch-or**: Single atomic instruction to claim an object for traversal. No CAS retry loops. Combined with a relaxed-load check-first optimisation to skip already-marked objects cheaply.
- **Local work buffers**: 1024-item thread-local buffer between `tp_traverse` callbacks and the deque. Push/pop with zero memory fences; deque only touched on overflow/underflow.
- **Barrier synchronisation**: Workers synchronise via barriers between GC phases, not fine-grained locking. Correct termination is guaranteed.
- **Serial fallback**: If parallel GC is not enabled, or the heap is too small, the existing serial collector runs unchanged.

### Why two implementations?

- **GIL build** (`gc_parallel.c`): Uses `_gc_prev` COLLECTING bit for marking. Split vector recorded during serial `update_refs` for work distribution. Phases: `update_refs` (serial) → `mark_alive` (parallel) → `subtract_refs` (parallel) → `mark` (parallel) → sweep (serial).
- **Free-threaded build** (`gc_free_threading_parallel.c`): Uses `ob_gc_bits` for marking. Page-based distribution via mimalloc internals. Phases: `update_refs` (parallel) → `mark_alive` (parallel) → `mark_heap` (parallel) → `scan_heap` (parallel). All phases parallelised because the world is already stopped.

---

## Specification

### Python API

```python
import gc

# Enable parallel GC with N worker threads
gc.enable_parallel(num_workers=4)

# Disable parallel GC (reverts to serial)
gc.disable_parallel()

# Query configuration
config = gc.get_parallel_config()
# Returns: {'available': True, 'enabled': True, 'num_workers': 4}

# Query statistics (for profiling/debugging)
stats = gc.get_parallel_stats()
# Returns dict with per-worker and per-phase timing data
```

### C API (internal, underscore-prefixed)

- `_PyGC_ParallelInit(interp, num_workers)` — Allocate parallel GC state.
- `_PyGC_ParallelStart(interp)` — Start worker threads.
- `_PyGC_ParallelStop(interp)` — Stop worker threads (join).
- `_PyGC_ParallelFini(interp)` — Deallocate parallel GC state.
- `_PyGC_ParallelIsEnabled(interp)` — Query enabled state.
- `_PyGC_ParallelSetEnabled(interp, flag)` — Enable/disable at runtime.
- `_PyGC_ParallelMoveUnreachable(interp, young, unreachable)` — Parallel mark + sweep.
- `_PyGC_ParallelSubtractRefs(interp, base)` — Parallel reference subtraction.
- `_PyGC_ParallelMarkAliveFromRoots(interp, containers)` — Parallel root marking (work-stealing variant).
- `_PyGC_ParallelMarkAliveFromQueue(interp, containers)` — Parallel root marking (producer-consumer variant).

FTP build has equivalent pool-based API functions via `_PyGC_ThreadPool*` and `_PyGC_Parallel*WithPool`.

### Build configuration

- GIL build: `Py_PARALLEL_GC` defined when `--with-parallel-gc` is passed to configure. Requires 64-bit platform.
- FTP build: `Py_PARALLEL_GC` defined when `--with-parallel-gc` is passed to configure (in addition to `--disable-gil`). Configured at runtime.

### Thresholds and fallback behaviour

- Parallel GC is **opt-in** — disabled by default.
- When enabled, the collector falls back to serial if:
  - `num_workers_active == 0` (workers not started).
  - Split vector has fewer than 2 entries (heap too small for meaningful partitioning).
  - Worker allocation or thread creation fails.
- Recommended minimum heap size for benefit: **500,000 tracked objects** (based on empirical benchmarks).
- Maximum worker threads: `_PyGC_MAX_WORKERS = 1024`.

### Worker thread lifecycle

- Workers are OS threads created via `PyThread_start_joinable_thread`.
- Each worker creates a `PyThreadState` (required for `Py_REF_DEBUG` in debug builds and for `tp_traverse` callbacks that call `Py_INCREF`).
- Worker thread states are cleaned up by the main thread after `join` to avoid race conditions with re-initialisation.
- Workers park on a barrier between collections (no spinning, no polling).

### Memory overhead

- Per-worker: 2 MB pre-allocated deque buffer (256K pointer entries).
- Per-collection: split vector grows dynamically (8 bytes per 8192 objects ≈ 1 KB per million objects).
- Work queue (GIL build, producer-consumer variant): 8 pre-allocated blocks of 4096 pointers (256 KB), growable.

---

## Backwards Compatibility

- **No public API breakage.** `gc.collect()`, `gc.get_stats()`, `gc.callbacks`, `gc.freeze()`, `gc.unfreeze()` — all unchanged.
- **Serial fallback is always available.** If `gc.enable_parallel()` is never called, behaviour is identical to upstream CPython.
- **No change to collection semantics.** The same objects are collected in the same order. Weak reference callbacks and `__del__` methods are called from the main thread in the same serial phase.
- **No change to generational thresholds.** Parallel GC only affects how the mark phase executes within a collection, not when collections are triggered.
- **Environment variable and command-line flag**: `PYTHONPARALLELGC=N` and `-X parallel_gc=N` enable parallel GC at startup. These are convenience wrappers for `gc.enable_parallel(N)`.
- **`tp_traverse` contract unchanged.** Extension modules' `tp_traverse` callbacks are called by worker threads, but the GIL is held (GIL build) or the world is stopped (FTP build), so existing callbacks remain safe.

---

## Security Implications

### Thread safety

- **Atomic operations for marking.** All object marking uses atomic fetch-and/fetch-or instructions (single instruction, no retry loops). Race conditions on marking are benign: worst case is duplicate traversal, never missed traversal.
- **ARM memory ordering.** Acquire fences after successful mark operations ensure workers see consistent object field values before traversal. Validated on aarch64.
- **Worker thread states** are managed by the main thread to avoid race conditions during creation and cleanup.
- **No new lock ordering constraints.** Workers do not acquire the GIL or any interpreter locks. Barriers are the sole synchronisation mechanism.

### Memory safety

- **Pre-allocated buffers** reduce allocation during GC, avoiding allocator re-entrancy.
- **Bounds checking** on worker indices and split vector access.
- **Debug-build postconditions** verify list linkage integrity after parallel operations.

### Denial of service

- `gc.enable_parallel(num_workers=1024)` allocates ~2 GB of deque buffers. This is a resource consumption concern, but no worse than `threading.Thread` creation. Could add a lower cap if desired.

---

## Performance Impact

### When parallel GC helps

| Heap size | Workers | Typical speedup | Notes |
|-----------|---------|----------------|-------|
| 1M objects | 8 | 1.2–2.3x | FTP build, PGO+LTO, collection time |
| Realistic workload | 8 | -54% to -67% STW | Throughput neutral, major pause reduction |
| Synthetic throughput | 8 | +31% geomean | Sustained workload improvement |

### When parallel GC does not help

- **Heaps <100K objects**: Overhead exceeds benefit (0.5–0.9x).
- **Linear chain or binary tree topologies**: Limited parallelism in graph structure.
- **Very short-lived collections** (automatic gen-0/gen-1): Overhead of barrier synchronisation dominates.

### Overhead of enabled-but-idle parallel GC

- **1-worker parallel vs serial**: ±3% (within noise). Infrastructure overhead is negligible when enabled but running with a single worker.

### Benchmark data (GIL build)

| Configuration | Serial (ms) | Parallel 4W (ms) | Speedup |
|--------------|-------------|-------------------|---------|
| independent_500k_s80 | 242 | 175 | 1.29x |
| independent_1M_s80 | 642 | 458 | 1.36x |
| wide_tree_500k_s80 | 299 | 223 | 1.38x |
| wide_tree_1M_s80 | 748 | 662 | 1.15x |

### Benchmark data (FTP build, all phases parallel)

| Configuration | Serial (ms) | Parallel (ms) | Speedup |
|--------------|-------------|---------------|---------|
| independent_1M_s80_w8 | 503 | 150 | 3.35x |
| layered_1M_s80_w16 | 1571 | 328 | 4.78x |
| wide_tree_1M_s80_w8 | 464 | 182 | 2.55x |
| graph_1M_s80_w8 | 677 | 244 | 2.78x |

### AI/ML workload simulation

| Tensors | Total objects | Serial (ms) | Parallel (ms) | Speedup |
|---------|--------------|-------------|---------------|---------|
| 50K | 300K | 96.92 | 76.03 | 1.27x |
| 200K | 1.2M | 518.82 | 391.08 | 1.33x |

---

## Rejected Alternatives

### 1. Parallel cleanup / deallocation workers (FTP)

- **Attempted**: Parallelise the deallocation phase using `cleanup_workers=N`.
- **Result**: 13x slowdown due to contention on biased reference counting (BRC) bucket mutexes. When multiple workers decref objects owned by a concentrated set of threads, the BRC queues serialise. Atomic CAS loops on `ob_ref_shared` exhibit severe cache-line contention (80.73% of time spent on `lock xaddq`).
- **Conclusion**: Deallocation in FTP is fundamentally serial due to BRC ownership semantics.

### 2. BRC sharding to reduce cleanup contention

- **Attempted**: Shard BRC buckets by decrefing thread ID.
- **Result**: Insufficient. Reduces queueing contention but the deeper bottleneck (atomic CAS on `ob_ref_shared`) remains. Abandoned as incomplete solution.

### 3. Fast decref optimisation (Py_BRC_FAST_DECREF)

- **Attempted**: Use atomic ADD instead of CAS loop for non-queued decrefs.
- **Result**: No measurable benefit in realistic workloads. Cache-line contention remains the bottleneck regardless of instruction choice. Code removed.

### 4. Work-stealing for root propagation (GIL build)

- **Attempted**: Distribute ~100 interpreter roots to worker deques and use work-stealing.
- **Result**: Hub-structured root graph causes severe imbalance: first worker marks most of the heap before others can steal. Replaced with **pipelined producer-consumer** design: main thread expands roots by one level (thousands of level-1 children) and workers claim batches from a shared queue.

### 5. Multi-threaded delete phase (FTP)

- **Attempted**: Run `tp_clear` / deallocation across multiple workers.
- **Result**: Mimalloc inter-thread communication cost too high. Objects must be returned to their owning thread's heap, causing cross-thread traffic that negates parallelism gains.

### 6. CAS-based atomic marking

- **Attempted**: Use compare-and-swap loops for object marking.
- **Result**: Under contention, CAS retry loops waste cycles. Replaced with single-instruction **fetch-and** (GIL build) and **fetch-or** (FTP build) operations. No retry loop needed — the old value tells us whether we won the race.

### 7. Ad-hoc thread creation per collection

- **Attempted**: Spawn fresh threads for each GC collection.
- **Result**: Thread creation overhead (typically 50–200 µs per thread on Linux) is significant relative to collection time for moderate heaps. Replaced with **persistent thread pool**: threads created once, parked on barriers between collections.

---

## Reference Implementation

- **Repository**: [link to PR — to be added]
- **Key files (GIL build)**:
  - `Python/gc_parallel.c` — parallel mark, subtract_refs, mark_alive
  - `Include/internal/pycore_gc_parallel.h` — data structures, API
  - `Include/internal/pycore_ws_deque.h` — Chase-Lev work-stealing deque
  - `Include/internal/pycore_gc_barrier.h` — barrier synchronisation
- **Key files (FTP build)**:
  - `Python/gc_free_threading_parallel.c` — page-based parallel GC
  - `Include/internal/pycore_gc_ft_parallel.h` — data structures, API
- **Key files (shared)**:
  - `Modules/gcmodule.c` — Python-level `gc.enable_parallel()` / `gc.disable_parallel()`
  - `Lib/test/test_gc_parallel.py` — FTP end-to-end tests
  - `Lib/test/test_gc_parallel_mark_alive.py` — GIL root marking tests
  - `Lib/test/test_gc_ft_parallel.py` — FTP internal tests
  - `Lib/test/test_gc_ws_deque.py` — Chase-Lev deque tests
  - `Lib/test/test_gc_parallel_properties.py` — property-based tests

---

## Open Issues

- **Default threshold**: Should parallel GC auto-enable above a certain heap size, or remain strictly opt-in?
- **Worker count default**: Should `num_workers` default to `os.cpu_count() // 2` or require explicit specification?
- **Interaction with subinterpreters**: Each interpreter has its own parallel GC state. No cross-interpreter sharing of workers.
- **Windows support**: Relies on `PyThread_start_joinable_thread` (available since 3.12). Needs CI validation on Windows.

---

## Copyright

This document is placed in the public domain or under the CC0-1.0-Universal licence, at the option of the reader.
