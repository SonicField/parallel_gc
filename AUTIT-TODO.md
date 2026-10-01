# Parallel GC Source Audit TODO

## Purpose

This document records source-quality issues found while reviewing the parallel
GC implementation at CPython revision
`86c83d41f5ae6df6558130b978d1d0a09a036a05`. It exists so that core developers
can see which risks are already known, which have been reproduced, and how we
intend to investigate and repair them.

This is a readiness backlog, not evidence that the collector design is unsound.
The performance design, phase structure, atomic ordering, barriers, work
distribution, and adaptive controller must not be changed as incidental parts
of these repairs. Any proposed change to those behaviours is a hard blocker for
discussion before implementation.

## Audit standard

The review applies the verification-first approach from
[SonicField/verifiable-practice](https://github.com/SonicField/verifiable-practice),
especially its
[Engineering Standards](https://github.com/SonicField/verifiable-practice/blob/main/concepts/engineering-standards.md)
and
[Code Audit playbook](https://github.com/SonicField/verifiable-practice/blob/main/playbooks/code-audit.md).
The exact Verifiable Practice revision used for this review was
`38d28d10035462e4c67f4b08d66638d3a4858216`.

The relevant principles are:

- define how a claim could be falsified;
- demonstrate the pre-fix failure before repairing it;
- make the smallest repair that restores the stated invariant;
- test the real integrated system, especially concurrency and resource
  failure;
- preserve exact commands, revisions, failures, skips, and limitations; and
- do not confuse formatting preferences with correctness findings.

## Summary

| ID | Severity | State | Issue |
|----|----------|-------|-------|
| A1 | BUG | Reproduced | Free-threaded lifecycle APIs race under concurrent use. |
| A2 | BUG | Source-proven | Partial GIL helper creation has no safe rollback. |
| A3 | BUG | Source-proven | Partial free-threaded helper creation frees live state. |
| A4 | BUG | Source-proven | Free-threaded worker arguments have process-global ownership. |
| A5 | BUG | Source-proven | GIL split-vector allocation failures are ignored. |
| A6 | BUG | Source-proven | Free-threaded unique-ID allocation failure is ignored. |
| A7 | BUG | Hypothesis | Free-threaded scan failure may not restore temporary GC state. |
| A8 | HARDENING | Source-proven | A GIL path silently removes a freed GC-list entry. |
| A9 | HARDENING | Confirmed gap | Failure injection and dynamic-analysis coverage are missing. |
| A10 | HARDENING | Reproduced | Added sources contain compiler warnings and unused alternatives. |

`Source-proven` means the unsafe control flow is directly visible but still
needs a checked-in test that demonstrates the failure. `Hypothesis` means the
failure mode is plausible and falsifiable but must not be presented as fact
until fault injection reproduces it.

## A1. Free-threaded lifecycle APIs race under concurrent use

Severity: **BUG**. State: **reproduced**.

The free-threaded implementations of `gc.enable_parallel()`,
`gc.disable_parallel()`, and the pool accessors read and mutate interpreter
pool state without a lifecycle lock. This conflicts with the `gc` module being
declared safe to use without the GIL.

An isolated debug-build probe allowed four concurrent calls to
`gc.enable_parallel()` to complete. Four concurrent calls to
`gc.disable_parallel()` then aborted with assertions including:

```text
unbind_gilstate_tstate: Assertion `tstate == gilstate_get()' failed
PyThreadState_Clear: Assertion `tstate->_status.initialized &&
!tstate->_status.cleared' failed
```

The valid reproducer exited with status 134. Earlier attempts made while two
unintended recursive dry-run build processes were reconfiguring the build
directories are invalid evidence and are not counted.

Falsifying test: start several free-threaded callers at a barrier, concurrently
enable the same interpreter pool, then concurrently disable it. Repeat under a
debug build and TSan. The process must not hang, abort, leak a pool, or clear a
thread state twice.

Acceptance condition: lifecycle operations on one interpreter have a defined
serialization rule, concurrent calls are idempotent, and collection cannot use
a pool while another thread destroys it.

Required discussion: approve the lifecycle synchronization design before code
is changed. This must not silently introduce synchronization into collection
hot paths.

## A2. Partial GIL helper creation has no safe rollback

Severity: **BUG**. State: **source-proven**.

`_PyGC_ParallelStart()` creates helpers in a loop. If creation fails, already
created helpers remain blocked on a startup barrier sized for the complete
pool. The caller invokes `_PyGC_ParallelFini()`, which eventually attempts to
join every configured handle, including handles that were never initialized.

The source comment that thread-creation failure is fatal does not make the
cleanup safe: `gc.enable_parallel()` reports an ordinary Python exception and
continues running the interpreter.

Falsifying test: inject failure after each possible successful helper creation.
Each case must return an exception within a bounded time, leave no helper
running, join only valid handles, and permit a later successful enable.

Acceptance condition: startup publishes the pool only after every helper is
ready, and every partial state has one bounded rollback path.

## A3. Partial free-threaded helper creation frees live state

Severity: **BUG**. State: **source-proven**.

When free-threaded helper creation fails after one or more successful starts,
the failure path frees the shared argument array, worker states, handles,
synchronization state, and pool. Already-running helpers can still reference
those allocations.

Worker thread-state creation failure is also not reported to the initializer;
a helper can enter service without state that debug reference accounting may
require.

Falsifying test: inject both helper-creation and helper-thread-state failures at
every position. Run the test under ASan and a debug build, with a bounded
timeout.

Acceptance condition: started helpers receive a shutdown signal and are joined
before any referenced storage is released. A pool is not reported as enabled
unless every required helper resource exists.

## A4. Free-threaded worker arguments have process-global ownership

Severity: **BUG**. State: **source-proven**.

`_pool_worker_args` is a file-static allocation, while `_PyGCThreadPool` is
owned by an interpreter. Initializing another interpreter overwrites the
process-global pointer; finalizing either interpreter can free or lose storage
belonging to the other pool. It also makes concurrent initialization race even
before A1 is considered.

Falsifying test: repeatedly create two live interpreters, enable pools in both,
collect in both, and destroy them in both orders. Add a concurrent variant and
run both under ASan and TSan.

Acceptance condition: every allocation needed by a pool is reachable from and
freed by that pool alone. No mutable process-global storage participates in
per-interpreter pool lifetime.

## A5. GIL split-vector allocation failures are ignored

Severity: **BUG**. State: **source-proven**.

`update_refs_with_splits()` ignores all three forms of
`_PyGCSplitVector_Push()` failure: the initial boundary, periodic boundaries,
and the exclusive end marker. A failed growth can therefore leave a vector
that has enough entries to look usable but lacks the true end of the GC list.
Parallel `subtract_refs` may then process an incomplete region.

Falsifying test: force split-vector growth and fail the allocation after the
vector already contains multiple entries. Verify that the collection either
uses a complete serial path or fails safely, and that cycles in the unrecorded
tail are not retained or corrupted.

Acceptance condition: an incomplete split vector is never dispatched. The
failure path has explicit semantics and leaves the collector in the same
object-state configuration expected by the selected fallback.

## A6. Free-threaded unique-ID allocation failure is ignored

Severity: **BUG**. State: **source-proven**.

`worker_collect_unique_id()` reports allocation failure, but
`par_disable_deferred_collect_ids()` discards that result after clearing the
unique ID from the object. The ID can then be absent from the later batch
release, leaking the corresponding interpreter resource. The scan work
descriptor's `error_flag` is not set by this path.

Falsifying test: create objects with unique IDs, fail the first allocation and
each growth of a worker's ID array, then verify that every cleared ID is
released exactly once and that object state remains valid.

Acceptance condition: clearing an object's ID and recording or releasing that
ID behave transactionally. Allocation failure cannot silently lose it.

## A7. Free-threaded scan failure may not restore temporary GC state

Severity: **BUG** if reproduced. State: **hypothesis**.

The parallel scan allocates worker state and page arrays after earlier GC
phases have written temporary reference and reachability state into objects.
Several pre-dispatch allocation failures return `-1`. The outer error path
clears alive bits, but it is not yet demonstrated that it restores every
temporary `ob_tid`, unreachable bit, worklist link, deferred-reference change,
and unique-ID change made by preceding phases.

Falsifying test: inject failure at every allocation in
`_PyGC_ParallelScanHeapWithPool()`. After each failed collection, validate heap
invariants and run repeated serial collections, allocations, unique-ID use,
weak references, and object destruction under ASan.

Acceptance condition: either fault injection proves the existing rollback is
complete, closing this item without a source repair, or one explicit rollback
path restores every phase invariant before the world restarts.

## A8. A GIL path silently removes a freed GC-list entry

Severity: **HARDENING** pending a reproducer. State: **source-proven**.

`update_refs_with_splits()` detects `_PyObject_IsFreed(op)`, removes the entry
from the generation list, and continues. A worker path similarly skips freed
objects. The upstream serial collector does not describe this as a recoverable
state. A freed object remaining in a GC list indicates that a fundamental heap
invariant has already been violated.

Continuing silently can conceal the original corruption and make later failure
non-local. Conversely, this check may encode a real requirement learned from a
specific interaction; it must not be removed merely because it looks unusual.

Falsifying investigation: identify the commit and reproducer that motivated
the check. Attempt to reproduce the stale entry in both serial and parallel
modes. Determine whether the state is sanctioned, transient, or corrupt before
choosing assertion, recovery, or removal.

Acceptance condition: the invariant and response are documented and tested.
The collector must not silently normalize unexplained heap corruption.

Required discussion: any behavioral change here requires explicit approval.

## A9. Failure injection and dynamic-analysis coverage are missing

Severity: **HARDENING**. State: **confirmed gap**.

The current tests exercise normal collection, properties, fork recovery,
work-stealing, the adaptive controller, and many graph shapes. They do not
systematically inject helper-creation, thread-state, split-vector, scan-array,
or unique-ID allocation failures. The project also lacks current ASan and TSan
evidence for both active collector builds.

Some tests are weak falsifiers. For example, the statistics test accepts an
unchanged `collections_attempted` counter even though its stated purpose is to
prove that a collection attempt was recorded. `gc.collect_async()` is a new
public API with documentation but no focused tests in the fork delta.

Acceptance condition:

- every resource-failure repair has a deterministic pre-fix failure;
- tests prove that the intended parallel path actually ran;
- `gc.collect_async()` has an agreed scope and falsifiable API tests, or is
  separated from the proposal;
- ASan passes GIL and free-threaded lifecycle and collection tests; and
- TSan results for both builds are recorded, including suppressions and known
  upstream reports rather than hiding them.

## A10. Added sources contain warnings and unused alternatives

Severity: **HARDENING**. State: **reproduced**.

Direct compilation with CPython's normal warning flags reports two
signedness warnings and ten unused functions across the added or modified GC
sources. The unused functions appear to be superseded implementation paths,
including coordinator-based GIL stealing and earlier free-threaded worker
implementations.

This is not a whitespace complaint. Dead alternatives obscure which algorithm
is authoritative, make ownership review harder, and can retain stale claims
about synchronization.

Falsifying review: for each unused function, prove by symbol and call-site
search that it is unreachable in every supported configuration. Compile GIL,
free-threaded, and feature-off configurations after removal.

Acceptance condition: project-added sources compile without project-introduced
warnings, and every removed fragment is shown to be unreachable. Cleanup must
be a separate behavior-preserving commit and must not reorder atomics or alter
phase boundaries.

## Repair plan

### Phase 0: preserve and classify the baseline

1. Record the exact CPython and parent revisions and retain the current passing
   correctness and performance evidence.
2. Turn each issue above into a small testable claim with a bounded timeout and
   an expected pre-fix result.
3. Design debug-only fault-injection hooks for thread creation, worker
   thread-state creation, and selected raw allocations. Review the hooks before
   implementation so instrumentation cannot affect optimized builds.
4. Keep GIL, free-threaded, and feature-off builds in every applicable gate.

Exit criterion: every BUG has a deterministic falsifier or is explicitly
marked as still awaiting one.

### Phase 1: make pool ownership and lifecycle safe

1. Move free-threaded worker arguments into per-pool ownership (A4).
2. Agree and implement free-threaded lifecycle serialization (A1).
3. Implement bounded partial-start rollback for the GIL pool (A2).
4. Implement bounded partial-start rollback for the free-threaded pool (A3).
5. Audit initialization and finalization of every mutex, condition variable,
   barrier, handle, worker state, and Python thread state.
6. Run repeated enable, collect, disable, interpreter-create, and
   interpreter-destroy sequences under ASan and TSan.

Exit criterion: no helper survives a failed enable, no pool frees another
pool's storage, and concurrent public lifecycle calls have tested semantics.

### Phase 2: make collection failure transactional

1. Demonstrate and repair incomplete GIL split-vector handling (A5).
2. Demonstrate and repair unique-ID recording failure (A6).
3. Resolve the scan rollback hypothesis with injection at every allocation
   point (A7).
4. Run post-failure serial and parallel collections repeatedly to detect state
   retained from an aborted phase.

Exit criterion: every injected allocation failure either safely falls back or
returns with all collector invariants restored.

### Phase 3: resolve invariant policy

1. Trace the history and original failure behind the freed-entry handling
   (A8).
2. Reproduce the condition, if possible, without parallel GC as a control.
3. Agree whether it is a valid transient state, a recoverable external defect,
   or heap corruption.
4. Encode the agreed response and a test without changing unrelated collector
   behavior.

Exit criterion: the source no longer contains an unexplained silent recovery
from a fundamental heap-state violation.

### Phase 4: strengthen verification and remove dead alternatives

1. Tighten tests that can pass without exercising their stated behavior.
2. Add or separate `gc.collect_async()` coverage and proposal scope.
3. Remove only proven-unused functions and fix warnings in a standalone
   behavior-preserving commit (A10).
4. Run focused tests, the four-build matrix, broad GIL and free-threaded tests,
   ASan, TSan, and applicable reference-leak checks.
5. Re-run the full optimized GIL and free-threaded ABBA benchmarks to verify
   that safety work did not change throughput, pause behaviour, dispatch
   threshold, or adaptive selection beyond normal variance.

Exit criterion: all accepted findings are closed with evidence; rejected or
deferred findings retain their reasoning and limitations.

## Commit and evidence rules

- Repair one issue, or one inseparable ownership group, per commit.
- Demonstrate the pre-fix failure before writing the repair.
- Keep the focused test with its repair in the final reviewable commit unless a
  separately reviewable test-infrastructure commit is required.
- Do not mix readability cleanup, behavior repair, performance tuning, and
  documentation reconciliation.
- Record exact commands and exit statuses in the sprint progress log.
- Alex performs remote pushes; local commits may be prepared by the assistant.
- Any change to atomic ordering, barrier structure, collector phases, work
  distribution, the 16,384-object GIL threshold, or adaptive-worker behaviour
  requires explicit discussion and approval.

## Current status

The project is aware of these issues and does not claim landing readiness. The
existing implementation remains valuable for design review, performance
analysis, and collaborative work at a core-developer sprint. The issues above
are a prioritized hardening backlog, with known defects clearly separated from
unconfirmed hypotheses.
