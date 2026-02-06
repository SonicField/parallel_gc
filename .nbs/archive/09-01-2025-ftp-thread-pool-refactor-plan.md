# FTP Thread Pool Refactoring Plan

## Design Principles (from Alex)
1. **No ad-hoc threads** - All parallel work uses the persistent thread pool
2. **No fallback** - If parallel GC is enabled, the pool MUST exist
3. **Consistency with GIL** - Workers should have thread states like GIL does

## Current State
- Persistent thread pool exists (`_PyGCThreadPool`)
- Pool only used for `_PyGC_ParallelPropagateAliveWithPool`
- 5 ad-hoc thread functions spawn their own threads
- Fallback path exists when pool isn't active (should be removed)

## Functions to DELETE (ad-hoc thread spawning)
1. `_PyGC_ParallelMarkAlive` - spawns `parallel_worker_thread`
2. `_PyGC_ParallelPropagateAlive` - spawns `propagate_worker_thread` (fallback)
3. `_PyGC_ParallelUpdateRefs` - spawns `update_refs_thread`
4. `_PyGC_ParallelMarkHeap` - spawns `mark_heap_thread`
5. `_PyGC_ParallelScanHeap` - spawns `scan_heap_thread`

## Functions to KEEP/EXTEND
1. `_PyGC_ParallelPropagateAliveWithPool` - already uses pool, becomes the only propagate function
2. `_PyGC_ThreadPoolInit/Fini` - pool management
3. `thread_pool_worker` - needs thread state setup
4. `thread_pool_do_work` - needs to handle multiple work types

## Refactoring Steps

### Step 1: Add thread state to pool workers
Add `_PyThreadState_New()` etc to `thread_pool_worker` like GIL does.

### Step 2: Extend _PyGCWorkType enum
```c
typedef enum {
    _PyGC_WORK_NONE = 0,
    _PyGC_WORK_PROPAGATE,       // Propagate alive from roots
    _PyGC_WORK_UPDATE_REFS,     // Initialize gc_refs on heap
    _PyGC_WORK_MARK_HEAP,       // Find roots and mark reachable
    _PyGC_WORK_SCAN_HEAP,       // Collect unreachable objects
    _PyGC_WORK_SHUTDOWN
} _PyGCWorkType;
```

### Step 3: Add work dispatch to thread_pool_do_work
Switch on work type to call appropriate work function.

### Step 4: Create pool-based versions of each phase
- `update_refs_pool_work()` - called by workers for UPDATE_REFS
- `mark_heap_pool_work()` - called by workers for MARK_HEAP
- `scan_heap_pool_work()` - called by workers for SCAN_HEAP

### Step 5: Update callers to use pool
Remove fallback paths, assume pool always exists.

### Step 6: Delete dead code
Remove all ad-hoc thread functions and their helpers.

### Step 7: Test
- Run gc tests
- Run benchmark
- Verify no segfaults
