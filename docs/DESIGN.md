# Parallel GC design

**Audience:** CPython core developers reviewing the design. Assumes familiarity
with `gc.c`, `gc_free_threading.c`, `PyGC_Head`, `ob_gc_bits` and the mimalloc
page layout.

The design baseline is CPython fork revision `c67363fa59` (upstream base
`333071231d`). Later unreferenced-code removal, opt-in production-test
instrumentation and build-dependency repairs are recorded in
[the integration log](CLAUDE_INTEGRATION_PLAN.md); they preserve the active
collector design. The parent's `cpython/` gitlink selects the source for a later
checkout; check this narrative against that source after collector changes.
Evidence lives in [PERFORMANCE.md](PERFORMANCE.md) and
[VALIDATION.md](VALIDATION.md); known defects in
[OPEN_ISSUES.md](OPEN_ISSUES.md). The superseded source documents
remain in git history at `724b74b`.

---

## 1. Overview

CPython's cycle collector stops the interpreter while it identifies objects
unreachable through reference-count information and graph traversal. On a
small collection, waking helpers and using atomic operations costs more than
it saves. On a large heap, reference adjustment and graph traversal can
dominate. The project therefore combines serial fast paths with persistent
worker pools. Both collectors are stop-the-world: "parallel" means the
collecting thread and helpers share collector work while application threads
are paused. It does not mean concurrent marking.

| Build | Guard | Source | Extends |
|-------|-------|--------|---------|
| GIL (`--with-parallel-gc`) | `Py_PARALLEL_GC` | `gc_parallel.c`, `pycore_gc_parallel.h` | `Python/gc.c` |
| Free-threaded (`--with-parallel-gc --disable-gil`) | `Py_GIL_DISABLED && Py_PARALLEL_GC` | `gc_free_threading_parallel.c`, `pycore_gc_ft_parallel.h` | `Python/gc_free_threading.c` |

The implementations are mutually exclusive and require a 64-bit target
(`SIZEOF_VOID_P >= 8`, enforced at compile time and by `configure` and
`PCbuild/build.bat`). Parallel GC is opt-in at build time and at runtime
(`gc.enable_parallel()`). There is no environment-variable, `-X` or `PyConfig`
control. The target is semantic equivalence with serial GC: the same
reachable and unreachable classification, finalization and weak-reference
semantics. Traversal and worklist order are not guaranteed.

### What runs in parallel

| Collector | Parallel phases | Serial phases |
|-----------|-----------------|---------------|
| GIL, ≥ 16,384 candidates | interpreter-root pre-marking, reference subtraction, reachability marking | count/split walk, list reconstruction, finalization, deallocation |
| GIL, < 16,384 candidates | none | complete collection |
| Free-threaded | `update_refs`, `mark_heap`, `scan_heap`; known-root propagation is *dispatched* to the pool but its effective parallelism is conditional (§3.3) | deferred stack scan, finalization, deallocation |

**Measured limitation (15 October 2026).** FT known-root propagation
(`mark_alive`) dominated the measured large live graphs. With live data
reachable only from module state, one worker performed about 99% of that phase
at 16 workers, and the collection was 0.61–0.83× the speed of serial. The same
graph reachable from a frame local scaled to 3.39×. A binary tree scaled to
1.22× regardless of holder. Mechanism and data:
[scaling review](reviews/2026-10-15-claude-scaling-review.md) §7; tracked as
P1–P3 in [OPEN_ISSUES.md](OPEN_ISSUES.md) §2.

---

## 2. GIL collector

### 2.1 Integration

The collector hooks into `deduce_unreachable()` in `Python/gc.c`.
`gc_collect_main()` first resolves the generation and merges younger
generations into it, preserving upstream trigger and promotion policy. The
threshold therefore applies to exactly the list the serial collector would
process.

```
deduce_unreachable()
  update_refs_with_splits()          serial; gc_refs = Py_REFCNT; waypoints every 8192
  candidates < 16,384?               yes: serial subtract_refs + move_unreachable; no training
  if ARMED: start pool               failure: serial remainder, warn after cleanup, FAILED
  _PyGC_ParallelMarkAliveFromQueue() parallel known-root pre-mark (serial fallback)
  _PyGC_ParallelSubtractRefs()       parallel atomic decrement (serial fallback)
  _PyGC_ParallelMoveUnreachable()    parallel mark, then serial list reconstruction
                                     (falls back to move_unreachable())
then: weakrefs, finalization, resurrection, deletion (upstream, serial)
```

### 2.2 Object layout

`_gc_prev` holds the previous-list pointer and metadata: bits 63–2 `gc_refs`
(`_PyGC_PREV_SHIFT` = 2), bit 1 COLLECTING, bit 0 FINALIZED. During parallel
marking COLLECTING is the mark bit: 1 = not yet proven reachable, 0 = marked.
Upstream uses bit 0 of `_gc_next` as the temporary unreachable-list tag (there
is no incremental collector old-space bit), and list reconstruction writes that
representation.

### 2.3 Count, partition and decide

`update_refs_with_splits()` sets `gc_refs = ob_refcnt` and records a pointer
into the list every `_PyGC_SPLIT_INTERVAL` (8192) objects in a growable
`_PyGCSplitVector`, with the list head appended as an exclusive end marker.
This gives O(1) partitioning without an extra traversal, and the exact
candidate count. Below `_PyGC_MIN_PARALLEL_CANDIDATES` (two slices, 16,384)
the collecting thread runs the serial path, wakes no helper and does not train
the controller. The threshold is collection-wide; phase-specific caps would
make measurement and tuning depend on several interacting policies.

### 2.4 Known-root pre-mark

The collecting thread marks known interpreter roots, expands each by one level
and places the children in a shared block queue, so that workers receive many
independent starting points rather than a few hub-like roots. Workers claim
64-object batches; descendants enter a 1024-entry worker-local buffer and
overflow to the worker's private deque. **This phase does not steal.** Before
reporting completion a worker must drain its buffer and deque: they hold
borrowed `PyObject *` values and are reused by later collections. Pre-marked
objects have COLLECTING cleared, so later phases skip them and their edges. If
the queue path cannot run, the serial known-root traversal is used; failure to
pre-mark is an optimization failure, not a semantic change.

### 2.5 Reference subtraction

Workers take contiguous split-vector ranges and call `tp_traverse` with
`_PyGC_ParallelVisitDecref`, which atomically subtracts from `gc_refs` of
COLLECTING objects because references cross ranges. `_PyGC_VisitStackRef()`
recognises both decrement visitors and skips borrowed or embedded stack
references, which `Py_REFCNT` does not represent.

### 2.6 Residual marking and list reconstruction

Workers scan their ranges for objects with `gc_refs > 0`, claim them with the
atomic COLLECTING transition (§2.7) and traverse locally. Only the winning
worker queues a shared descendant. **This phase does not steal.** The
collecting thread then walks the list: objects still COLLECTING go to
`unreachable`; reachable objects have `_gc_prev` restored. List mutation stays
serial so one owner repairs links in one ordered pass.

### 2.7 Atomic marking

```c
static inline int
gc_try_mark_reachable_atomic(PyGC_Head *gc)
{
    uintptr_t prev = _Py_atomic_load_uintptr_relaxed(&gc->_gc_prev);
    if (!(prev & _PyGC_PREV_MASK_COLLECTING)) {
        return 0;                       // already marked: no RMW
    }
    uintptr_t old_prev = _Py_atomic_and_uintptr(
        &gc->_gc_prev, ~_PyGC_PREV_MASK_COLLECTING);
    int marked = (old_prev & _PyGC_PREV_MASK_COLLECTING) != 0;
    if (marked) {
        _Py_atomic_fence_acquire();     // weakly ordered targets
    }
    return marked;
}
```

The bit is monotonic (1→0), so fetch-and needs no retry loop, the old value
assigns ownership, and there is no ABA. Memory-ordering comments in the source
are correctness documentation; any change must be reviewed for x86-64 and
weakly ordered targets such as AArch64.

### 2.8 Serial fallback conditions

Serial code runs when parallel GC is disabled, the pool is not active, the
collection is below threshold, the split vector cannot describe usable work, or
a phase cannot dispatch. Lazy-start failures fall back with bounded
diagnostics (§5).

---

## 3. Free-threaded collector

### 3.1 Integration

`gc_collect_main()` keeps the upstream trigger policy and delegates to
`gc_collect_internal()`, which owns the stop/resume schedule. Parallel GC
replaces selected work inside that schedule.

```
gc_mark_alive_from_roots()     _PyGC_ParallelPropagateAliveWithPool() | gc_propagate_alive()
deduce_unreachable_heap()
  _PyGC_AssignPagesToBuckets()       page-bucket preparation
  _PyGC_ParallelUpdateRefsWithPool() | gc_visit_heaps(update_refs)
  gc_visit_thread_stacks()           serial deferred-reference scan
  _PyGC_ParallelMarkHeapWithPool()   | mark_heap_visitor
  _PyGC_ParallelScanHeapWithPool()   | scan_heap_visitor (also used at shutdown)
find weakrefs, resume world; decrefs, callbacks, finalizers
stop world; resurrection, weakref and free-list clearing; resume; delete_garbage
update adaptive controller
```

Known-root propagation and everything in `deduce_unreachable_heap()` run with
the world stopped. Biased-reference merging, delayed frees, weak references,
finalizers, resurrection and `tp_clear` keep their upstream placement.

### 3.2 Object layout and comparison with GIL

`ob_gc_bits` holds ALIVE (`1<<5`) and UNREACHABLE (`1<<2`); `ob_tid` stores
`gc_refs` while the world is stopped.

| Aspect | GIL | Free-threaded |
|--------|-----|---------------|
| Mark bit | `_gc_prev` COLLECTING | `ob_gc_bits` ALIVE / UNREACHABLE |
| `gc_refs` | upper bits of `_gc_prev` | `ob_tid` |
| Work distribution | split vector over the GC list | mimalloc pages |
| Stealing | none | `mark_heap`, known-root propagation |

### 3.3 Known-root propagation

Roots (`sysdict`, extra interpreter roots, thread stacks) are flattened into an
array and dealt round-robin to worker deques; workers set ALIVE through the
transitive closure using a 1024-entry private buffer, their deque and stealing.
ALIVE is an optimization hint: some roots (for example extension globals) are
missed, and the later reference-difference pass is authoritative. The parallel
path is used only while `gc.freeze()` is inactive and parallel GC is enabled;
otherwise the unchanged `gc_propagate_alive()` runs.

Marking uses `_PyGC_TryMarkAlive()`: a relaxed byte load and relaxed store
that sets ALIVE and clears UNREACHABLE. Two workers may both traverse one
object. That is safe here and avoids an atomic read-modify-write per edge;
`mark_heap` cannot tolerate duplicate ownership and uses fetch-and (§3.6).
Substituting one protocol for the other is a design change.

**Effective parallelism is conditional.** Work becomes stealable only when a
worker's private buffer overflows into its deque, and an idle worker leaves the
phase permanently after `2 × num_workers` consecutive failed steal sweeps
(`propagate_pool_work`). When the root set fans out slowly (for example data
reachable only through `sysdict → sys.modules → module dict`), helpers can exit
before any work is stealable, and one worker traverses the closure alone.
Shapes whose traversal never fills the private buffer (deep, narrow trees)
never expose stealable work. Measurements:
[scaling review](reviews/2026-10-15-claude-scaling-review.md) §7.3–7.4.
Correctness is unaffected: each owner drains its own work.

### 3.4 Page-based work distribution

Non-empty mimalloc GC pages, including pages in the interpreter's abandoned
pool (`_mi_abandoned_pool_enumerate_pages()`), are assigned to per-worker
buckets: ordinary pages contiguously for locality, huge pages round-robin so
one huge page does not dominate a bucket. Page counting is O(threads) via
`heap->page_count`; enumeration is O(pages). A page is the natural unit of
ownership while the world is stopped and avoids two workers iterating one
page.

### 3.5 `update_refs` and the deferred stack scan

Two barrier-separated passes over the buckets: (1) set UNREACHABLE and zero
`ob_tid`; (2) add the adjusted reference count and atomically subtract
references found by `tp_traverse`. The barrier ensures no worker subtracts from
an `ob_tid` its owner has not initialized. ALIVE objects are skipped. Bucket
assignment failure happens before either pass and falls back to the serial
walk; a failure after mutation begins aborts the collection rather than mixing
structurally different walks.

`gc_visit_thread_stacks()` then accounts for deferred stack references
serially: frame ownership, tagged stack references and the
`skip_deferred_objects` fallback belong to the upstream stack protocol.

### 3.6 `mark_heap`

Workers scan their pages for objects with positive adjusted `gc_refs`, or
objects that must be kept because deferred references could not be inspected.
The worker that atomically clears UNREACHABLE owns the object and traverses
it:

```c
static inline int
_PyGC_TryMarkReachable(PyObject *op)
{
    if (!(_Py_atomic_load_uint8_relaxed(&op->ob_gc_bits)
          & _PyGC_BITS_UNREACHABLE)) {
        return 0;
    }
    return _PyGC_TryClearBit(op, _PyGC_BITS_UNREACHABLE);
}
```

Workers drain their deque LIFO and steal FIFO. A worker leaves after three
consecutive idle rounds (`mark_heap_pool_work`). An early exit cannot lose
reachability because every owner drains its own deque. A shared error flag
propagates traversal or allocation failure; parallel marking errors restore
reference state before aborting.

### 3.7 `scan_heap`

The phase gathers current pages into an array that workers claim through an
atomic index. Reachable objects have `ob_tid` ownership restored and ALIVE
cleared. Unreachable objects have deferred reference counting disabled and are
linked into per-worker unreachable or legacy-finalizer lists with a per-worker
live count; the collecting thread merges them. Unique IDs are collected per
worker and released in one batch, avoiding a lock per object. Shutdown
collections keep the serial visitor because their deferred-reference handling
has different locking requirements.

### 3.8 Serial work around the parallel phases

After the first stopped-world section, application threads run
weak-reference callbacks and finalizers; the world stops again for
resurrection, weak-reference and free-list clearing, then resumes for
`tp_clear` and deletion. A finalizer-heavy workload can therefore spend most
of its callback interval outside the parallel phases (Amdahl), and a
`gc.callbacks` start-to-stop interval is not one stop-the-world pause.

### 3.9 Built-in container traversal and PGO

The propagation local-buffer loop avoids generic per-edge callback dispatch
when an object's `tp_traverse` is the built-in list, tuple or dictionary
traversal function. Selection is by traversal-function identity, not a type
name; custom subclass traversal remains on the generic path. Lists and tuples
retain the serial reverse-index visitation order. Tuples retain
`_PyTuple_MaybeUntrack()` and clear ALIVE if untracking succeeds.

Dictionary layout knowledge lives in `_PyDict_FOREACH_GC_REF` in
`pycore_dict.h`, shared with `dict_traverse()` in `dictobject.c`. Callers supply
the operation on each reference: the serial caller invokes its visitor; the
parallel caller performs propagation directly. The macro preserves split,
combined-Unicode and general-key layouts, skips missing entries, and visits a
general entry's value before its key. This separates layout rules from the
operation rather than maintaining two dictionary walkers.

These explicit paths remove measured dispatch overhead without changing the
marking or work-distribution policy. Parallel-aware PGO additionally trains
both collectors through `Tools/build/parallel_gc_profile.py`; it supplements
the explicit paths rather than relying on compiler decisions to recreate them.
Retained results and the unsuccessful forced-inlining experiment are recorded
in [PERFORMANCE.md](PERFORMANCE.md) §5. The traversal tests check visitation,
untracking and generic fallback; they are not just speed measurements.

---

## 4. Shared infrastructure

### 4.1 Chase-Lev deque (`pycore_ws_deque.h`)

After Chase and Lev (2005) and Lê et al. (2013). `top` and `bot` are
cache-line padded (64 bytes, hard-coded) and initialised to 1; the array is a
power-of-two circular buffer. Owner push/take is LIFO and lock-free; steal is a
FIFO CAS. Standalone capacity is 4096 pointers; each collector worker normally
supplies a preallocated 256K-entry region (about 2 MiB on 64-bit), avoiding
hot-path allocation. Growth reports allocation failure, and propagating it
without losing work is a required invariant (open items in
[OPEN_ISSUES.md](OPEN_ISSUES.md)).

### 4.2 Local buffer

A 1024-entry `_PyGCLocalBuffer` avoids fences for owner-only work.
`_PyGC_OverflowFlush()` moves half to the deque when full;
`_PyGC_RefillLocalFromDeque()` pulls up to 512; `_PyGC_BatchSteal()` steals
up to 512 by repeated single steals (used by FT propagation, not by the GIL
paths). Items in the buffer are invisible to other workers.

### 4.3 Dispatch and barrier (`pycore_gc_barrier.h`)

Each worker sleeps on its own condition variable; `dispatch_and_wait()`
signals only the selected workers and waits on a completion condition. The
barrier (`num_left`, `capacity`, `epoch`, mutex, condition) is portable across
POSIX and Windows primitives. It is not the dispatch mechanism. The GIL startup
handshake uses a cancellable condition protocol; the FT phase barrier is
resized to the active participant count for the `update_refs` boundary.

### 4.4 Termination

| Phase | Policy |
|-------|--------|
| GIL pre-mark and residual mark | No stealing; each worker drains its shared-queue claims, buffer and deque. |
| FT known-root propagation | Steal; exit after `2 × num_workers` consecutive failed sweeps. |
| FT `mark_heap` | Steal; exit after three idle rounds. |

The FT rules are heuristics, not termination protocols. They are safe because
work is only ever pushed by its owner, which drains it; they can cost
parallelism (§3.3).

---

## 5. Pool lifecycle and worker selection

### 5.1 States

| State | Policy | Live helpers | Collection |
|-------|--------|--------------|------------|
| `DISABLED` | off | no | serial |
| `ARMED` | on | no | start the pool when eligible |
| `ACTIVE` | on | yes | parallel with adaptive controller |
| `FAILED` | off | no | serial; no automatic retry |

A transient `STARTING` state exists while the lifecycle lock is held; it is
never reported as enabled. Fork, disable, shutdown and competing collections
wait for it to commit to `ACTIVE` or roll back to `FAILED`.
`gc.enable_parallel()` moves `DISABLED`/`FAILED` to `ARMED` (resetting the
controller and failure latch, creating no thread) and is a no-op otherwise.
`gc.disable_parallel()` moves any state to `DISABLED`.

### 5.2 Lazy transactional startup

- **GIL:** the first collection with ≥ 16,384 candidates and two usable splits
  starts the fixed 16-helper pool while the collecting thread holds the GIL,
  before any dispatch. The collecting thread only coordinates. A workload that
  stays below the threshold never creates a thread.
- **FT:** the first collection starts 15 helpers *before* stopping the world,
  because thread-state creation and QSBR growth can need stop-the-world
  coordination. The collecting thread is worker zero (16 participants).

The transaction allocates all pool state, creates every worker
`PyThreadState` before native threads, records each created handle, and waits
for readiness through a cancellable handshake. It publishes the pool only when
every helper is ready. On failure it wakes and joins only created helpers,
deletes created thread states, frees all resources, reduces the exception to a
bounded code and enters `FAILED`. The collection completes serially; one
`RuntimeWarning` is emitted after collection state is safe (world restarted,
`collecting` cleared). A secondary failure while warning is suppressed, and
warnings-as-errors cannot turn the serial fallback into a failed collection.
Only an explicit `gc.enable_parallel()` permits another attempt.

Lazy startup exists because eager creation triggered glibc's irreversible
first-thread transition: `sqlite_synth` was 38.1% (GIL) and 10.4% (FT) slower
with an unused pool ([PERFORMANCE.md](PERFORMANCE.md) §5).

### 5.3 Disable and shutdown

GIL `gc.disable_parallel()` stops helpers but may retain reusable storage; FT
joins helpers and destroys the pool. Re-enabling is lazy in both. Interpreter
finalization handles all states; `pylifecycle.c` finalizes pools before
thread-state teardown and `pystate.c` defensively finalizes any remainder. The
FT pool and worker arguments are per-interpreter; a lifecycle mutex serializes
enable, disable, configuration snapshots and the collection-start decision.

### 5.4 Observability

| `get_parallel_config()` field | `DISABLED` | `ARMED` | `ACTIVE` | `FAILED` |
|---|---|---|---|---|
| `enabled` | false | true | true | false |
| `pool_active` | false | false | true | false |
| `num_workers` | 0 | 16 | 16 | 0 |
| `adaptive_workers` | absent | 4 | current | absent |
| `startup_failed` | false | false | false | true |

`get_parallel_stats()` adds a monotonic `pool_startup_failures` counter, a
bounded `last_pool_startup_error` code, implementation counters and the last
private phase timings. FT also reports a `parallel_cleanup` key inherited from
the prototype although finalization and deletion are serial. Field names are
subject to API review ([OPEN_ISSUES.md](OPEN_ISSUES.md) §3).

### 5.5 Adaptive worker controller (`pycore_gc_random_walk.h`)

Both collectors share one stochastic random walk. It starts at
`min(4, maximum)`; the first valid parallel collection sets a baseline cost.
On each accepted count it refreshes the baseline and, with probability 20%,
proposes `N−1` or `N+1` with equal probability. The next valid collection keeps
the trial only if its cost is lower, else walks back. Bounds are 2–16, and the
count persists while the pool exists. Cost is elapsed nanoseconds divided by
the exact candidate count, not objects collected: a live heap that reclaims
nothing still does graph work. Zero-candidate or invalid samples and GIL
sub-threshold collections do not train it.

FT excludes serial from the search: serial cost is discontinuous, and an
adjacent walk that retreats to serial may never cross a slower intermediate
count to a faster one. Local minima within 2–16 remain possible; there is no
global-optimum or convergence guarantee. In a GIL build the count is helpers
coordinated by the collecting thread; in FT it includes worker zero (4 = the
collector plus three helpers).

### 5.6 Timing boundaries

Upstream timing still supplies `gc.get_stats()` and callback durations.
Private timestamps split the last eligible collection into phases and supply
the controller's elapsed cost. GIL starts the interval immediately before
`update_refs_with_splits()` in a qualifying `deduce_unreachable()` and updates
the controller once after cleanup. FT records from the start of
`gc_collect_internal()` through `delete_garbage()`, before legacy-finalizer
bookkeeping. Both therefore include serial cleanup.

### 5.7 Helper thread states

GIL helpers create and bind persistent `PyThreadState` objects. FT helpers own
persistent thread states and install them (and the interpreter) in thread-local
storage while running collector work, without a full bind. This supports
debug-build reference accounting when `tp_traverse` changes a reference count.
Extension `tp_traverse` therefore runs on helper threads; compatibility is an
open item.

---

## 6. Fork lifecycle

**Scope:** forks made through `PyOS_BeforeFork()`,
`PyOS_AfterFork_Parent()` and `PyOS_AfterFork_Child()` (including
`os.fork()`). A raw `fork()` from an extension bypasses CPython's recovery and
is not supported.

**Problem:** a child of an active pool inherits handles for vanished threads,
worker thread states CPython removes after fork, synchronization objects whose
state refers to vanished waiters, dispatch counters and queues, and the
parent's adaptive history. Dispatching through them can wait forever.

**Parent:** pool, adaptive state, statistics and configuration are unchanged.
No dispatch can be in progress at the snapshot because the world is stopped.

**Child:** before Python resumes, recovery confirms no phase was active,
discards inherited handles, thread-state pointers, queues and synchronization
state without joining parent-only helpers, leaves no pool or helper, and
preserves the enabled policy and maximum of 16. An enabled child is `ARMED`;
`DISABLED` and `FAILED` are preserved. The controller is reset: active workers
to `min(4, maximum)`, previous cost to zero, pending trial cleared, random seed
reset, and any timing begun before the fork discarded.

**Forks during collection:** parallel phases never call Python, so supported
fork sites (GC callbacks, weak-reference callbacks, `__del__`, destruction
during cleanup) occur while helpers are idle. The child finishes the inherited
collection serially and excludes it from learning; a per-collection latch also
covers forks from the start callback. Recovery must not assume
`gcstate->collecting` is clear.

```text
PyOS_BeforeFork()         acquire FT lifecycle lock; stop world; verify GC idle
fork()
  parent: PyOS_AfterFork_Parent()  release lifecycle lock; resume world
  child:  reinit runtime locks; remove vanished thread states;
          recover parallel-GC state; reset controller; remain armed; resume
```

Child recovery runs after CPython reinitializes thread machinery and detaches
vanished thread states, before those states are destroyed and before user
after-fork callbacks (`Modules/posixmodule.c`). The child reinitializes the FT
lifecycle mutex rather than unlocking a copied owner. GIL and FT keep separate
recovery code (all GIL workers are helpers; FT worker zero is the collecting
thread) but share the reset definition.

**Subinterpreters:** CPython deletes non-main interpreters in the child, so
only the main interpreter's controller is recovered. Upstream-based feature-off
GIL and FT builds crash (`SIGSEGV`) when the main interpreter forks with an
idle legacy subinterpreter, without parallel GC. The intended test is retained
and skipped. If upstream fixes this, pools of interpreters about to be deleted
must be abandoned without joining parent-only helpers.

**Verification (both feature-on builds, subprocesses with bounded waits):**
fork between collections then collect a large heap in the child; fork from
`__del__`, finish the inherited collection, then collect; parent keeps its
worker count and cost; child starts at four with no cost; child recovery
creates no helper and stays armed; the inherited collection neither trains nor
dispatches; a later child collection trains; repeat to expose stale state.
Feature-off builds keep normal fork behaviour; platforms without `fork()` skip.

---

## 7. Python API (`Modules/gcmodule.c`)

- `gc.enable_parallel()`: arm (§5.1). No worker-count argument. Raises
  `RuntimeError` in builds without support.
- `gc.disable_parallel()`: §5.3. Raises `RuntimeError` without support.
- `gc.get_parallel_config()`: availability, state fields (§5.4). Reports
  `available: False` without support.
- `gc.get_parallel_stats()`: diagnostics and phase timings; does not replace
  `gc.get_stats()`.
- `gc.collect_async()`: schedules the ordinary collector and returns without
  waiting. It neither enables parallel collection nor selects workers, and is
  outside the discussion draft's scope.

---

## 8. Required invariants

1. Every reachable object is marked. Atomic marking, worklist draining and
   termination must establish this on every active path; the concurrency audit
   must validate the argument.
2. Marking is monotonic within a collection: COLLECTING/UNREACHABLE only clear.
3. Parallel and serial paths classify the same candidates as reachable and
   unreachable immediately before weak-reference and finalizer processing.
4. Each helper has its own deque and wake state; shared bits, counters,
   descriptors and synchronization use their documented atomic or locked
   protocols.
5. A dispatch returns only after every selected worker signals completion; the
   FT `update_refs` barrier prevents cross-page decrements before every page is
   initialized.
6. No borrowed pointer survives a phase: every buffer and deque is empty at
   completion.
7. Adaptive measurements include serial cleanup and use the shared
   normalization with exact candidate counts; GIL sub-threshold collections do
   not train.
8. Work queues never silently drop an object. Before parallel mutation a phase
   may fall back to its serial equivalent; after it, the collector restores
   defined state or aborts rather than combining two half-completed
   algorithms.

---

## 9. Source map

| File | Role |
|------|------|
| `Python/gc_parallel.c` | GIL pool, lifecycle, split vector, pre-mark, subtract, mark, controller dispatch |
| `Python/gc_free_threading_parallel.c` | FT page buckets, pool, propagation, `update_refs`, `mark_heap`, `scan_heap` |
| `Python/gc.c`, `Python/gc_free_threading.c` | Integration with serial fallbacks, lazy start, warnings, timing |
| `Include/internal/pycore_gc_parallel.h`, `pycore_gc_ft_parallel.h` | Collector state and interfaces |
| `Include/internal/pycore_ws_deque.h`, `pycore_gc_barrier.h`, `pycore_gc_random_walk.h` | Shared deque/buffer, barrier, controller |
| `Include/internal/pycore_interp_structs.h` | Per-interpreter parallel-GC state |
| `Include/internal/pycore_dict.h`, `Objects/dictobject.c` | Shared exact-dict traversal macro |
| `Include/internal/mimalloc/mimalloc/internal.h`, `Objects/mimalloc/segment.c` | Abandoned-page enumeration and counts |
| `Include/internal/pycore_uniqueid.h`, `Python/uniqueid.c` | Batched unique-ID release |
| `Python/pylifecycle.c`, `Python/pystate.c`, `Modules/posixmodule.c` | Shutdown and fork recovery |
| `Modules/gcmodule.c`, `Modules/clinic/gcmodule.c.h` | Python API (Clinic output generated) |
| `configure.ac` (+ generated `configure`, `pyconfig.h.in`), `Makefile.pre.in`, `PCbuild/*` | Build option, PGO training, Windows integration |
| `Lib/test/test_gc_*`, `test_parallel_gc_profile.py`, `Modules/_testinternalcapi/test_ws_deque.c` | Tests and test hooks |
| `Tools/build/parallel_gc_profile.py` | Supplementary PGO training |
| `Doc/library/gc.rst`, `Doc/using/configure.rst` | CPython-facing documentation |

At `c67363fa59` the fork differs from its base at 56 paths (40 modified, 16
added). `Include/internal/pycore_global_strings.h` changes only its generated
section (`num_workers`), with matching generated entries in
`pycore_global_objects_fini_generated.h`, `pycore_runtime_init_generated.h` and
`pycore_unicodeobject_generated.h`. `configure` and `pyconfig.h.in` were
regenerated with CPython's pinned Autoconf container. Verify the path set:

```bash
git -C cpython diff --name-status \
    333071231d3a46cccc32d7f44b99328c3299d0b1 \
    c67363fa59543ef5d572383af927f1cff88514a1
```

The path-by-path inventory is in
`SOURCE_INVENTORY.md` (removed; `git show 724b74b:docs/SOURCE_INVENTORY.md`).

---

## 10. Heritage and provenance

Earlier project records attribute worker-pool, barrier and deque heritage to
[CinderX](https://github.com/facebookincubator/cinder) and to the
work-stealing literature:
[Chase and Lev](https://dl.acm.org/doi/10.1145/1073970.1073974) and
[Lê et al.](https://dl.acm.org/doi/10.1145/2442516.2442524). The current code
is integrated separately with both CPython collectors and uses CPython's
threading and atomic abstractions. Exact source revisions, copied portions and
licensing conclusions are not yet mapped; this is an open provenance task
([OPEN_ISSUES.md](OPEN_ISSUES.md) §3), not a verified statement either way.
