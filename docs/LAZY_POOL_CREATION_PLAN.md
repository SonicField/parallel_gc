# Lazy Parallel-GC Pool Creation Plan

## Decision

Both collector implementations will separate enabling parallel-GC policy from creating helper threads.

`gc.enable_parallel()` will arm parallel GC without creating a worker pool. The pool will be created lazily when a collection first reaches the point at which the current implementation would dispatch parallel work. After successful creation, the pool remains persistent and is reused by later collections.

If pool creation fails, the partial pool will be cancelled and completely reclaimed. The current collection will finish through the existing serial collector. The runtime will emit one warning after collection is back in a safe state, record the failure, and make no automatic startup attempt during later collections. The process remains on the serial path until an explicit later `gc.enable_parallel()` request.

This decision applies to GIL and free-threaded builds. It does not change collection coverage, generation selection, the GIL candidate threshold, the FT phase algorithm, the adaptive random walk, atomic ordering, barriers used by active phases, or object-lifecycle semantics.

## Evidence

The complete PGO-trained ABBA campaigns found `sqlite_synth` 38.1% slower with parallel GC enabled in the GIL build and 10.4% slower in the free-threaded build.

A fixed-loop diagnostic then established:

- The measured workload performed no cyclic collection.
- Disabling automatic GC did not remove the slowdown.
- Enabling and then disabling the pool retained the slowdown.
- One unrelated Python thread reproduced 38.9% slowdown in the GIL build and 11.4% in the FT build without enabling parallel GC.
- Creating 15 unrelated threads added no material cost beyond creating one.
- glibc's `__libc_single_threaded` flag changed from 1 to 0 after either helper-pool creation or one unrelated thread and remained 0 after those threads exited.

The diagnostic is recorded in [`sqlite-thread-transition-2026-10-07.md`](../benchmarks/results/pyperformance/investigations/sqlite-thread-transition-2026-10-07.md).

## GIL implementation result

The GIL phase is implemented in CPython commit `7ec0874a7d`. The
free-threaded collector remains eager and is still governed by the plan below.

The GIL implementation provides the explicit five-state lifecycle,
transactional startup, serial failure recovery, bounded diagnostics, explicit
retry, and armed-child fork recovery described here. Deterministic tests fail
each of the 16 worker-thread-state creation positions and each of the 16 native
thread creation positions. Tests also cover resource failure, exact threshold
behavior, repeated active-pool reuse, warning failure, shutdown in every stable
state, and forks from ordinary code, a GC start callback, and a finalizer.

Verification completed locally:

- GIL debug focused suite: 222 tests run, 59 expected skips, success.
- GIL broad suite with the documented unavailable-dependency exclusions:
  48,224 tests across 486 files, 3,518 skips, success.
- Free-threaded debug focused suite: 174 tests run, 26 expected skips,
  success; no free-threaded behavior was changed.
- Free-threaded broad suite with the documented unavailable-dependency
  exclusions: 48,041 tests across 484 files, 3,507 skips, success.
- Parent benchmark-harness suite in the pyperformance environment: 40 tests,
  success.
- GIL AddressSanitizer lifecycle and fork suites: 26 tests, one expected skip,
  success.
- GIL leak-hunting lifecycle repetitions: `[1, 0, 0]`, reported by the CPython
  runner as acceptable.
- PGO+LTO boundary observation: 16,383 candidates retained one OS thread;
  16,384 candidates started 16 helpers; disable returned the process to one.

The rigorous PGO+LTO `sqlite_synth` ABBA result was 1.421316 microseconds with
parallel GC disabled and 1.429422 microseconds while armed. The 0.57 percent
difference was not significant. A separate 131,072-loop observation remained
at one OS thread and `pool_active == false` throughout. This rejects the former
38.1 percent eager-start penalty for this workload. Raw results, combined
files, comparison, executable hash, and repository states are in
[`gil-lazy-pool-sqlite-abba-2026-10-07`](../benchmarks/results/pyperformance/investigations/gil-lazy-pool-sqlite-abba-2026-10-07/).

The remaining acceptance work is Linux and Windows CI, first-use and
steady-state large-graph performance, and the separate free-threaded
lazy-start implementation and evidence.

Before commit `7ec0874a7d`, the GIL startup failure path was incomplete. If
thread creation failed after workers entered the fixed startup barrier, those
workers waited for participants that were never created and cleanup could
deadlock while joining them. Worker thread-state creation failure only printed
a warning and allowed startup to continue. The transactional implementation
replaces that protocol.

Lazy creation must not move that unsafe startup protocol into collection. Transactional startup is a prerequisite.

## Required state model

Each interpreter needs an explicit lifecycle state. Boolean `enabled` plus a nullable pool cannot distinguish the required cases.

| State | Policy requested | Live helpers | Collection behaviour |
|---|---:|---:|---|
| `DISABLED` | No | No | Serial |
| `ARMED` | Yes | No | Attempt lazy startup only when current eligibility rules select parallel work |
| `ACTIVE` | Yes | Yes | Use the existing parallel collector and adaptive controller |
| `FAILED` | No | No | Serial; do not retry automatically |

Pool construction also uses an internal transient `STARTING` state while the lifecycle lock is held. `STARTING` is never reported as enabled or exposed as a stable public state. Fork, disable, interpreter shutdown, and a competing collection must wait until the transaction commits to `ACTIVE` or rolls back to `FAILED`.

State transitions:

| Event | Before | After | Result |
|---|---|---|---|
| `gc.enable_parallel()` | `DISABLED` or `FAILED` | `ARMED` | Clear the per-request failure latch and reset adaptive state; create no thread |
| `gc.enable_parallel()` | `ARMED` or `ACTIVE` | unchanged | No-op |
| Eligible collection, startup succeeds | `ARMED` | `ACTIVE` | Run the current parallel path |
| Eligible collection, startup fails | `ARMED` | `FAILED` | Complete serially, record failure, warn once after safe cleanup |
| Ineligible collection | `ARMED` | `ARMED` | Complete serially without creating a thread |
| `gc.disable_parallel()` | any state | `DISABLED` | Stop live helpers if present; create no thread |

“Stays serial” means no collection retries pool creation after a failure. An explicit later `gc.enable_parallel()` is the only action that clears `FAILED` and permits one new transactional attempt.

## API observability

`gc.get_parallel_config()` must not claim that a failed pool is enabled.

Proposed fields and meanings:

| Field | `DISABLED` | `ARMED` | `ACTIVE` | `FAILED` |
|---|---:|---:|---:|---:|
| `available` | true | true | true | true |
| `enabled` | false | true | true | false |
| `pool_active` | false | false | true | false |
| `num_workers` | 0 | 16 | 16 | 0 |
| `adaptive_workers` | absent | 4 | current value | absent |
| `startup_failed` | false | false | false | true |

`gc.get_parallel_stats()` should add a monotonic `pool_startup_failures` counter and a bounded `last_pool_startup_error` code. It must not retain an exception object or an unbounded platform error string in interpreter state.

The distinction between `ARMED` and `ACTIVE` is required for tests, operations,
fork recovery, and honest diagnostics. The implemented public field names
remain subject to core-developer API review.

## Transactional pool startup

Pool construction must have a single owner and must not publish a usable pool until every required resource and worker is ready.

The common transaction is:

1. Hold the existing per-interpreter lifecycle mutex or equivalent GIL-build serialization.
2. Confirm the state is still `ARMED` and no collection or lifecycle operation has superseded the request.
3. Allocate all pool-owned state, queues, buffers, handles, and synchronization objects.
4. Create every worker `PyThreadState` before starting native helpers where the build permits it.
5. Start helpers one at a time and record the exact number successfully created.
6. Have each started helper report readiness through a cancellable mutex-and-condition handshake, not a fixed-count barrier that cannot complete after partial creation.
7. If all helpers become ready, publish the pool atomically with the lifecycle lock held and transition to `ACTIVE`.
8. On any failure, set the transaction's shutdown flag, wake every started helper, join only recorded handles, delete every created thread state, finalize every initialized primitive, free every allocation, and leave no pool pointer published.
9. Clear the temporary exception after reducing it to a bounded failure code, transition to `FAILED`, and return “parallel unavailable for this collection” to the collector.

No helper may access interpreter pool state after the failed transaction returns. No uncreated handle may be joined. No helper may block on a participant count that includes an uncreated thread.

The GIL and FT implementations may retain separate pool structures and worker entry points. They must implement the same transaction contract and share test terminology and failure codes.

## GIL collection integration

The GIL collector must preserve its existing `_PyGC_MIN_PARALLEL_CANDIDATES` threshold of 16,384 and its existing split-count check.

The armed path must obtain the exact candidate and split information without creating helpers. This requires separating the lightweight split/controller state from native worker startup. It must not add an extra full list traversal merely to decide whether to create the pool.

The intended sequence is:

1. Perform the existing serial `update_refs_with_splits()` traversal using lightweight armed-state storage.
2. If the exact candidate count is below 16,384, run the existing serial remainder and leave the state `ARMED`.
3. If fewer than two usable splits exist, run the existing serial remainder and leave the state `ARMED`.
4. Otherwise attempt transactional pool startup while the collecting thread still owns the GIL and before dispatching any worker phase.
5. On success, execute the existing mark-alive, subtract-refs, and move-unreachable parallel paths without algorithm changes.
6. On failure, execute the existing serial subtract-refs and move-unreachable paths from the current valid collection state.

An application whose GIL collections always remain below the threshold will never create a helper thread and will not trigger glibc's first-thread transition through parallel GC.

## Free-threaded collection integration

The FT collector must attempt lazy startup before stopping the world. `_PyThreadState_New()` and QSBR growth can themselves require stop-the-world coordination, so pool construction inside an already stopped world can deadlock.

The intended sequence is:

1. At the existing serialized collection entry, observe `ARMED` before `_PyEval_StopTheWorld()`.
2. Attempt the transactional FT pool initialization using the current maximum of 16 participants: the collecting thread as worker zero and 15 helpers.
3. On success, transition to `ACTIVE`, then enter the current FT collection and phase-dispatch code unchanged.
4. On failure, transition to `FAILED`, then execute the current serial FT collection.

This plan does not introduce a new FT heap-size threshold or change the minimum adaptive participant count. Whether FT should make a separate serial-versus-parallel eligibility decision is outside this change and requires its own evidence and approval.

## Warning contract

Pool startup failure must not replace a valid serial collection with an exception or abort.

The failure path will:

- finish restoring or completing all collector state;
- restart the world in FT builds;
- clear the collector's `collecting` flag normally;
- emit one `RuntimeWarning` for that explicit enable request after collection is safe;
- suppress and clear any secondary failure produced while formatting or delivering the warning;
- retain the failure counter and code even if the warning cannot be delivered.

Proposed message:

```text
parallel GC worker pool could not be started; parallel GC has been disabled and collection continued serially
```

Warnings machinery must not run while the world is stopped, while GC lists contain temporary flags, or while partially created helpers exist.

## Disable, shutdown, and repeated activation

`gc.disable_parallel()` in `ARMED` state only clears policy and lightweight adaptive state. It does not create a pool in order to disable it.

`gc.disable_parallel()` in `ACTIVE` state retains the existing build-specific teardown policy unless evidence justifies unification: GIL stops helpers and may retain reusable storage; FT stops helpers and destroys its pool. Re-enabling remains lazy in both builds: stopped GIL helpers are restarted only when an eligible collection occurs.

Interpreter finalization must handle all four states. `ARMED` and `FAILED` contain no live helper and require no join. `ACTIVE` uses the current ordered shutdown after the transactional-start invariants are established.

## Fork behaviour

Lazy creation simplifies child recovery and changes the current fork architecture, but only if the fork protocol observes a stable lifecycle state.

Before the operating-system fork, the supported CPython fork path must synchronize with the per-interpreter parallel-GC lifecycle lock. It must not copy an interpreter while its pool state is `STARTING` or stopping. The pre-fork hook waits for that transaction to commit or roll back and holds the lifecycle state stable through the fork boundary.

This lock must be acquired before `PyOS_BeforeFork()` calls `_PyEval_StopTheWorldAll()`. Acquiring it after stopping the world is forbidden: another FT thread could be paused while holding the lifecycle lock, leaving the forking thread waiting forever. The parent releases the lifecycle lock before `_PyEval_StartTheWorldAll()`. The child reinitializes the copied lock, converts the copied stable state according to the table below, and never unlocks a synchronization object whose owner identity came from the parent.

Stable-state transitions are:

| Parent state at fork | Parent after fork | Child after fork |
|---|---|---|
| `DISABLED` | `DISABLED` | `DISABLED` |
| `ARMED` | `ARMED`, same policy state | `ARMED`, adaptive state reset, no pool |
| `ACTIVE` | `ACTIVE`, same pool and adaptive history | copied pool abandoned, then `ARMED` with reset adaptive state |
| `FAILED` | `FAILED` | `FAILED`; an explicit child enable may arm one new attempt |

- The parent retains its state, pool, and adaptive history unchanged.
- A child inheriting `DISABLED` remains `DISABLED`.
- A child inheriting `ARMED` remains `ARMED` and resets adaptive state.
- A child inheriting `ACTIVE` abandons copied helper state, becomes `ARMED`, resets adaptive state, and creates no replacement thread during after-fork recovery.
- A child inheriting `FAILED` remains serial; whether an explicit child `enable_parallel()` may retry follows the ordinary `FAILED` transition.
- A child completing a collection inherited from a finalizer fork finishes that collection serially and does not train the reset controller.

The child needs a per-collection `inherited_collection_serial` latch whenever the fork occurs while `gc.collecting` is set. This includes a fork from a GC start callback while the state is only `ARMED`, not just a fork from a finalizer after parallel phases. The latch prevents lazy startup and every parallel dispatch for the remainder of that inherited collection. Normal collection cleanup clears the latch. A later eligible collection may then start the child's pool transactionally.

Without that latch, a child forked from a start callback could create helpers partway through a collection whose temporary state was copied from the parent. That transition is forbidden.

Child recovery must not allocate a pool or create threads. The existing [`FORK_ARCHITECTURE.md`](FORK_ARCHITECTURE.md) requirement to replace helpers before returning to Python will be revised only after the implementation and fork tests establish this armed-child model.

## Tests written before implementation

Tests must use deterministic internal fault injection. Resource exhaustion must not be simulated by actually exhausting process memory or thread limits in CI.

### State and activation tests

- `enable_parallel()` reports `ARMED`, zero live helpers, initial adaptive count four, and no increase in native or Python thread count.
- Repeated enable in `ARMED` and `ACTIVE` states is a no-op.
- Disable from `ARMED`, `ACTIVE`, and `FAILED` reaches `DISABLED` without leaks.
- Explicit enable from `FAILED` permits exactly one new startup attempt.

### GIL eligibility tests

- Repeated sub-16,384-candidate collections remain serial and create no helper.
- A collection at the exact threshold attempts startup once.
- A collection with insufficient splits remains serial and armed.
- After successful startup, later eligible collections reuse the same helpers.

### FT lazy-start tests

- Enable alone creates no helper.
- The first collection attempts startup before stop-the-world entry.
- Successful startup preserves current phase results, participant counts, and adaptive persistence.

### Failure injection tests for both builds

- Fail each pool allocation site independently.
- Fail each worker thread-state creation index independently.
- Fail native thread creation at the first, middle, and last helper.
- Delay started helpers at each startup boundary while failure and cancellation occur.
- Assert bounded completion with a watchdog; a deadlock is a test failure.
- Assert that only successfully created handles are joined.
- Assert zero live helpers, zero published pool, and valid interpreter thread-state lists after failure.
- Assert that the triggering collection returns the same collected count and leaves the same reachability result as serial collection.
- Assert one warning, one failure-counter increment, and no automatic retry on later collections.
- Assert that an explicit later enable can retry and reach `ACTIVE` after fault injection is removed.

### Concurrency and lifecycle tests

- Race enable, disable, and collection from multiple application threads without duplicate startup.
- Pause FT startup at deterministic transaction boundaries, request a supported fork from another application thread, and prove the fork waits for commit or rollback before copying state.
- Instrument fork-hook ordering and prove the lifecycle lock is acquired before stop-the-world and released in the parent before start-the-world.
- Hold the lifecycle lock on a second FT thread while requesting fork and prove the pre-fork path waits while that thread can still run, rather than stopping its owner and deadlocking.
- Finalize interpreters in every state.
- Exercise release and debug builds so worker thread-state requirements are covered.
- Exercise ordinary forks from `DISABLED`, `ARMED`, `ACTIVE`, and `FAILED` parent states and assert the complete state table above.
- Fork from both the start callback and a finalizer in `ARMED` and `ACTIVE` states.
- Assert that an inherited collection performs no startup attempt or parallel dispatch and clears its serial-only latch exactly once at collection exit.
- Verify that the child creates no helper during recovery, completes inherited work serially, and starts lazily on a later eligible collection.
- Retain the documented upstream subinterpreter/fork skip until upstream makes that lifecycle valid.

### Platform tests

- Run GIL and FT feature-on tests on Linux and Windows.
- Run GIL and FT feature-off controls to prove no API or lifecycle change leaks into ordinary builds.
- Run the existing full CPython suites and parent benchmark-harness tests.

## Performance verification

The change is not accepted solely because tests pass.

1. Run a rigorous GIL `sqlite_synth` ABBA comparison between never-threaded disabled and armed-but-unused states. The hypothesis predicts no first-thread transition and therefore no 38% regression.
2. Run the same FT comparison. With no collection, armed FT should also remain never-threaded.
3. Run an already-threaded pool/no-pool ABBA control to estimate incremental pool cost separately from glibc's first-thread transition.
4. Measure the first eligible collection separately from steady-state collections so startup latency is visible rather than averaged away.
5. Repeat the GIL threshold-boundary tests around 16,384 candidates and verify that steady-state large-graph throughput and pauses are unchanged after the pool is active.
6. Repeat the FT exact-container, 500,000-requested-object, mixed-workload, and sustained throughput/pause campaigns.
7. Repeat complete GIL and FT pyperformance ABBA campaigns with the same PGO+LTO build procedure.

The expected result is removal of the first-thread cost from armed-but-unused workloads, not concealment of startup latency. The first-use measurement must report the complete pool-creation cost.

## Documentation consistency

The following documents must remain synchronized with the implemented
behavior:

- `README.md` and `docs/GETTING_STARTED.md` for user-visible enable/disable behaviour;
- `docs/ARCHITECTURE.md` and `docs/DESIGN_POST.md` for state and startup sequencing;
- `docs/FORK_ARCHITECTURE.md` for armed child recovery without replacement threads;
- `docs/CORE_DEV_DECISIONS.md` for the approved failure and retry contract;
- `docs/SOURCE_INVENTORY.md` and `docs/PATCH_SERIES.md` for changed ownership and review order;
- the active PEP draft for lazy persistence, observability, failure, and fork semantics;
- `docs/TESTING.md` for fault-injection and threshold-boundary commands.

No document should state that GIL `gc.enable_parallel()` returns only after a
complete pool exists. The free-threaded implementation is still eager.

## Atomic implementation sequence

1. Add the approved state contract and deterministic internal startup-failure controls, with tests written first and committed only when green.
2. Make GIL startup transactional without changing eager timing; prove every injected partial failure cleans up.
3. Make FT startup expose the same transaction and failure codes; retain its currently safe partial-start cleanup.
4. Add GIL armed state and lazy threshold-triggered startup; run focused correctness and threshold performance tests.
5. Add FT armed state and pre-stop-the-world lazy startup; run focused correctness and phase-result tests.
6. Change child fork recovery from eager replacement to armed lazy recovery in a separate commit with ordinary and finalizer-fork tests.
7. Update API diagnostics, warning delivery, documentation, PEP text, and test commands.
8. Rebuild PGO+LTO GIL and FT binaries and run the complete performance and regression evidence.

Each source commit must preserve the existing algorithms and atomic order. Any required algorithm change, threshold change, or atomic-order change is a hard blocker for discussion rather than an implementation detail.

## GIL decisions applied

The GIL implementation applies the following agreed decisions:

1. An explicit enable after `FAILED` becomes `ARMED` and permits one retry.
2. Configuration uses `pool_active` and `startup_failed`; statistics use
   `pool_startup_failures` and `last_pool_startup_error`.
3. GIL disable stops helpers and may retain reusable pool storage.
4. The one-time warning is delivered after the collecting flag is cleared; a
   warning-delivery exception is cleared.
5. The first eligible collection starts the pool and uses it immediately.
6. An `ACTIVE` GIL child becomes `ARMED`; an inherited collection is forced
   serial through cleanup. GIL lifecycle transitions are serialized by the
   GIL, so the free-threaded pre-fork lifecycle-lock work remains separate.
