# Core-Developer Sprint Readiness Plan

## Goal

Prepare a self-contained working package that two CPython core developers can
clone, build, test, read, modify, and use to discuss the PEP without relying on
conversation history or undocumented local state.

This plan prepares the project for a design and implementation sprint. It does
not claim that the proposal is ready to land in CPython.

Reconciled on 12 October 2026. These nine steps include eventual submission
work; they are not nine prerequisites for an informal engineering discussion.
The [review handoff](REVIEW_HANDOFF.md) is the starting place for Matt and Pablo.
The [handoff reconciliation plan](HANDOFF_RECONCILIATION_PLAN.md) records this
documentation pass and the remaining publication checks.

## Working rules

- Preserve the restored collector design and behavior.
- Do not change atomic ordering without explicit discussion and approval.
- Treat any required adaptation to current CPython as a hard blocker for
  discussion before implementation.
- Keep GIL and free-threaded builds as equal, first-class configurations.
- Write a falsifying test before repairing a behavioral defect whenever
  practicable.
- Make one coherent change per commit. Do not mix documentation, behavior,
  performance tuning, and unrelated cleanup.
- Record exact commands, revisions, results, failures, and skipped checks.
- The assistant may create local commits. Alex performs remote pushes.

## Reconciliation baseline: 12 October 2026

- CPython fork: `SonicField/cpython`, branch `parallel-gc-upstream-port`,
  revision `c67363fa59543ef5d572383af927f1cff88514a1`.
- Parent: `SonicField/parallel_gc`, branch `main`; the pre-handoff committed
  checkpoint is `ce6dcecbdf1ed6fa8270ea1928cd1e339262a784`.
- At reconciliation, parent and CPython had seven and four local commits ahead
  of their origin tracking refs. These counts are historical, not live status.
- Both collectors use lazy transactional startup, warning/serial fallback,
  explicit retry, and armed child-fork recovery.
- Latest project evidence measures GIL collector `669ed6b17e` and FT
  `195830171f`. The later `c67363fa59` changes release-build tests only.
- Current local FT debug, ASan, TSan and optimized lifecycle selections pass.
  Broad full-suite/platform repeats after the FT change remain pending.
- The CI activation contract is repaired. Matrix run `37663869128` passed at
  the preceding published checkpoint; it does not cover the current local work.
- Known source and performance failures remain documented in
  [AUTIT-TODO.md](../AUTIT-TODO.md) and the handoff. Live GitHub status could
  not be retrieved through this environment's destination filter.

Use the parent's `cpython/` gitlink for the source selected by a later checkout.
[VALIDATION.md](VALIDATION.md) is the single entry point for dated test evidence
and pending platform runs; this baseline does not advance when commits are made.

## Readiness steps

### 1. Correct the current CI contract

Update the parent four-configuration workflow so feature-on jobs call
`gc.enable_parallel()` explicitly. Remove every `PYTHON_PARALLEL_GC` setting
and expectation. Verify the fixed ceiling of 16 and initial adaptive count of
4. Add every applicable focused suite, including
`test_gc_parallel_mark_alive`, and run the benchmark-harness unit tests.

Acceptance evidence:

- The workflow builds GIL and free-threaded configurations with and without
  `--with-parallel-gc`.
- Feature-on jobs prove that parallel collection was explicitly enabled.
- Feature-off jobs prove that parallel collection is unavailable.
- The GIL-specific mark-alive suite runs rather than being silently omitted.
- `benchmarks.test_gc_perf_benchmark` passes in CI.

Falsifier: any job relies on an environment variable to activate the
collector, expects `num_workers == 4`, or omits a collector-specific suite.

### 2. Publish and verify the exact two-repository checkpoint

Push the CPython fork first, then push the parent repository containing the
updated submodule pointer. Test the public checkout path from a fresh clone.

Acceptance evidence:

- Both documented revisions exist on GitHub.
- `git clone --recurse-submodules` obtains the documented CPython revision.
- The corrected parent CI runs against that exact submodule commit.
- A reviewer does not need a local patch, hidden branch, or conversation
  instruction to obtain the source.

Falsifier: a fresh clone checks out a different revision, cannot initialize the
submodule, or refers to a commit that is not publicly reachable.

### 3. Replace or retire stale entry-point tooling

Audit the root `Makefile` and every active script under `tools/`. Update tools
that serve the current workflow. Replace obsolete tools with a clear failure
message or remove them when removal is safe and agreed.

The setup path must never check out or pull `python/cpython:main` over the
recorded fork. Build helpers must use out-of-tree directories and the same four
configurations documented in `BUILD_AND_TEST.md`.

Acceptance evidence:

- Every advertised command either performs the current documented operation or
  stops before mutating anything and directs the user to the correct command.
- No setup command changes the submodule branch or revision.
- The Makefile, README, and build guide describe one consistent workflow.

Falsifier: following any advertised quick-start command changes the CPython
checkout, builds without the intended feature flag, or reuses incompatible
objects between configurations.

### 4. Repair resource failure and make pool creation lazy

Both implementations now separate enabled policy from a live pool and use
transactional partial-start rollback with serial fallback and no automatic
retry. GIL repair is `7ec0874a7d`; FT is `195830171f`. Deterministic startup
failure tests and local ASan/TSan evidence exist in both modes. Repeat on the
published checkpoint and retain the separate failed-join policy task (A12).

Design and approve the tests before changing the implementation. The complete
state, failure, fork, test, and performance proposal is in
[`LAZY_POOL_CREATION_PLAN.md`](LAZY_POOL_CREATION_PLAN.md). This direction is
not an authorization to change collector phases, thresholds, or atomic
ordering.

Acceptance evidence:

- Injected thread-creation failure cannot deadlock, join uninitialized handles,
  or leave running helpers referencing freed state.
- Enabling parallel GC creates no helper before a collection selects parallel
  work.
- A failed startup completes the collection serially, warns once, and makes no
  automatic retry.
- Two interpreters can independently arm, collect, disable, and destroy pools
  repeatedly.
- ASan reports no use-after-free for the lifecycle tests.
- Active pools retain the existing collection algorithms and adaptive policy.

Falsifier: enable alone creates a helper, any partial-start path leaves a
helper running, waits on an unreachable barrier count, frees live worker
state, retries automatically, or prevents the serial collection from
completing.

### 5. Create the actual reviewable CPython patch series

Turn `PATCH_SERIES.md` from a proposed ordering into a real review branch. Keep
shared primitives, GIL integration, mimalloc helpers, free-threaded
integration, API/lifecycle, tests, and documentation in reviewable dependency
order. Keep generated output with its authoritative input.

Acceptance evidence:

- Every commit has one reviewable purpose and an accurate message.
- Every applicable commit builds in both GIL and free-threaded modes.
- Feature-off builds remain valid throughout the series.
- The final tree is identical in behavior to the approved source checkpoint,
  except for separately approved and tested repairs.

Falsifier: a reviewer must understand an unrelated collector, generated file,
and API decision simultaneously to review one commit, or an intermediate
commit cannot build in an applicable configuration.

### 6. Produce clean current-revision correctness and performance evidence

Build the final sprint revision from clean source. Run the focused four-build
matrix, broad GIL and free-threaded tests, relevant reference-leak checks, and
the optimized benchmark campaign for both collector builds. Add optimized
feature-off controls to measure compile-time overhead separately from runtime
serial-versus-parallel behavior.

The current offender inventory and evidence-led optimization sequence are in
[`PERFORMANCE_INVESTIGATION_PLAN.md`](PERFORMANCE_INVESTIGATION_PLAN.md).

Acceptance evidence:

- Logs name the exact clean CPython and parent revisions.
- All four debug configurations run the documented focused suites.
- Broad failures, skips, and environmental exclusions remain visible.
- Full GIL and FT ABBA results use the standard documented parameters.
- Optimized feature-off controls are recorded alongside same-binary mode
  comparisons.
- Raw samples and negative regions are retained.

Falsifier: a headline result comes from a dirty or unidentified worktree, a
pre-normalization collector, a debug build, a one-second run, or an
uncontrolled serial/parallel ordering.

### 7. Perform a behavior-preserving readability pass

Make the core source easier for CPython developers to review without changing
collector behavior. Remove demonstrably unreachable or unused implementation
fragments, compiler warnings, stale terminology, audit-marker comments, and
excessive visual separators. Break up presentation only where the resulting
diff remains mechanically reviewable.

Do not combine this step with algorithmic changes. Do not reorder atomics.

Acceptance evidence:

- Feature-on builds produce no project-introduced compiler warnings.
- Every removed function is proven unused and covered by the existing active
  path tests.
- GIL, FT, feature-off, fork, property, and deque tests are unchanged in
  outcome.
- A source-review diff shows presentation changes separately from behavior.

Falsifier: cleanup changes phase boundaries, synchronization, object-state
transitions, atomic operations, fallback behavior, or benchmark results beyond
normal variance.

### 8. Reconcile the PEP, provenance, and sprint agenda

Update the PEP and reviewer documents against the final sprint revision. Add
the missing GIL mark-alive and fork suites to the PEP inventory. Record the
subinterpreter/fork limitation in the PEP Open Issues. Map CinderX-derived code
to exact source revisions and paths and record the licensing conclusion.

Keep undecided policy questions visibly undecided. In particular, separate the
collector proposal from decisions about `gc.get_parallel_stats()`, the
orthogonal `gc.collect_async()`, `parallel_cleanup`, activation policy, and the
fixed ceiling.

Acceptance evidence:

- The PEP, architecture, source inventory, decision list, and submodule pointer
  name the same revision and behavior.
- Every consequential PEP claim points to code, a test, benchmark evidence, or
  an explicit open issue.
- The sprint agenda states the decisions core developers are being asked to
  make and the evidence relevant to each decision.
- Provenance can be checked without guessing which CinderX code was used.

Falsifier: the PEP presents an unresolved API as settled, omits a known failure,
attributes older performance results to current source, or relies on vague
heritage language where exact provenance is available.

### 9. Track landing gates separately from sprint readiness

Do not block design discussion on work that is specifically required for
landing. Maintain a separate visible gate list covering:

- ThreadSanitizer in both active collector builds;
- feature-on Linux x86-64, native Windows, and native macOS validation;
- final clean broad-suite results;
- an agreed public API and activation policy;
- a CPython issue, PEP number and process metadata when appropriate;
- a NEWS entry tied to the real issue; and
- any additional requirements identified by core developers.

Acceptance evidence:

- Sprint-readiness documents never claim landing readiness.
- Every landing gate has a state: not started, blocked, in progress, passed, or
  explicitly rejected with a reason.
- Negative and unavailable results remain visible.

Falsifier: the project is described as submission-ready while any required
platform, sanitizer, provenance, API, or process gate is unknown.

## Progress table

| Step | Status | Evidence or blocker |
|------|--------|---------------------|
| 1. Correct CI | Implemented; current repeat pending | Explicit activation and four configurations; prior matrix `37663869128` passed. |
| 2. Publish checkpoint | Pending current publication | Current local commits and this handoff need review/push; fresh public clone unverified. |
| 3. Tooling | Deferred, disclosed | README directs readers to explicit commands; legacy Makefile/tools remain. |
| 4. Failure paths and ownership | Startup implemented; join policy open | Both-mode all-position injection and local sanitizers; A12 remains unresolved. |
| 5. Patch series | Future submission work | Proposed dependency order exists; current history remains snapshot plus incremental commits. |
| 6. Current evidence | Partial | GIL/FT optimized project results and FT lazy pyperformance recorded; broad current/platform repeats and feature-off optimized controls pending. |
| 7. Readability | Deferred | Warnings/dead alternatives and explanatory comments remain audit work; no behavior-changing cleanup authorized. |
| 8. PEP and provenance | Handoff docs reconciled; provenance open | New discussion draft selected; exact heritage/licensing and public API decisions remain. |
| 9. Landing gates | Tracked separately | See gate table below; informal discussion does not claim all gates passed. |

## Landing gate status at this checkpoint

| Gate | State | Evidence or missing work |
|------|-------|--------------------------|
| GIL and FT ASan/TSan | Passed local selections; wider coverage pending | Lazy-pool record names selections, revisions and options. Phase allocation failures remain untested. |
| Linux AArch64 correctness/performance | Partial | Local focused/sanitizer and optimized evidence; latest broad FT repeat pending. |
| Linux x86-64 and Windows | Passed earlier checkpoint; current repeat pending | Full runs `37615265794`/`37615268403` at `d396f837b9`. |
| Native macOS active collector | Not started | Standard feature-off workflow is not active-GC evidence. |
| Source failure policies | In progress | A5/A6/A7/A8/A12 remain; scan rollback is still a hypothesis. |
| Performance limits and adaptation | Open | Known regressions, no global-optimum/convergence claim, no agreed overhead limit. |
| Current GIL full pyperformance | Pending | Full sweep predates lazy startup; focused SQLite after startup change is neutral. |
| Optimized feature-off controls | Pending | PGO-training controls do not measure compile-time feature overhead. |
| Extension compatibility and provenance | Pending | Agree traversal test set and exact copied-source/licensing mapping. |
| Public API/process metadata/NEWS | Pending | Discussion PEP provisional; no issue/PEP number or upstream PR created here. |

## Progress log

Add one dated entry after each material experiment, decision, commit, or
blocked result. Each entry must record:

- the step served;
- the hypothesis or acceptance condition;
- the exact command or review procedure;
- the observed result;
- the interpretation and remaining uncertainty; and
- the relevant commit or CI run identifier.

### 2026-10-01: readiness audit converted into an execution plan

- Step served: all nine readiness steps.
- Procedure: compared the source, tests, automation, documentation, recorded
  evidence, and repository state with the project's verifiable-practice
  criteria.
- Result: identified nine distinct bodies of work and recorded a falsifier and
  acceptance evidence for each.
- Remaining uncertainty: none of the nine steps has yet passed its acceptance
  conditions.
- Commit: recorded by the commit containing this document.

### 2026-10-01: first corrected four-build CI run

- Step served: 1, correct the current CI contract.
- Hypothesis: explicit runtime activation, fixed-ceiling assertions, complete
  focused-suite selection, and benchmark-harness tests accurately represent
  the restored collector contract.
- Procedure: GitHub Actions run
  [36844525501](https://github.com/SonicField/parallel_gc/actions/runs/36844525501).
- Result: runtime configuration verification passed in all four jobs and the
  free-threaded feature-on job passed completely. Both feature-off jobs found
  tests that treated API presence as feature availability. A setup-time skip
  also leaked disabled ordinary-GC state into `test_capi.test_misc`. The GIL
  feature-on job reached the newly selected mark-alive suite but its stochastic
  worker-transition test exceeded the three-minute timeout.
- Interpretation: the activation contract is correct; test isolation and
  deterministic dispatch coverage required repair before the matrix could be
  accepted.
- Repair: CPython commit `ef4a380032` uses configuration availability guards,
  avoids mutation before a setup skip, and replaces performance-dependent
  stochastic dispatch coverage with deterministic real-collector dispatches
  at 2, 4, 8, and 16 workers.
- Local verification: the exact GIL feature-on, FT feature-on, GIL feature-off,
  and FT feature-off test sequences passed. The respective totals were 572,
  635, 528, and 593 tests. The benchmark harness passed 6/6 with all four
  binaries.
- Remaining uncertainty: the repaired matrix has not yet run on GitHub.

### 12 October 2026: informal-review handoff reconciliation

- Goal: give Matt and Pablo a reproducible starting place without requiring all
  eventual landing work to finish first.
- Procedure: reread VP, inspect source lifecycle/configuration/controller and
  the upstream-base path diff, then compare entry guides, PEP, source audit,
  benchmark reports and CI workflows with those sources.
- Observed gaps: eager FT descriptions, obsolete child recovery, stale
  benchmark headlines, repaired startup defects still listed as open, missing
  PGO/dictionary paths in the inventory, and an unselected newer PEP draft.
- Action: reconcile the parent documents, select the newer discussion draft,
  add the review entry page and record separate local, historical CI and
  current publication states. Collector code and measurements are unchanged.
- Remaining work: evening review/commit, push CPython then parent, verify a
  public recursive clone, repeat matrix and manual Linux/Windows full suites.
- Verification details and final status belong in
  [HANDOFF_RECONCILIATION_PLAN.md](HANDOFF_RECONCILIATION_PLAN.md).
