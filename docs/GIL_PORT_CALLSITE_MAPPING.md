# GIL Parallel GC Call-Site Mapping

**Status:** implemented at `92f992042c`

**Design baseline:** `beb2907f8d723d7a202d068cb7de69448c53ff7e`

**Upstream target:** `333071231d3a46cccc32d7f44b99328c3299d0b1`

## Constraint

The parallel implementation, work distribution, atomics, synchronization,
fallbacks, adaptive controller, diagnostics, and tests remain unchanged. This
document maps their existing call sites onto the restored three-generation GIL
collector. If a mapping cannot preserve behaviour, it is a hard blocker for
discussion rather than permission to alter the design.

## Why the call sites moved

The baseline was integrated with CPython's incremental GIL collector. Upstream
commit `1575a81bf2` replaced that collector with the forward-ported traditional
three-generation collector. The core cycle-detection pipeline remains:

```text
update_refs -> subtract_refs -> move_unreachable -> cleanup
```

The surrounding driver changed from generation-specific functions calling
`gc_collect_region()` to `gc_collect_main()` operating on the selected and
merged generation list.

## Exact mapping

| Baseline operation | Current serial call site | Mapping |
|---|---|---|
| `update_refs_with_splits(base, split_vector)` | `deduce_unreachable()` calls `update_refs(base)` | Replace only when the unchanged baseline enable predicate is true; retain serial `update_refs()` otherwise. |
| `_PyGC_ParallelMarkAliveFromQueue(interp, base)` with baseline serial fallback | Between `update_refs` and `subtract_refs` in `deduce_unreachable()` | Preserve the exact baseline ordering and fallback. |
| `_PyGC_ParallelSubtractRefs(interp, base)` with serial fallback | `deduce_unreachable()` calls `subtract_refs(base)` | Preserve the baseline call and result handling after the approved collection-wide size decision. |
| `_PyGC_ParallelMoveUnreachable(interp, base, unreachable)` with serial fallback | `deduce_unreachable()` initializes `unreachable`, then calls `move_unreachable()` | Preserve the exact baseline ordering and fallback. |
| Record `last_generation` | Baseline `gc_collect_region()` entry | Put at `gc_collect_main()` after `GENERATION_AUTO` has been resolved and before `deduce_unreachable()`. |
| Reset private adaptive timing state | Baseline `_PyGC_Collect()` entry | Reset the unchanged `parallel_gc` timing fields in `gc_collect_main()`, after its entry assertions and before the `collecting` compare-and-exchange. This does not alter upstream GC timing. |
| Record `cleanup_end_ns` and call `_PyGC_RandomWalkUpdate()` | End of baseline `gc_collect_region()`, immediately after legacy-finalizer handling and list validation | Current `gc_collect_main()` has the same post-cleanup point. Pass the exact candidate count, matching the free-threaded collector, rather than the baseline's coarse split-vector proxy. |

The 8192-object split interval remains the work-partitioning granularity. The
approved serial threshold is two complete slices (16,384 candidates): below
that point, subtraction and reachability stay entirely on the collecting
thread and the adaptive controller is not updated. Above it, the interval does
not select or cap the active worker count; that remains the responsibility of
`adaptive_workers`.

## Timing responsibilities

Upstream and `parallel_gc` timing have separate purposes and must remain
separate:

- Upstream's existing `stats.ts_start`, `stats.ts_stop`, and `stats.duration`
  remain untouched. They define the canonical collection duration for both
  serial and parallel collections, so the two modes remain directly
  comparable through the normal upstream statistics and callbacks.
- The `parallel_gc` fields (`gc_start_ns` and the phase end timestamps) remain
  private inputs to the unchanged adaptive worker controller. They retain
  their baseline boundaries and do not replace, adjust, or contribute to
  upstream's `stats.duration`.
- Resetting the private fields at the common collection entry is bookkeeping;
  the adaptive measurement itself still starts at the original point in the
  parallel `deduce_unreachable()` path.

The two systems may use the same monotonic clock API, but they do not share
timestamps or reporting semantics.

## List-flag representation

The baseline incremental collector used bit 0 of `_gc_next` for old-space
membership and bit 1 for `NEXT_MASK_UNREACHABLE`. Its parallel sweep therefore
preserved the old-space bit while setting the unreachable bit.

The restored upstream collector represents generations with separate lists.
It has no old-space bit and uses bit 0 for `NEXT_MASK_UNREACHABLE`. The approved
mapping changes the parallel sweep's temporary flag from
`2 | old_space_bit` to `1`. This removes no parallel-GC state: the old-space
bit belonged exclusively to the retired incremental collector.

## Baseline code retention

The literal baseline patch adds these files cleanly to the upstream target:

- `Include/internal/pycore_gc_parallel.h`
- `Include/internal/pycore_gc_random_walk.h`
- `Include/internal/pycore_gc_barrier.h`
- `Include/internal/pycore_ws_deque.h`
- `Lib/test/test_gc_parallel_mark_alive.py`

Their algorithms and memory-ordering operations require no change merely to
place them in the current source tree.

`Python/gc_parallel.c` retains the baseline algorithms with the approved
list-bit mapping, complete draining of private pre-mark work, adaptive rollback
state, and current internal visitor symbol required by stack-reference
handling. The 16,384-candidate decision is integrated in `Python/gc.c`.

## Invariants that the call-site mapping must preserve

1. `update_refs_with_splits` completes before any parallel traversal starts.
2. Parallel mark-alive completes before parallel `subtract_refs` begins.
3. `move_unreachable` starts only after `subtract_refs` completes.
4. Fewer than 16,384 candidates take the serial path before pre-mark dispatch;
   malformed or unusable split work also retains a serial fallback.
5. `_PyGC_DispatchAndWait` continues to use `adaptive_workers`; inactive
   workers remain asleep.
6. No atomic operation, fence, mutex, condition variable, semaphore, barrier,
   queue operation, or ordering is changed.
7. The original reentrancy and allocation-failure paths remain unchanged.
8. Timing is reset once per collection and the controller is updated once,
   after cleanup, using the original inputs.

## Resolved call-site decision

`gc_collect_main()` is the current common lifecycle for manual, automatic, and
shutdown collections. It therefore receives the private timing reset and the
post-cleanup controller update at the equivalent baseline boundaries.
`last_generation` is recorded only after `GENERATION_AUTO` has resolved and
immediately before `deduce_unreachable()`.

This mapping does not authorize any change to either timing system. Any case
where the baseline adaptive boundaries cannot coexist with upstream's
unchanged duration boundaries is a hard blocker for discussion.

## Verification status and remaining gate

The baseline GIL API, lifecycle, statistics, mark-alive, property, and deque
test intent is restored. Fixed-seed tests exercise phase order and adaptive
state, and threshold tests cover both sides of 16,384 candidates. Debug and
optimized AArch64 builds and the long-form benchmark have run. A clean-revision
broad suite, sanitizer rerun, and native feature-on platform matrix remain
submission gates.
