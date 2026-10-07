# Parallel GC Fork Architecture

## Status and purpose

This document defines the required `fork()` behavior of the parallel garbage
collectors. It is both an implementation guide and a permanent record of the
reasoning behind the lifecycle protocol.

The design applies to the GIL and free-threaded implementations when parallel
GC has been enabled. It covers forks made through CPython's supported
`PyOS_BeforeFork()`, `PyOS_AfterFork_Parent()`, and
`PyOS_AfterFork_Child()` protocol, including `os.fork()`.

It does not attempt to make a raw `fork()` call from an extension safe. Such a
call bypasses CPython's existing lock and thread-state recovery as well as the
parallel-GC protocol.

## The problem

Both collectors use persistent native worker threads after their pools have
started. A GIL collector may instead be armed with no helpers. A POSIX fork
duplicates memory but retains only the calling thread in the child. Without
explicit recovery, a child of an active pool inherits:

- worker handles for threads that no longer exist;
- worker `PyThreadState` pointers that CPython removes after the fork;
- mutexes, condition variables, barriers, and semaphores whose copied state
  refers to vanished waiters;
- dispatch counters and work queues prepared for the old process; and
- adaptive measurements learned from the parent's workload.

The parent does not have this problem. Its address space and helper threads
continue to exist after the fork.

A child that dispatches work through the inherited pool can wait forever for
workers that cannot report completion. This applies even when the fork occurs
between collections. Forking from a finalizer is an additional case because
the child resumes part-way through the collection that invoked the finalizer.

## Required behavior

### Parent process

The fork must not replace, stop, or restart the parent's GC helpers. Its pool,
adaptive state, statistics, and current configuration remain unchanged.

CPython stops the Python world before taking the process snapshot. At that
point the parallel-GC pool must not have a dispatch in progress. The parent can
resume the world and continue using the existing pool after the fork.

### Child process

The child must never dispatch through synchronization or thread state copied
from the parent. Before Python execution resumes, child recovery must:

1. Confirm that no parallel phase was active at the fork boundary.
2. Discard inherited thread handles and worker `PyThreadState` pointers.
3. Reinitialize every pool synchronization primitive and dispatch counter.
4. Reset all worker queues and per-dispatch state to an empty, idle state.
5. Preserve whether parallel GC was enabled and preserve the configured
   maximum of 16 workers.
6. Reset the adaptive controller for the child's workload.

The GIL implementation then leaves the child `ARMED`. It creates no native
thread during after-fork recovery; a later eligible collection starts a new
pool transactionally. A child of `ARMED` remains armed, a child of `DISABLED`
remains disabled, and a child of `FAILED` remains failed until an explicit
enable request.

The free-threaded implementation currently creates replacement helpers during
after-fork recovery. If that replacement fails, CPython's recovery fails
fatally rather than return to Python with a partially live pool. Converting the
free-threaded implementation to the GIL armed-child model is planned but is
not part of the current GIL change.

## Adaptive state

The parent retains its complete adaptive state. The child starts a new
learning history because child processes commonly perform different work from
their parents.

Child recovery resets:

- active workers to `min(4, maximum_workers)`;
- the previous normalized collection cost to zero;
- pending trial and rollback state;
- the random-walk generator seed; and
- any per-collection timing that began before the fork.

A collection that began in the parent and resumed in the child must not train
the child's new controller. The first adaptive measurement in the child comes
from a collection begun after child recovery.

## Forks during garbage collection

Parallel phases do not invoke Python callbacks. Supported Python-level fork
sites therefore occur while the helpers are idle. They include:

- a `gc.callbacks` start or stop callback;
- a weak-reference callback;
- `tp_finalize` or Python `__del__`;
- destruction triggered during serial cleanup; and
- ordinary application code between collections.

When a finalizer calls `fork()`, the calling thread survives in both processes.
The parent completes the collection with its existing pool. The GIL child
reinitializes its controller without creating helpers, then completes the
inherited collection's remaining work serially. A per-collection latch also
forces serial completion after a fork from the start callback, where no
parallel phase has run yet. Normal collection exit clears the latch. The
free-threaded child completes the inherited serial tail after replacing its
helpers. In both implementations, the inherited collection is excluded from
adaptive learning.

The implementation must not assume that `gcstate->collecting` is clear during
child recovery.

## Hook ordering

The lifecycle integrates with CPython's fork protocol as follows:

```text
calling thread                 parent                       child
--------------                 ------                       -----
PyOS_BeforeFork()
  stop Python world
  verify GC dispatch idle
fork()
                               existing helpers survive     helper threads absent
PyOS_AfterFork_Parent()         resume world
                                                            reinitialize runtime locks
                                                            remove vanished thread states
                                                            recover parallel-GC state
                                                            reset adaptive state
                                                            GIL: remain armed
                                                            FT: create child helpers
                                                            resume Python execution
```

Child pool recovery must run after CPython has reinitialized its fundamental
thread machinery and detached vanished thread states. It must run before those
states are destroyed, because their destruction may invoke destructors, and
before user after-fork callbacks or other Python code can request a collection.

## Implementation boundaries

The common lifecycle entry points belong in CPython's internal GC interfaces.
The GIL and free-threaded collectors retain separate recovery code because
their worker topology and current startup policy differ:

- every GIL pool worker is a helper thread;
- free-threaded worker zero is the collecting thread and workers 1 through 15
  are helpers.

The two paths share the adaptive reset definition and parent-preservation
contract. Recovery must not alter collection algorithms, atomic ordering, work
partitioning, or the parent process's controller state.

## Existing multi-interpreter boundary

The kernel initially copies every interpreter into the child, but CPython's
after-fork recovery deliberately deletes every interpreter except the main
interpreter before returning to Python. Parallel-GC recovery therefore
recovers only the surviving main interpreter's controller. The GIL path does
not build a pool at this point.

Current upstream-based feature-off GIL and free-threaded builds terminate the
child with `SIGSEGV` when the main interpreter forks while an otherwise idle
legacy subinterpreter exists. The same failure occurs without a parallel-GC
pool, so it cannot serve as a red test for pool disposal and is not caused by
this project.

If upstream makes that lifecycle valid, a non-surviving interpreter that owns
a parallel-GC pool must mark or abandon the copied pool before normal
interpreter cleanup so cleanup does not signal or join parent-only helpers. It
must not receive replacement helpers because CPython is about to delete it.
That integration should be tested against the corrected upstream lifecycle
rather than changing subinterpreter cleanup in this proposal.

## Verification requirements

Both feature-on builds must exercise these cases in subprocesses with bounded
waits:

1. Fork between collections, then complete a large parallel collection in the
   child.
2. Fork from `__del__`, finish the inherited collection, then complete a new
   large collection in the child.
3. Verify that the parent retains its adaptive worker count and previous cost.
4. Verify that the child begins at four workers with no previous cost.
5. In the GIL build, verify that child recovery creates no helper and that the
   controller remains armed until an eligible collection.
6. Verify that the inherited collection does not update child adaptive state
   or dispatch GIL helpers.
7. Verify that a subsequent child collection produces a new adaptive
   measurement.
8. Repeat the lifecycle to expose stale handles, queues, and synchronization
   state.

The feature-off GIL and free-threaded builds must retain normal CPython fork
behavior. Platforms without `fork()` skip these tests. Windows pool lifecycle
is unaffected by this POSIX-only recovery path.
