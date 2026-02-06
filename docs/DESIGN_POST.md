# Designing a Parallel Garbage Collector for CPython

**TL;DR**: We built parallel garbage collectors for both GIL and Free Threaded CPython. The GIL build uses a multi-phase architecture (mark_alive, subtract_refs, mark, sweep) with split-vector work distribution and Fetch-And atomic marking. The Free Threaded build uses page-based work distribution over mimalloc pages with relaxed-atomic marking on `ob_gc_bits`. Both builds share a Chase-Lev work-stealing deque and a portable barrier implementation. On heaps with 1M+ objects, collection speedups of 1.2--2.3x are achieved with 8 workers.

---

## Scope and Build Configurations

### GIL Python (Default Build)

The primary parallel GC targets **GIL-based CPython**. The GIL provides a critical simplification: application code is paused during collection, so parallel workers only race with each other, not with the application.

Parallel GC is opt-in via `./configure --with-parallel-gc` (guarded by `#ifdef Py_PARALLEL_GC`). The same flag enables parallel GC for both GIL and free-threaded builds.

### Free Threaded Python (PEP 703)

A second, fully independent parallel GC targets **Free Threaded Python** (`--disable-gil`). This build removes the GIL, enabling true multi-threaded execution, but collection still runs during a stop-the-world pause. The collector uses a different architecture suited to Free Threaded Python's memory layout (mimalloc pages, `ob_gc_bits` marking, `ob_tid`-based gc_refs). See the [Free Threaded Python section](#free-threaded-python-parallel-gc) below.

```
Build configuration:
  --disable-gil           Free Threaded Python (uses separate parallel GC)
```

The FTP implementation is guarded by `#if defined(Py_GIL_DISABLED) && defined(Py_PARALLEL_GC)`.

---

## Design Heritage: CinderX

This implementation is ported from [CinderX](https://github.com/facebookincubator/cinder), Meta's performance-oriented fork of CPython. CinderX introduced parallel GC to accelerate Instagram's Python workloads.

While the core data structures (Chase-Lev deque, barrier synchronisation) originate in CinderX, the algorithm has evolved substantially. The current implementation is a multi-phase collector with per-phase work distribution strategies, rather than the simple work-stealing mark-sweep described in the original CinderX port.

---

## GIL Build: Multi-Phase Architecture

The GIL parallel collector runs within `deduce_unreachable()` and proceeds through four parallel phases, each with its own work distribution strategy.

### Phase 1: mark_alive (Interpreter Root Pre-Marking)

**Purpose**: Pre-mark objects reachable from interpreter roots (sysdict, builtins, thread stacks, type dicts) before the main GC cycle. This reduces the work in subsequent phases, since objects marked alive here are skipped by both subtract_refs and mark.

**Two distribution strategies** are available, selected at the call site:

1. **Work-stealing from roots** (`_PyGC_ParallelMarkAliveFromRoots`): Interpreter roots are distributed round-robin to worker deques. Workers traverse subgraphs and steal from each other using coordinator-based termination.

2. **Pipelined producer-consumer** (`_PyGC_ParallelMarkAliveFromQueue`): The main thread expands interpreter roots by one level (via `tp_traverse`), pushing level-1 children to a shared work queue. Workers claim batches from the queue using atomic CAS and traverse subtrees locally. This addresses a work distribution problem: ~100 interpreter roots form a hub, and the first worker in a naive work-stealing scheme marks most of the heap before others can steal. Level-1 expansion provides thousands of distributed starting points instead.

### Phase 2: subtract_refs (Parallel Reference Count Decrement)

**Purpose**: Decrement gc_refs for internal references. For each object in the collection set, call `tp_traverse` with a visitor that atomically decrements gc_refs of referenced objects.

**Distribution**: Uses the **split vector**, a growable array of pointers into the GC list recorded during the serial `update_refs` phase at 8192-object intervals (`_PyGC_SPLIT_INTERVAL`). Workers are assigned ranges of split vector entries, giving each worker a contiguous segment of roughly `total_objects / num_workers` objects.

```c
// During update_refs, record waypoints every 8192 objects:
#define _PyGC_SPLIT_INTERVAL 8192

// Workers get ranges of split vector entries, not raw object indices.
// For 1M objects, this gives ~122 waypoints divided among N workers.
worker->slice_start = splits->entries[start_idx];
worker->slice_end   = splits->entries[end_idx];
```

Atomic decrement is necessary because references can cross segment boundaries -- multiple workers may decrement the same object's gc_refs simultaneously:

```c
static inline void
gc_decref_atomic(PyGC_Head *gc)
{
    _Py_atomic_add_uintptr(&gc->_gc_prev,
                           -((uintptr_t)1 << _PyGC_PREV_SHIFT));
}
```

### Phase 3: mark (Parallel Root Discovery and Local Marking)

**Purpose**: Find GC roots (objects with gc_refs > 0 after subtract_refs) and mark their subgraphs as reachable.

**Distribution**: Uses the same split vector segments as subtract_refs. Each worker scans its segment for roots, marks them, and traverses subgraphs **locally** -- there is no work-stealing between workers in this phase.

```c
// Simplified Local-Only Marking (no work-stealing)
// Workers scan their segment, find roots, mark locally.
// No stealing from other workers - just process own buffer and deque.
//
// This is sufficient because mark_alive already covered interpreter roots,
// so gc_roots_found ~ 0 and any residual work is small.
```

This simplification is safe because Phase 1 (mark_alive) already marked the vast majority of reachable objects from interpreter roots. The mark phase handles only residual GC roots (objects with external references not reachable from interpreter roots), which are typically few.

### Phase 4: Sweep (Serial)

After parallel marking, the main thread sweeps the GC list single-threaded. Objects with the COLLECTING flag still set are unreachable; they are moved to the unreachable list. Reachable objects have their `_gc_prev` restored as doubly-linked list pointers.

The entry point for the entire parallel marking pipeline is `_PyGC_ParallelMoveUnreachable()`, called from `deduce_unreachable()` in `gc.c`.

---

## Atomic Marking: Fetch-And

Objects are marked as reachable by atomically clearing the `COLLECTING` flag in `_gc_prev`. We use **Fetch-And** (atomic AND) rather than compare-and-swap (CAS):

```c
static inline int
gc_try_mark_reachable_atomic(PyGC_Head *gc)
{
    // Fast path: check if already marked (relaxed load -- very cheap)
    uintptr_t prev = _Py_atomic_load_uintptr_relaxed(&gc->_gc_prev);
    if (!(prev & _PyGC_PREV_MASK_COLLECTING)) {
        return 0;  // Already marked by another worker
    }

    // Slow path: atomically clear the COLLECTING bit
    // Fetch-And always succeeds in one operation (no retry loop)
    uintptr_t old_prev = _Py_atomic_and_uintptr(
        &gc->_gc_prev, ~_PyGC_PREV_MASK_COLLECTING);

    // If old value had COLLECTING set, we successfully claimed this object
    int marked = (old_prev & _PyGC_PREV_MASK_COLLECTING) != 0;

    // ARM: acquire fence after successful mark ensures we see
    // consistent field values before traversal
    if (marked) {
        _Py_atomic_fence_acquire();
    }

    return marked;
}
```

Fetch-And is superior to CAS here because:

- It **always succeeds** in one atomic operation (no retry loop under contention).
- The old value tells us whether we were the worker that cleared the bit.
- Combined with a **check-first relaxed load**, shared objects (types, builtins, modules) that are already marked are handled with a ~10x cheaper relaxed load instead of an atomic read-modify-write.

---

## Chase-Lev Work-Stealing Deque

The heart of the parallel infrastructure is the Chase-Lev work-stealing deque, as described in:

- ["Dynamic Circular Work-Stealing Deque"](https://dl.acm.org/doi/10.1145/1073970.1073974) (Chase & Lev, 2005)
- ["Correct and Efficient Work-Stealing for Weak Memory Models"](https://dl.acm.org/doi/10.1145/2442516.2442524) (Le et al., 2013)

Each worker has a local deque:
- **Owner operations** (push/take from bottom): Lock-free, LIFO for cache locality
- **Steal operations** (take from top): Lock-free CAS, FIFO for fairness

```c
// Worker pushes discovered objects to local deque
_PyWSDeque_Push(&worker->deque, child_object);

// Worker takes from own deque (fast path)
PyObject *obj = _PyWSDeque_Take(&worker->deque);

// When local deque empty, steal from others
PyObject *stolen = _PyWSDeque_Steal(&other_worker->deque);
```

### Local Buffer Optimisation

Workers use a small local buffer (`_PyGCLocalBuffer`) as a staging area between `tp_traverse` callbacks and the deque. Pushes and pops to the local buffer require zero memory fences (just array indexing). The buffer is flushed to the deque only when full, amortising the cost of deque operations.

### Coordinator-Based Termination

The mark_alive phase uses coordinator-based termination for correct work-stealing shutdown. When a worker exhausts its local work and fails to steal:

1. It attempts to become the **coordinator** (via mutex-protected election).
2. The coordinator polls all deques. If work exists, it wakes idle workers via a counting semaphore.
3. Termination: when the coordinator is the only active worker and all deques are empty, it wakes all waiters to exit.

This avoids false termination (exiting while work remains in other deques) and wasted spins (idle workers sleep instead of spinning).

---

## Divergence from CinderX

While the core data structures originate in CinderX, we made several adaptations:

### 1. Atomic Abstractions

CinderX uses raw C11 atomics. We use CPython's portable atomic wrappers:

| CinderX | CPython |
|---------|---------|
| `atomic_load_explicit(..., relaxed)` | `_Py_atomic_load_uintptr_relaxed()` |
| `atomic_fetch_and()` | `_Py_atomic_and_uintptr()` |
| `atomic_thread_fence()` | `_Py_atomic_fence_acquire()` |

### 2. Barrier Synchronisation

CinderX uses a custom barrier implementation. We implemented barriers using CPython's `PyMUTEX_T` and `PyCOND_T` primitives, defined in a **shared header** (`pycore_gc_barrier.h`) used by both GIL and FTP builds:

```c
typedef struct {
    unsigned int num_left;
    unsigned int capacity;
    unsigned int epoch;  // Disambiguates spurious wakeups
    PyMUTEX_T lock;
    PyCOND_T cond;
} _PyGCBarrier;
```

### 3. Thread Lifecycle

Our implementation:

- Creates worker threads when `gc.enable_parallel(N)` is called
- Destroys threads when `gc.disable_parallel()` is called
- Workers wait at a barrier between collections (no busy-waiting)

### 4. Build System Integration

Parallel GC is opt-in via `./configure --with-parallel-gc`. This defines `Py_PARALLEL_GC` for both GIL and free-threaded builds.

---

## Optimisations Beyond CinderX

### 1. Thread-Local Memory Pools

**Problem**: Each collection called `calloc()` to allocate deque backing arrays, creating allocator contention and cache pollution.

**Solution**: Pre-allocate 2MB memory pools per worker at `gc.enable_parallel()` time:

```c
// 256K entries = 2MB per worker
size_t pool_entries = _Py_WSDEQUE_PARALLEL_GC_SIZE;
size_t pool_bytes = sizeof(_PyWSArray) + sizeof(uintptr_t) * pool_entries;
worker->local_pool = PyMem_RawCalloc(1, pool_bytes);

// During collection, use pre-allocated buffer:
_PyWSDeque_InitWithBuffer(&worker->deque, worker->local_pool,
                          pool_bytes, pool_entries);
```

The pool handles up to 256K objects per worker before falling back to dynamic allocation.

### 2. Split Vector Work Distribution

**Problem**: Original round-robin root distribution scattered related objects across workers, hurting cache locality.

**Solution**: The split vector, populated during the serial `update_refs` phase at 8192-object intervals, divides the GC list into segments. Workers are assigned ranges of split vector entries, preserving allocation-order locality. Objects allocated together tend to reference each other and stay on the same worker.

### 3. Threshold Mechanism

**Problem**: Triggering parallel GC on small heaps where overhead dominates.

**Solution**: The decision to use parallel collection is made in `deduce_unreachable()` after `update_refs_with_splits` populates the split vector. If the split vector has insufficient entries to warrant parallel execution (i.e., too few objects to distribute meaningfully across workers), the collector falls back to the serial path. There is no hardcoded object-count threshold.

---

## Lessons from the Incremental Collector

CPython 3.13 introduced an incremental GC that spreads collection work across multiple pauses. Studying this implementation informed several design decisions:

### 1. Adaptive Thresholds

The incremental collector uses `work_to_do` budgeting to limit work per pause. Similarly, our split-vector threshold ensures parallel GC only activates when the heap is large enough to benefit.

### 2. Tuple Untracking

The incremental collector untracks tuples that only reference immutable objects. We inherit this optimisation -- untracked tuples are never added to worker deques.

### 3. Serial Remains Faster for Small Heaps

For typical Python workloads with modest heaps, the incremental collector's simple serial loop outperforms parallel GC. Parallelism has overhead (atomics, barriers, work distribution) that only pays off at scale.

This is why parallel GC targets a specific niche: **large heaps with manual GC**, particularly AI/ML workloads.

---

## Free Threaded Python Parallel GC

The Free Threaded (FTP) build has a fully independent parallel GC implementation (`gc_free_threading_parallel.c`, `pycore_gc_ft_parallel.h`). It shares the Chase-Lev deque and barrier infrastructure with the GIL build but differs in almost every other respect.

### Key Architectural Differences

| Aspect | GIL Build | FTP Build |
|--------|-----------|-----------|
| Object layout | `_gc_prev` field in `PyGC_Head` | `ob_gc_bits` byte on `PyObject` |
| gc_refs storage | Upper bits of `_gc_prev` | `ob_tid` field (repurposed during STW) |
| Marking mechanism | Fetch-And on `_gc_prev` | Relaxed read + relaxed store on `ob_gc_bits` |
| Work distribution | Split vector (GC list intervals) | Page-based (mimalloc page buckets) |
| Thread pool | Barrier-synchronised pool | Persistent thread pool (`_PyGCThreadPool`) |
| Phases | mark_alive, subtract_refs, mark, sweep | UPDATE_REFS, MARK_HEAP, SCAN_HEAP |

### Page-Based Work Distribution

FTP Python uses mimalloc for memory allocation. Objects live on mimalloc **pages**, which are natural units of work distribution. Pages are enumerated in O(pages) time (not O(objects)) and assigned to worker buckets using sequential filling:

- **Normal pages**: Sequential bucket filling for locality (consecutive pages go to the same worker until the bucket is "full").
- **Huge pages**: Round-robin assignment to spread expensive traversals across workers.

### Relaxed-Atomic Marking

FTP marking uses **relaxed read + relaxed store** instead of atomic read-modify-write, because during stop-the-world all threads are cooperating GC workers:

```c
static inline int
_PyGC_TryMarkAlive(PyObject *op)
{
    // Relaxed read -- filters most already-marked objects
    if (_Py_atomic_load_uint8_relaxed(&op->ob_gc_bits) & _PyGC_BITS_ALIVE) {
        return 0;
    }
    // Relaxed write -- no atomic RMW needed during STW
    uint8_t new_bits = (op->ob_gc_bits | _PyGC_BITS_ALIVE)
                     & ~_PyGC_BITS_UNREACHABLE;
    _Py_atomic_store_uint8_relaxed(&op->ob_gc_bits, new_bits);

    _Py_atomic_fence_acquire();  // Ensure consistent field reads for traversal
    return 1;
}
```

If two workers race to mark the same object, both see not-ALIVE, both write ALIVE (idempotent), both traverse the referents. Duplicate traversal is acceptable: discovered references hit the relaxed-read check on the next level and stop propagating. This eliminates two expensive atomic RMW operations per object (~20--40 cycles) in favour of one relaxed read + one relaxed store (~2--3 cycles).

### FTP Phases

1. **UPDATE_REFS**: Initialise gc_refs from reference counts. Parallel over page buckets with atomic `ob_tid` writes.
2. **MARK_HEAP**: Find roots (gc_refs > 0) and mark reachable objects. Uses work-stealing for transitive closure.
3. **SCAN_HEAP**: Collect unreachable objects into per-worker worklists, then merge.

---

## Architecture Summary

```
                           gc.collect()
                               |
                    split vector populated
                      during update_refs
                               |
                  enough split points for parallel?
                    No --> serial incremental
                    Yes --> parallel collector
                               |
    +--------------------------+--------------------------+
    |                          |                          |
Phase 1: mark_alive     Phase 2: subtract_refs    Phase 3: mark
 (interpreter roots)    (parallel gc_refs decr)   (local-only roots)
                               |
                     split vector segments
                      ~8K objects/segment
                               |
    +----------+----------+----------+----------+
    | Worker 0 | Worker 1 |   ...    | Worker N |
    |  Deque   |  Deque   |         |  Deque   |
    | LocalBuf | LocalBuf |         | LocalBuf |
    +----------+----------+----------+----------+
                               |
                  Phase 4: sweep (serial)
                  move unmarked -> unreachable
                               |
                  Marking: Fetch-And on _gc_prev
```

---

## API

```python
import gc

# Enable parallel GC with N worker threads
gc.enable_parallel(num_workers=4)

# Disable parallel GC (destroys worker threads)
gc.disable_parallel()

# Check configuration
gc.get_parallel_config()
# {'available': True, 'enabled': True, 'num_workers': 4}

# Get statistics from last collection
gc.get_parallel_stats()
# {'enabled': True, 'num_workers': 4,
#  'roots_found': 142, 'roots_distributed': 8703,
#  'gc_roots_found': 0,
#  'collections_attempted': 5, 'collections_succeeded': 5,
#  'objects_traversed': 1048576,
#  'workers': [
#      {'objects_marked': 5000, 'steal_attempts': 12,
#       'steal_successes': 3, 'objects_discovered': 4800,
#       'traversals_performed': 4900, 'roots_in_slice': 0,
#       'work_time_ns': 1234567, 'objects_in_segment': 131072},
#      ...
#  ],
#  'phase_timing': {
#      'update_refs_ns': 500000, 'mark_alive_ns': 200000,
#      'subtract_refs_ns': 800000, 'mark_ns': 100000,
#      'cleanup_ns': 300000, 'total_ns': 1900000,
#      'scan_mark_ns': 1600000, 'finalization_ns': 0,
#      'dealloc_ns': 300000, 'stw_pause_ns': 800000
#  }}
```

---

## Performance Characteristics

Based on systematic experimentation:

| Scenario | Parallel vs Incremental |
|----------|------------------------|
| < 100K objects | 0.5--0.9x (slower) |
| 100K--300K objects | 0.9--1.1x (break-even) |
| 300K--500K objects | 1.1--1.3x (slight win) |
| > 500K objects | **1.2--2.3x (clear win)** |

Best results: **2.33x speedup** on random graph topologies with 1M objects and 8 workers (FTP build, PGO+LTO, fixed seed=42).

---

## Future Work

### GIL Build

- **Parallel sweep**: Currently serial; could parallelise for large heaps.
- **NUMA awareness**: Pin workers to cores for better memory locality.
- **Dynamic worker count**: Adjust based on heap size and CPU availability.

### Free Threaded Build

- **Concurrent marking**: Mark objects while application runs (currently STW).
- **Incremental collection**: Spread work across multiple pauses.
- **Write barriers**: If moving to concurrent collection, track mutations during marking.

---

## Conclusion

Parallel GC for CPython is a targeted optimisation for large-heap workloads, particularly AI/ML applications with manual GC timing. The GIL build uses a multi-phase architecture with Fetch-And atomic marking, split-vector work distribution, and pipelined producer-consumer root expansion. The Free Threaded build uses page-based distribution over mimalloc pages with relaxed-atomic marking. Both builds share a Chase-Lev work-stealing deque and portable barrier synchronisation.

On heaps with 1M+ objects, collection speedups of 1.2--2.3x are achieved with 8 workers on an optimised FTP build, with stop-the-world pause reductions of 54--67%.
