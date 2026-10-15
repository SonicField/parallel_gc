# Designing a Parallel Garbage Collector for CPython

This project explores parallel cyclic garbage collection in both GIL and
free-threaded CPython. The implementations are stop-the-world collectors:
application threads are paused while the collecting thread and helper threads
perform selected phases.

The current port is maintained on the fork branch
`SonicField/cpython:parallel-gc-upstream-port` and recorded by the `cpython/`
submodule.

## Scope

Parallel GC is compiled with `--with-parallel-gc` and enabled explicitly with
`gc.enable_parallel()`. Serial collection remains the default.

The two builds parallelise different work:

| Collector | Parallel phases | Serial phases |
|-----------|-----------------|---------------|
| GIL, at least 16,384 candidates | interpreter-root pre-marking, reference subtraction, reachability marking | `update_refs_with_splits`, list reconstruction, finalization, deallocation |
| GIL, fewer than 16,384 candidates | none | complete collection |
| Free-threaded | root propagation, `update_refs`, `mark_heap`, `scan_heap` | finalization, deallocation |

The free-threaded collector retains serial fallbacks for its parallel heap
phases. Page assignment prepares per-worker buckets used by `update_refs` and
`mark_heap`; `scan_heap` uses dynamic page distribution.

## Shared infrastructure

Both implementations keep helper threads alive between collections. Dispatch
signals only the active subset of workers, while the remaining workers stay
parked on per-worker condition variables. The collecting thread waits on a
completion condition.

Both builds use a Chase-Lev deque. The GIL path also stages work in a small
local buffer, reducing owner-side deque operations. The free-threaded path
uses deques for work stealing and local staging during root propagation.

The shared barrier infrastructure supports:

- portable mutex/condition operations for a cancellable startup handshake;
- phase boundaries in multi-stage worker-pool operations, including the
  free-threaded `update_refs` initialization and computation stages.

The free-threaded collecting thread participates as worker zero. Therefore an
adaptive value of four means one collecting thread and three helper threads.

## GIL collector

The GIL implementation works over the generation's linked GC list.

### Count, partition, and decide

The collecting thread first runs `update_refs_with_splits` serially. This
initializes temporary reference counts, obtains the exact number of candidate
objects, and records a split vector containing positions in the GC list every
8192 objects. Recording those waypoints during a traversal the collector must
perform anyway avoids a second partitioning pass.

If the generation contains fewer than 16,384 candidates, the collecting thread
uses the upstream serial subtraction and reachability paths. Starting helpers
and changing the traversal to atomic operations is not profitable at that
scale. This is one collection-wide decision rather than a collection of
phase-specific policies, and serial collections do not train the adaptive
worker controller.

### Known-root pre-mark

For a large collection, helpers first mark objects reachable from interpreter
roots. The collecting thread expands the small root set by one level into a
shared block queue so that workers receive many independent starting points,
then each worker closes over its own local buffer and private deque. Workers do
not steal in this phase.

Pre-marking is an optimization: it allows later subtraction and reachability
passes to skip the usually large reachable subgraph. It does not replace the
reference-difference algorithm. Every worker must drain its local buffer and
deque before completing because they contain borrowed object pointers and are
reused across collections.

### Reference subtraction

Workers receive contiguous split-vector ranges and call `tp_traverse` to
atomically subtract internal references from `gc_refs`.

References can cross worker ranges, so subtraction uses atomic operations even
though application threads are stopped.

### Reachability and list movement

Workers scan their assigned ranges for objects whose residual `gc_refs` show
an external reference and mark their discovered subgraphs. Segment ownership
partitions root discovery; an atomic collecting-bit transition gives one
worker ownership of each shared descendant. These GIL phases deliberately use
worker-private queues without stealing.

After the helpers finish, the collecting thread reconstructs the doubly linked
GC lists and moves objects that remain marked as collecting to the unreachable
list. Keeping list mutation serial preserves one ordering and repair protocol.
Weak-reference handling, finalization, resurrection handling, and deallocation
then follow the upstream serial collector.

### `tp_traverse` calling contract

GIL helpers create and bind persistent `PyThreadState` objects. This is needed
by debug-build reference accounting when a `tp_traverse` implementation calls
`Py_INCREF` or `Py_DECREF`.

## Free-threaded collector

The free-threaded implementation works over mimalloc GC pages and stores
temporary GC state in `ob_tid` and `ob_gc_bits`.

### Root propagation and preparation

Known roots are propagated in parallel using local buffers and Chase-Lev
deques, with a serial fallback. This ALIVE pass is only an optimization because
known roots do not include every possible extension-held root. Its relaxed,
idempotent marking may allow duplicate traversal; that is safe in this pass and
avoids an atomic read-modify-write per object.

The collector then enumerates non-empty mimalloc GC pages and assigns them to
worker buckets before parallel `update_refs`. Pages left behind by exited
threads are included from the interpreter's abandoned-page pool. Ordinary
pages are assigned contiguously for locality; huge pages are distributed
round-robin so one large page does not dominate one bucket.

Parallel `update_refs` has two barrier-separated page passes. Every worker
first marks its objects unreachable and initializes temporary reference state;
only after all workers cross the barrier may they compute adjusted counts and
atomically subtract cross-page references. The barrier prevents an edge from
being subtracted before the target page has been initialized.

The collector then scans thread stacks serially to account for deferred
references before dispatching parallel `mark_heap`.

### Parallel `mark_heap`

Each worker scans its assigned pages for roots: objects whose temporary
reference count is nonzero, plus deferred-reference objects that must be kept
alive. Claiming a reachable object atomically clears its
`_PyGC_BITS_UNREACHABLE` bit.

Workers traverse claimed objects using Chase-Lev deques. A worker that
exhausts its own deque attempts to steal from the others. Atomic bit clearing
gives exactly one worker ownership of each newly reachable object. After
exhausting available work, a worker performs repeated idle rounds before
leaving the phase; a shared error flag terminates unsuccessful work.

### Parallel scan and serial cleanup

After marking, the pool runs `scan_heap` in parallel. Per-worker results are
merged by the collecting thread. This restores object ownership state, handles
deferred-reference state, builds the unreachable and legacy-finalizer
worklists, counts live objects, and batches unique-ID release.

The collector then preserves the upstream schedule: it finds weak references,
resumes application threads for pending decrefs, callbacks, and finalizers,
stops the world again for resurrection handling, weak-reference clearing, and
free-list clearing, resumes it, and finally breaks cycles with `tp_clear`.
These serial tails can dominate a finalizer-heavy workload even when the
parallel heap phases improve.

Each parallel phase retains the original serial path as its error or shutdown
fallback.

## Worker selection

The fixed maximum of 16 is an upper bound on threads executing collector work.
A GIL build uses helpers while the collecting thread coordinates them; in a
free-threaded build the collecting thread participates as worker zero. A
shared stochastic random-walk controller starts at four. On each accepted
count it refreshes the measured cost and has a 20% chance to try `N-1` or
`N+1` with equal probability. The following valid collection keeps the trial
only if its elapsed cost per work unit improves; otherwise it walks back to the
previous count. The accepted count persists between collections and is bounded
to 2--16. The GIL collector's
8192-object split interval creates list waypoints for work partitioning; it is
not a worker-count heuristic.

The private adaptive timing intentionally runs from each implementation's
internal collection start point through the serial post-delete cleanup
boundary, because the objective is broader collection cost rather than
helper-only speed. Both collectors pass elapsed nanoseconds and their exact
candidate count to the same shared normalization function.

FT deliberately searches only within parallel execution. Serial can be a
separate local minimum: two participants can be slower than serial while four
are faster than both. A local walk that retreats into serial cannot necessarily
cross that slower intermediate count. Excluding serial avoids this trap;
local minima within 2–16 and noisy samples remain limitations. The controller
does not guarantee discovery of the fastest configuration.

## Fork safety

The parent pool survives a supported CPython fork unchanged. The child cannot
use copied worker handles or synchronization state because the corresponding
threads no longer exist. GIL child recovery therefore abandons copied helpers,
reinitializes the controller in the armed state, and creates no thread. A later
eligible collection starts the replacement pool. Free-threaded recovery uses
the same armed-child contract. Both reset the adaptive controller. A collection
that began before the fork is excluded from the child's new learning history
and completes serially in both implementations. FT fork preparation takes the
lifecycle mutex before stopping the world so its owner can finish; the parent
releases the mutex before resuming the world.

This behavior is exercised for ordinary forks and forks from `__del__` in both
collector builds. [FORK_ARCHITECTURE.md](FORK_ARCHITECTURE.md) is the normative
engineering record.

## Atomic operations

The GIL collector atomically clears the collecting bit in `_gc_prev` when a
worker claims an object. A relaxed load avoids an unnecessary read-modify-write
for objects already marked.

The free-threaded authoritative marker atomically clears the unreachable bit,
giving one worker ownership of each newly reachable object. This is distinct
from the earlier ALIVE optimization's relaxed, duplicate-tolerant marking.

Memory-ordering comments in the implementation are correctness documentation,
not performance claims. Any change to those operations should be reviewed
against both x86-64 and weakly ordered architectures such as AArch64.

## Runtime API

```python
import gc

gc.enable_parallel()
gc.get_parallel_config()
gc.collect()
gc.disable_parallel()
```

The configuration reports availability, whether the collector is enabled, and
the currently selected worker count.

The runtime API takes no worker-count argument. In the GIL build, enable arms
the collector and the first eligible collection creates a pool with a fixed
maximum of 16 helpers. In the free-threaded build, enable also arms without
helpers; the first collection starts 15 helpers before stopping the world
because the collecting thread is participant zero. The
adaptive controller selects the active participant count for each collection.
There is no environment-variable, `-X`, or `PyConfig` startup control.

Thread creation is expensive, so helpers persist after first use. Lazy startup
also avoids glibc's permanent first-thread transition in workloads that arm the
feature but never use it. A failed transaction rolls back, finishes serially,
warns once after safe cleanup and enters FAILED without automatic retry. An
explicit enable permits another attempt. The
[lazy-pool engineering record](LAZY_POOL_CREATION_PLAN.md) contains the state
contract, fault-injection coverage and SQLite evidence.

## Design heritage

Earlier project records attribute worker-pool, barrier and deque heritage to
[CinderX](https://github.com/facebookincubator/cinder) and the work-stealing
literature:

- Chase and Lev,
  [Dynamic Circular Work-Stealing Deque](https://dl.acm.org/doi/10.1145/1073970.1073974)
- Le et al.,
  [Correct and Efficient Work-Stealing for Weak Memory Models](https://dl.acm.org/doi/10.1145/2442516.2442524)

The current implementation is not a direct copy: it is integrated separately
with CPython's GIL and free-threaded collectors and uses CPython's internal
threading and atomic abstractions.

## Evidence and open work

The latest GIL project run at `669ed6b17e` reports a 1.08x collection geomean
across eight requested 500,000-object shapes, with one unstable negative graph
result. Mixed throughput is unchanged and mean callback interval increases 3%.
FT collector `195830171f` reports a 1.24x collection geomean and mixed
throughput improvement of 23.5%, but sustained AI throughput falls 9.9% and its
mean interval rises 116%. FT pyperformance `float` is 10.5% slower. All these
measurements use PGO+LTO on one AArch64 host. See
[BENCHMARKING.md](BENCHMARKING.md) for raw evidence and the distinction between
callback interval and stop-the-world time.

Local Linux AArch64 tests include GIL and FT ASan/TSan selections. Earlier
feature-on Linux x86-64 and Windows workflows passed at `d396f837b9`; current
FT lifecycle changes require repeats. Active macOS evidence remains missing.
See [REVIEW_HANDOFF.md](REVIEW_HANDOFF.md) for the checkpoint and CI limits.

Open work includes:

- repeating both optimized performance runs from clean published commits and
  adding feature-off optimized controls;
- attributing the remaining performance regressions without assuming their
  causes or changing collector policy;
- measuring memory cost and pause-time effects;
- extending platform and sanitizer coverage.

Concurrent or incremental collection would require a different design,
including mutation tracking and write barriers; it is not part of the current
implementation.
