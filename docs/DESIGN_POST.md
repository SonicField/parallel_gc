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
a worker limit. Serial collection remains the default.

The two builds parallelise different work:

| Collector | Parallel phases | Serial phases |
|-----------|-----------------|---------------|
| GIL | reference subtraction, reachability marking | `update_refs_with_splits`, list movement, finalization, deallocation |
| Free-threaded | `mark_heap` | root propagation, `update_refs`, `scan_heap`, finalization, deallocation |

The free-threaded distinction is important. Its page assignment prepares
`mark_heap`; `update_refs` and `scan_heap` remain serial.

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
- phase boundaries in multi-stage worker-pool operations. The current
  free-threaded collection path parallelises only `mark_heap` and does not use
  the barrier to parallelise `update_refs` or `scan_heap`.

The free-threaded collecting thread participates as worker zero. Therefore a
configured value of four means one collecting thread and three helper threads.

## GIL collector

The GIL implementation works over the generation's linked GC list.

### Reference subtraction

The collecting thread first runs `update_refs_with_splits` serially. This
initializes temporary reference counts and records a split vector containing
positions in the GC list. Workers then receive contiguous ranges and call
`tp_traverse` to atomically subtract internal references from `gc_refs`.

References can cross worker ranges, so subtraction uses atomic operations even
though application threads are stopped.

### Reachability and list movement

Workers scan their assigned ranges for objects whose residual `gc_refs` show
an external reference and mark their discovered subgraphs. After the helpers
finish, the collecting thread walks the generation and moves objects that
remain marked as collecting to the unreachable list. Finalization and
deallocation remain serial.

### `tp_traverse` calling contract

Both parallel GIL phases invoke type-provided `tp_traverse` functions on helper
threads without attaching Python thread states. Current CPython C-API
documentation explicitly allows `tp_traverse` to be called from any thread and
states that only one thread state is attached while traversal handlers run
during garbage collection. The collecting thread remains that attached thread.

## Free-threaded collector

The free-threaded implementation works over mimalloc GC pages and stores
temporary GC state in `ob_tid` and `ob_gc_bits`.

### Serial preparation

Root propagation remains serial. The collector then runs serial `update_refs`,
including its lazy initialization of referents not found by a heap-page walk.

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
gives exactly one worker ownership of each newly reachable object. An atomic
outstanding-work count prevents termination while a scanner or queued object
can still publish more work.

### Serial scan and cleanup

After the helpers finish, the collecting thread runs serial `scan_heap`. This
restores object state, merges reference counts, rewrites deferred frame
references, and builds the unreachable and legacy-finalizer worklists.
Weak-reference handling, finalization, and deallocation also remain serial.

Keeping these phases serial preserves the current collector's ordering and
state-restoration behavior while the proposal concentrates parallelism in the
transitive marking phase.

## Worker selection

The configured count is an upper bound on threads executing collector work.
A GIL build uses helpers while the collecting thread coordinates them; in a
free-threaded build the collecting thread participates as worker zero. A
collection activates at most one worker per 8192 candidate objects. This grain
is provisional until benchmark evidence can support a final policy.

## Fork safety

A process must not fork while helper threads are active and then use inherited
synchronization state as though those threads survived. The lifecycle hooks use
the following protocol:

1. Before `fork()`, quiesce and stop the parallel worker pool.
2. In the parent, try to restart the previous pool.
3. If the parent cannot recreate helpers, preserve the successful fork and
   disable parallel GC rather than surfacing an unrelated failure.
4. In the child, leave parallel GC disabled. Do not create threads in the
   post-fork handler.
5. The child may create a fresh pool later through
   `gc.enable_parallel(workers)`.

## Atomic operations

The GIL collector atomically clears the collecting bit in `_gc_prev` when a
worker claims an object. A relaxed load avoids an unnecessary read-modify-write
for objects already marked.

The free-threaded marker uses atomic access to `ob_gc_bits`. During the
stop-the-world phase only GC workers modify these bits. Two workers may both
decide to traverse an object, but they store the same marking state and later
checks stop duplicate propagation.

Memory-ordering comments in the implementation are correctness documentation,
not performance claims. Any change to those operations should be reviewed
against both x86-64 and weakly ordered architectures such as AArch64.

## Runtime API

```python
import gc

gc.enable_parallel(4)
gc.get_parallel_config()
gc.collect()
gc.disable_parallel()
```

The configuration reports availability, whether the collector is enabled, and
the currently selected worker count.

The command-line and environment forms are:

```bash
./python -X parallel_gc=4 script.py
PYTHON_PARALLEL_GC=4 ./python script.py
```

Startup values are either zero (disabled) or 2 through 64. A nonzero request
fails interpreter initialization when the build does not include
`--with-parallel-gc`; zero remains valid.

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
