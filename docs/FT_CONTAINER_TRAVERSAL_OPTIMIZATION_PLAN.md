# Free-threaded container traversal optimization plan

**Status:** In progress. Steps 0 through 2 are complete; tuple investigation is next.

## Terminal goal

Remove avoidable free-threaded parallel-GC traversal overhead for exact built-in lists, tuples, and dictionaries while preserving the collector's existing behavior and the original parallel-GC design.

The work serves the larger goal: enabling parallel GC should remain cheap on workloads that do not benefit from parallel collection while retaining its large-heap throughput and pause-time gains.

## Method

This plan follows [Verifiable Practice](https://github.com/SonicField/verifiable-practice): state falsifiable claims before changes, separate observation from interpretation, run the smallest discriminating test first, retain negative results, and make each commit represent one independently verified outcome.

Planning does not authorize implementation. The human reviewer approves the acceptance criteria and any design boundary before source changes are retained.

## Repository boundary

- `SonicField/cpython` owns collector source, focused correctness tests, and one atomic implementation commit per specialized container type.
- `SonicField/parallel_gc` owns the performance harness, raw measurements, investigation log, and this plan.
- A parent-repository submodule-pointer update must follow the corresponding CPython commit; it must not hide unrelated parent changes.

## Current state

### Observations

- CPython is at `01a89cbeb8` plus an uncommitted experimental list fast path in `Python/gc_free_threading_parallel.c`.
- The parent repository is at `67c72309211869e2bfdc9c09c383fdae5c584186`; unrelated parent changes remain uncommitted and outside this work's commit boundary.
- The exact experimental diff has SHA-256 `b7520df6e6992d6c41424e82fc20412c785f8ab6099076abf4e8bef9c7f8a976` and is archived with the exploratory results.
- The clean optimized free-threaded baseline measured `gc_traversal` at approximately 2.81 milliseconds with parallel GC enabled and 1.57 milliseconds disabled.
- That benchmark contains approximately 499,500 list edges, most of which are repeated references to objects already marked alive.
- The baseline optimized profile attributed 37.84 percent of samples to `propagate_pool_visitproc`, 20.50 percent to `list_traverse`, and 10.28 percent to `_PyGC_TryMarkAlive`.
- Marking `_PyGC_TryMarkAlive` `Py_ALWAYS_INLINE` removed its standalone symbol but did not improve the result: enabled time remained approximately 2.83 milliseconds.
- The uncommitted exact-list traversal experiment passed the four focused free-threaded parallel-GC test files and measured approximately 1.98 milliseconds enabled and 1.57 milliseconds disabled in one rigorous ABBA campaign.
- Temporary instrumentation observed 508,499 propagation attempts, 6,665 successful first marks, and 501,834 already-alive results.
- CPython's existing `list_traverse` and `tuple_traverse` visit elements in reverse index order. `dict_traverse` has separate split-table, combined-Unicode, and general-key paths.
- A clean optimized free-threaded binary from `01a89cbeb8` completed a rigorous disabled/enabled/enabled/disabled baseline campaign for all five controlled container workloads.
- Both campaign halves reproduced the same result: enabling the unoptimized parallel path made exact-list traversal approximately 1.43-1.44 times slower and exact-tuple traversal approximately 1.38-1.39 times slower. It made split dictionaries approximately 1.26-1.27 times faster and combined-Unicode dictionaries approximately 1.36-1.37 times faster, while making general-key dictionaries approximately 1.08-1.09 times slower.

### Interpretations

- The list result is consistent with callback and generic `tp_traverse` dispatch overhead being a material cost on AArch64.
- The result does not show that atomics or cross-core duplicate successful marking are the dominant cost.
- The list experiment is promising but is not yet a retained optimization: the comparison did not alternate baseline and candidate binaries, and the specialized-path correctness contract has not received dedicated adversarial tests.

### Unknowns

- Whether a baseline-binary/candidate-binary ABBA comparison reproduces the apparent list improvement.
- Whether tuple or dictionary traversal is hot enough in controlled workloads for specialization to have practical value.
- Whether dictionary specialization can reuse existing private traversal machinery cleanly instead of duplicating layout logic.
- Whether any specialization changes a large-heap throughput, pause, or adaptive-worker guardrail.

## Non-negotiable invariants

- Do not change atomic operations or their ordering.
- Do not change phase ordering, work queues, thresholds, worker selection, adaptive state, or serial/parallel selection.
- Do not visit an object that the corresponding existing `tp_traverse` would omit, and do not omit an object it would visit.
- Preserve exact built-in traversal order, null handling, tuple untracking, alive-bit cleanup, and return behavior.
- Specialize only when the resolved traversal function is the exact built-in traversal function. Subclasses, heap types, and types with custom traversal must retain the generic callback path.
- Keep important container hot paths explicit in source. Parallel-aware PGO may optimize the surrounding collector but must not replace or be required for the exact-container specializations.
- When CPython is configured with `--with-parallel-gc`, its normal PGO build must collect representative profiles from the enabled parallel collector in both GIL and free-threaded builds. Runtime activation remains unchanged.
- Do not modify upstream pyperformance benchmarks. Type-specific performance workloads belong to `parallel_gc`.
- Do not accept a speedup that damages GIL behavior, large-heap throughput, pause behavior, adaptive behavior, or correctness.
- If implementation requires a semantic adaptation, atomic change, new object-layout contract, or changed serial behavior, stop and discuss it before coding.

## Claims and falsifiers

### List claim

**Hypothesis:** Directly iterating the elements of an exact built-in list during the stop-the-world propagation phase removes material callback and dispatch overhead without changing traversal semantics.

**Falsified if:** the candidate fails a semantic or sanitizer check; the optimized baseline/candidate ABBA does not improve enabled `gc_traversal` by at least 20 percent in both halves; the disabled control changes materially; final assembly still contains the generic per-edge callback path; or a mandatory guardrail regresses.

The 20 percent threshold is fixed before the confirmatory run because the exploratory result suggested an improvement of roughly 30 percent. It prevents retaining a complex fast path for noise or a marginal gain.

### Tuple claim

**Hypothesis:** Directly iterating exact built-in tuple elements, while preserving `_PyTuple_MaybeUntrack` and alive-bit cleanup, materially reduces traversal cost in a tuple-dominant graph.

**Falsified if:** the pre-change profile does not identify tuple traversal or its callback as a material cost; the candidate fails a semantic or sanitizer check; both ABBA halves do not improve the enabled tuple workload in the same direction; the improvement is less than 5 percent; the disabled control changes materially; or a mandatory guardrail regresses.

### Dictionary claim

**Hypothesis:** A direct exact-dictionary path that reproduces `dict_traverse` for all three storage layouts materially reduces traversal cost in a dictionary-dominant graph.

**Falsified if:** the pre-change profile does not identify dictionary traversal or its callback as a material cost; a faithful implementation would duplicate or expose unsafe layout knowledge without an approved design; any dictionary layout or subclass test fails; both ABBA halves do not improve the enabled dictionary workload in the same direction; the improvement is less than 5 percent; the disabled control changes materially; or a mandatory guardrail regresses.

### Parallel-aware PGO claim

**Hypothesis:** Adding a focused enabled-parallel-GC workload to the standard PGO training of `--with-parallel-gc` builds improves the remaining helper, queue, synchronization, and phase-control code without changing runtime behavior or weakening the explicit container paths.

**Falsified if:** either GIL or free-threaded training does not execute its parallel collector; profile data does not cover the intended parallel functions; feature-off PGO builds change; runtime default activation changes; optimized baseline/candidate measurements show no benefit in any trained parallel path; a broad interpreter or large-heap guardrail regresses; or build reliability deteriorates.

The PGO workload is a secondary optimization. A favorable compiler decision is not evidence that an explicit exact-container path should be removed.

“Falsified” here means that the proposed specialization is rejected. It does not imply that no other optimization can exist.

## Evidence protocol

Every experiment record must contain the CPython and parent revisions, dirty-state hash, compiler identity, configure flags, PGO and LTO status, executable hash, invocation, environment, affinity, raw-result path, complete samples, observation, interpretation, and remaining uncertainty.

Performance claims require two separate controls:

1. Alternate optimized baseline and candidate binaries in A-B-B-A order with parallel GC enabled in both. This isolates the source change.
2. Compare the same baseline and candidate binaries with parallel GC disabled. This checks that build drift or benchmark work did not create the apparent improvement.

The candidate and baseline builds must use the same source base, compiler, configure flags, PGO training procedure, LTO setting, affinity, and benchmark inputs. The parallel-aware PGO experiment is the sole exception: it intentionally varies only the PGO workload after the fully explicit collector source is fixed. Runs with other unequal work, incomplete provenance, thermal disturbance, frequency-policy changes, or unexplained variance are inconclusive rather than positive or negative.

Before implementation, each type-specific workload must assert its graph shape, tracked status, node count, edge count, collection count, and requested collector mode. One-second smoke runs may validate plumbing but cannot support a performance claim.

## Correctness contract

The focused tests must compare serial and parallel outcomes and must cover the following cases.

### Lists

- Empty and populated exact lists.
- Repeated references to one tracked child.
- Deep nesting, a self-cycle, a mutual cycle, reachable cycles, and unreachable cycles.
- Null-free traversal of all live slots after list growth and shrinkage.
- A list subclass with references outside the list payload, proving that it remains on the generic subtype traversal path.
- Tracked holders containing untracked GC-capable objects, preserving the existing untracked-object rule.

### Tuples

- Empty, singleton, and populated exact tuples.
- Repeated references and nested tracked tuples.
- Tuples that remain tracked and tuples that `_PyTuple_MaybeUntrack` makes untracked.
- Verification that an untracked tuple does not retain a stale alive bit across later collections.
- A tuple subclass with additional references, proving generic subtype traversal.

### Dictionaries

- Split-table dictionaries, combined Unicode-key dictionaries, and general-key dictionaries.
- Live entries mixed with deleted entries and unused capacity.
- Null values in legal internal slots and repeated references in values.
- General dictionaries whose keys and values are tracked objects, proving that both are visited exactly once per live entry.
- Self-cycles, mutual cycles, reachable cycles, and unreachable cycles.
- A dictionary subclass with additional references, proving generic subtype traversal.

### Test sensitivity

Before accepting a test set, temporarily introduce representative defects and show that the tests fail: omit the first or last sequence element, route a subtype through the exact-type path, skip tuple alive-bit cleanup, omit split-dictionary values, and omit general-dictionary keys. These mutations are never committed.

## Execution sequence

### Step 0: Protect and identify the exploratory state

**Status:** Complete on 2026-10-05.

Record the current CPython diff, revision, parent revision, optimized build identity, and all raw list experiment paths. Do not commit the current list patch.

The preserved evidence is in `benchmarks/results/pyperformance/investigations/ft-container-traversal-2026-10-05/`. Its README records the missing baseline-executable hash as a limitation; no stronger provenance claim is made.

Exit condition: another person can reconstruct which source and binary produced every quoted list number.

Atomic commit: parent repository only, `Record FT container traversal optimization plan and baseline`.

### Step 1: Add the verification substrate

**Status:** Complete on 2026-10-05.

Add project-owned list-, tuple-, and dictionary-dominant workloads with graph-shape assertions and baseline/candidate ABBA support. Add unit tests for workload construction, mode attestation, sample retention, and refusal of mismatched work. Do not change CPython collector code in this step.

Run the harness tests and demonstrate a controlled negative case in which mismatched work or mode is rejected.

Exit condition: all three workloads have reproducible clean-baseline measurements, and the harness can fail for the conditions it claims to verify.

Atomic commit: parent repository only, `Add FT container traversal verification workloads`.

### Step 2: Retain or reject the list specialization

**Status:** Complete on 2026-10-05. The specialization was retained as CPython commit `06f1d674a4`.

Write the list correctness tests before retaining the exploratory implementation. Run them on the clean baseline, then validate their sensitivity with temporary mutations. Apply only the exact-list direct traversal mechanism, preserving the shared visit operation and generic fallback.

Run focused debug tests, optimized baseline/candidate enabled ABBA, disabled control ABBA, final assembly inspection, hardware-counter comparison, sanitizer checks, and the mandatory performance guardrails.

Exit condition: every list criterion passes. If any criterion fails, record the negative result and restore the clean baseline rather than weakening the criterion.

Atomic CPython commit: implementation and focused tests together, `Specialize FT parallel traversal for exact lists`.

Atomic parent commit after the CPython commit: raw evidence, verdict, and submodule pointer only, `Record exact-list traversal verification`.

### Step 3: Investigate and, only if justified, specialize tuples

**Status:** Complete on 2026-10-05. The specialization was retained as CPython commit `0205d62bcb`.

Profile the clean list-retained build on the tuple workload before writing tuple code. If tuple traversal is not a material measured cost, record a falsified hypothesis and make no CPython commit.

If the hypothesis survives, write and sensitivity-check the tuple contract tests. Implement only exact-tuple iteration while retaining `_PyTuple_MaybeUntrack`, the tracked-status recheck, alive-bit cleanup, traversal order, and generic fallback.

Run the same debug, optimized ABBA, disabled-control, assembly, counter, sanitizer, and guardrail sequence used for lists.

Exit condition: the tuple claim either has a recorded negative verdict with no source change or satisfies every acceptance criterion.

Atomic CPython commit if retained: `Specialize FT parallel traversal for exact tuples`.

Atomic parent commit: `Record exact-tuple traversal verdict`.

### Step 4: Investigate the dictionary design boundary

Profile the tuple-retained build on each dictionary storage layout before writing dictionary code. Compare the exact behavior of `dict_traverse` with available internal dictionary helpers.

If faithful reuse requires a new private API, an extraction from `Objects/dictobject.c`, duplicated storage-layout logic, or any new concurrency assumption, stop and present the alternatives for approval. This is a hard design gate, not permission to choose the smallest patch.

Exit condition: either the dictionary hypothesis is rejected with evidence or the human reviewer approves a precise implementation boundary.

Atomic parent commit: `Record FT dictionary traversal design verdict`. There is no CPython implementation commit at this gate.

### Step 5: If approved, specialize dictionaries

Write and sensitivity-check tests for all three dictionary layouts before collector code. Implement the approved exact-dictionary path without changing `dict_traverse` semantics or generic subtype handling.

Run per-layout profiles and ABBA comparisons as well as the same debug, disabled-control, assembly, counter, sanitizer, and guardrail sequence used for the sequence types.

Exit condition: every dictionary criterion passes. Otherwise revert the candidate and record the negative result.

Atomic CPython commit if retained: `Specialize FT parallel traversal for exact dictionaries`.

Atomic parent commit: `Record exact-dictionary traversal verification`.

### Step 6: Train the enabled parallel collector during PGO

Add a focused CPython-owned profile workload that runs only when the interpreter is configured with `--with-parallel-gc`. It must explicitly enable the collector and exercise representative GIL and free-threaded parallel collections, including the explicit list, tuple, and dictionary paths plus normal helper, queue, synchronization, adaptive, and phase-control work. The GIL workload must exceed its serial-selection boundary so the parallel path actually runs.

Do not enable parallel GC for the entire existing PGO test suite and do not change the runtime default. The focused workload supplements the standard profile task so that unrelated interpreter profiles remain represented.

Before implementation, define the exact functions and phases that the workload must cover. Add tests proving that feature-off builds skip the workload cleanly, feature-on builds enable the collector, both GIL and free-threaded variants complete representative parallel collections, and failures propagate instead of silently producing incomplete profiles.

Build the fully specialized collector twice from identical source and configuration: once with the existing PGO task as the control and once with only the additional parallel-GC profile workload. Record function profile coverage, final assembly, executable hashes, and enabled and disabled binary ABBA results. Run broad pyperformance and large-heap guardrails to detect profile-budget displacement or other regressions.

Exit condition: the PGO workload demonstrably trains both parallel collectors, improves at least one previously untrained parallel path, preserves the explicit container paths, and passes every build, correctness, disabled-mode, whole-interpreter, and large-heap guardrail. Otherwise record the negative result and retain the explicit specializations without the PGO change.

Atomic CPython commit if retained: `Train parallel GC in optimized builds`.

Atomic parent commit: `Record parallel-aware PGO verification`.

### Step 7: Cumulative integration verification

Run the focused parallel-GC tests in GIL and free-threaded debug and optimized builds, the full CPython test suite in feature-off and feature-on configurations, the parent repository test suite, Linux CI, Windows build and test CI, and the established fork and lifecycle tests.

Run complete GIL and free-threaded pyperformance ABBA campaigns plus the project-specific full mixed and synthetic throughput/pause campaigns. Preserve negative regions and compare them with the pre-optimization evidence.

Run AddressSanitizer and ThreadSanitizer configurations suitable for the collector. A sanitizer limitation or unsupported configuration is recorded as a limitation, not silently treated as a pass.

Exit condition: all correctness matrices pass and no mandatory performance guardrail regresses. Any failure is investigated against the individual type commits rather than patched in the cumulative result.

Atomic parent commit: `Record cumulative container traversal verification`.

## Mandatory per-type verification matrix

| Gate | Required result before a CPython commit |
|------|-----------------------------------------|
| Contract tests on baseline | Pass, establishing unchanged semantics |
| Mutation sensitivity | Each representative defect makes a relevant test fail |
| Focused free-threaded debug tests | Pass |
| Focused GIL debug tests | Pass; no behavior change |
| Optimized PGO+LTO build | Completes with recorded provenance |
| Explicit hot path | Does not depend on PGO inlining or cloning decisions |
| Baseline/candidate enabled ABBA | Meets the type's predeclared threshold in both halves |
| Baseline/candidate disabled control | No material change |
| Final AArch64 assembly | Expected callback/dispatch cost is absent from the specialized inner loop |
| Hardware counters | Direction is consistent with the claimed mechanism; unexplained adverse counters are investigated |
| Sanitizer checks | Pass, or an explicit tooling limitation blocks retention |
| Large-heap and adaptive guardrails | No material regression |
| Repository state | Only the type's source and focused tests enter the CPython commit |

## Stop and rollback rules

- Stop after any falsifier; do not move the goalposts or weaken a test to retain a preferred implementation.
- Revert an experiment that does not meet its performance threshold even if it appears cleaner in source.
- Report inconclusive measurements as inconclusive and repeat only after identifying the uncontrolled condition.
- Do not combine a failed type experiment with the next type.
- Use `git revert` for a committed regression; do not rewrite published history.
- Preserve the evidence for rejected approaches, including the unsuccessful `_PyGC_TryMarkAlive` forced-inline experiment.

## Progress log

| Date | Type | Stage | Observation | Verdict | Evidence |
|------|------|-------|-------------|---------|----------|
| 2026-10-05 | Shared mark helper | Exploratory | Forced inlining removed the standalone helper symbol but left enabled `gc_traversal` at approximately 2.83 milliseconds. | Falsified as a useful standalone optimization; reverted. | `benchmarks/results/pyperformance/investigations/ft-container-traversal-2026-10-05/forced-inline/` |
| 2026-10-05 | List | Exploratory | One optimized enabled/disabled ABBA measured approximately 1.98 versus 1.57 milliseconds after exact-list direct traversal, compared with 2.81 versus 1.57 milliseconds at the clean baseline. | Failed to falsify; confirmatory baseline/candidate ABBA and contract tests remain mandatory. | `benchmarks/results/pyperformance/investigations/ft-container-traversal-2026-10-05/direct-list/` |
| 2026-10-05 | List | Evidence archive | Campaign files and the exact experimental patch were preserved. The baseline executable hash was not recoverable because the build had been overwritten. | Step 0 complete; evidence is exploratory rather than submission-grade. | `benchmarks/results/pyperformance/investigations/ft-container-traversal-2026-10-05/README.md` |
| 2026-10-05 | Container workloads | Verification substrate | Five graph-validating workloads, explicit mode attestation, mismatch rejection, binary ABBA support, and source provenance passed 39 harness tests and actual free-threaded smoke runs. | Step 1 harness complete. | Parent commits `99ef64a` and `67c7230` |
| 2026-10-05 | Container workloads | Clean baseline | A clean optimized FT binary completed disabled/enabled/enabled/disabled rigorous runs. Both halves reproduced large list and tuple penalties, split and Unicode-dictionary gains, and a smaller general-dictionary penalty. | Baseline accepted; it supports type-specific investigation and rejects treating all dictionary layouts as one performance case. | `benchmarks/results/pyperformance/investigations/ft-container-clean-baseline-2026-10-05/` |
| 2026-10-05 | List | Initial mutation sensitivity | Omitting index zero did not fail the liveness-only test because a later reachability phase recovered the early propagation miss. | Final heap outcome is insufficient to verify the early fast path; add direct debug observation. | `benchmarks/results/pyperformance/investigations/ft-exact-list-verification-2026-10-05.md` |
| 2026-10-05 | List | Direct mutation sensitivity | The debug probe failed when index zero was omitted and when a list subtype was sent through the exact-list path. | Sensitivity established; both mutations removed. | `benchmarks/results/pyperformance/investigations/ft-exact-list-verification-2026-10-05.md` |
| 2026-10-05 | List | Optimized binary ABBA | Enabled halves measured 2.23 to 1.38 milliseconds and 2.24 to 1.37 milliseconds. Both disabled halves were neutral. | The fixed 20 percent gate passed in both halves. | `benchmarks/results/pyperformance/investigations/ft-exact-list-enabled-abba-2026-10-05/` and `ft-exact-list-disabled-control-abba-2026-10-05/` |
| 2026-10-05 | List | Final per-type verification | Debug GIL/FT, ASan, standard PGO, assembly, counters, adaptive exercise, and eight 500,000-object heap guardrails passed. | Retained as CPython commit `06f1d674a4`; Step 2 complete. | `benchmarks/results/pyperformance/investigations/ft-exact-list-verification-2026-10-05.md` |
| 2026-10-05 | Test infrastructure | Release lifecycle tests | The optimized run found two existing tests that unconditionally called a debug-only hook; the clean baseline reproduced both failures. Conditioning only the private-hook assertions made the optimized and debug runs pass while retaining public lifecycle coverage. | Repaired separately as CPython commit `d29fb102c4`. | `Lib/test/test_gc_ft_parallel.py` |
| 2026-10-05 | Tuple | Pre-code profile | On the optimized list-retained build, `propagate_pool_visitproc`, `tuple_traverse`, and `_PyGC_TryMarkAlive` accounted for 37.00, 13.61, and 9.67 percent of samples. | The callback-removal hypothesis survived; tuple tests were justified. | `benchmarks/results/pyperformance/investigations/ft-exact-tuple-verification-2026-10-05.md` |
| 2026-10-05 | Tuple | Mutation sensitivity | Tests failed when index zero was omitted, when untracked tuples retained the alive bit, and when tuple subtypes used the exact path. | Sensitivity established; all mutations removed. | `benchmarks/results/pyperformance/investigations/ft-exact-tuple-verification-2026-10-05.md` |
| 2026-10-05 | Tuple | Final per-type verification | Enabled ABBA improved both halves by 1.59-1.64x; disabled ABBA was neutral; debug GIL/FT, ASan, standard PGO, assembly, counters, adaptive exercise, and eight large-heap guardrails passed. | Retained as CPython commit `0205d62bcb`; Step 3 complete. | `benchmarks/results/pyperformance/investigations/ft-exact-tuple-verification-2026-10-05.md` |

Append one row after every baseline, mutation check, rejected hypothesis, retained change, regression, or inconclusive run. Do not replace older rows when the conclusion changes.
