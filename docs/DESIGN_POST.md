# Designing a Parallel Garbage Collector for CPython

This project explores parallel cyclic garbage collection in both GIL and
free-threaded CPython. The implementations are stop-the-world collectors:
application threads are paused while the collecting thread and helper threads
perform selected phases.

The current port is published on the fork branch
`SonicField/cpython:parallel-gc-upstream-port` and recorded by the `cpython/`
submodule.

## Scope

Parallel GC is compiled with `--with-parallel-gc` and enabled explicitly with
`gc.enable_parallel()`. Serial collection remains the default.

The two builds parallelise different work:

| Collector | Parallel phases | Serial phases |
|-----------|-----------------|---------------|
| GIL | interpreter-root marking, reference subtraction, reachability marking | `update_refs_with_splits`, list movement, finalization, deallocation |
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
pushes discovered objects directly onto its deque so other workers can steal
them.

The shared barrier infrastructure supports:

- a startup handshake in the GIL worker pool;
- phase boundaries in multi-stage worker-pool operations, including the
  free-threaded `update_refs` initialization and computation stages.

The free-threaded collecting thread participates as worker zero. Therefore a
configured value of four means one collecting thread and three helper threads.

## GIL collector

The GIL implementation works over the generation's linked GC list.

### Reference subtraction

The workers first mark objects reachable from interpreter roots. The
collecting thread then runs `update_refs_with_splits` serially. This initializes
temporary reference counts and records a split vector containing positions in
the GC list. Workers receive contiguous ranges and call `tp_traverse` to
atomically subtract internal references from `gc_refs`.

References can cross worker ranges, so subtraction uses atomic operations even
though application threads are stopped.

### Reachability and list movement

Workers scan their assigned ranges for objects whose residual `gc_refs` show
an external reference and mark their discovered subgraphs. After the helpers
finish, the collecting thread walks the generation and moves objects that
remain marked as collecting to the unreachable list. Finalization and
deallocation remain serial.

### `tp_traverse` calling contract

GIL helpers create and bind persistent `PyThreadState` objects. This is needed
by debug-build reference accounting when a `tp_traverse` implementation calls
`Py_INCREF` or `Py_DECREF`.

## Free-threaded collector

The free-threaded implementation works over mimalloc GC pages and stores
temporary GC state in `ob_tid` and `ob_gc_bits`.

### Root propagation and preparation

Known roots are propagated in parallel using local buffers and Chase-Lev
deques, with a serial fallback. The collector then runs parallel `update_refs`,
including its lazy initialization of referents not found by a heap-page walk.
Its initialization and computation stages are separated by a resized barrier.

After `update_refs`, the collector enumerates non-empty mimalloc GC pages and
assigns them to worker buckets. Pages left behind by exited threads are included
from the interpreter's abandoned-page pool. Ordinary pages are assigned
contiguously for locality; huge pages are distributed round-robin.

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

After marking, the pool runs `scan_heap` in parallel using an atomic page
counter for dynamic distribution. Per-worker results are merged by the
collecting thread. This restores object state, merges reference counts,
rewrites deferred frame references, and builds the unreachable and
legacy-finalizer worklists. Weak-reference handling, finalization, and
deallocation remain serial.

Each parallel phase retains the original serial path as its error or shutdown
fallback.

## Worker selection

The fixed maximum of 16 is an upper bound on threads executing collector work.
A GIL build uses helpers while the collecting thread coordinates them; in a
free-threaded build the collecting thread participates as worker zero. A
shared stochastic hill-climbing controller tries adjacent counts and retains
only improvements, within that bound. The GIL collector's
8192-object split interval creates list waypoints for work partitioning; it is
not a worker-count heuristic.

## Fork safety

The restored design does not install special parallel-GC fork hooks. Fork
behavior therefore remains a validation item; this document does not claim a
pool restart or child-disable protocol that the implementation does not have.

## Atomic operations

The GIL collector atomically clears the collecting bit in `_gc_prev` when a
worker claims an object. A relaxed load avoids an unnecessary read-modify-write
for objects already marked.

The free-threaded marker uses atomic access to `ob_gc_bits`. Atomically clearing
the unreachable bit gives one worker ownership of each newly reachable object.

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

The runtime API takes no worker-count argument. It creates a pool with a fixed
maximum of 16, and the adaptive controller selects the active count for each
collection. There is no environment-variable, `-X`, or `PyConfig` startup
control.

## Design heritage

The worker-pool, barrier, and Chase-Lev deque design draws on
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

No performance claim is made for the current port. New measurements must record
the exact revision, build flags, hardware, affinity and NUMA policy, workload
parameters, samples, and statistic reported. See
[BENCHMARKING.md](BENCHMARKING.md).

The current port has functional build-and-test evidence on Linux AArch64. This
does not imply an AArch64 performance result. macOS and Windows remain
unverified.

Open work includes:

- establishing reproducible current-port performance baselines;
- deciding when parallel dispatch is worthwhile;
- measuring memory cost and pause-time effects;
- extending platform and sanitizer coverage.

Concurrent or incremental collection would require a different design,
including mutation tracking and write barriers; it is not part of the current
implementation.
