# Open issues

Known defects, hypotheses, review decisions and landing blockers. The project
does not claim landing readiness. Status reconciled against CPython
`c67363fa59` on 12 October 2026, with performance defects added on 15 October
and local integration repairs recorded on 16 October 2026. The full historical
audit text, with original findings and reproducers,
is `AUTIT-TODO.md` (removed; `git show 724b74b:AUTIT-TODO.md`).

**Terms.** *Source-proven*: the unsafe control flow is visible in source but no
checked-in test yet demonstrates the failure. *Hypothesis*: plausible and
falsifiable, not to be presented as fact until reproduced. *Repaired*: fixed
locally with evidence; local verification is not current-checkpoint CI
confirmation ([VALIDATION.md](VALIDATION.md)).

## 1. Source audit

Audit standard: [Verifiable Practice](https://github.com/SonicField/verifiable-practice)
`38d28d10035462e4c67f4b08d66638d3a4858216`, Engineering Standards and Code
Audit playbook. Initial audit revision `86c83d41f5`.

| ID | Severity | State | Issue |
|----|----------|-------|-------|
| A1 | BUG | Repaired; Linux verified | FT lifecycle APIs raced under concurrent use. |
| A2 | BUG | Repaired; local injection and sanitizers | Partial GIL startup had no safe rollback. |
| A3 | BUG | Repaired; local injection and sanitizers | Partial FT startup freed live state. |
| A4 | BUG | Repaired; Linux verified | FT worker arguments had process-global ownership. |
| A5 | BUG | Source-proven | GIL split-vector allocation failures are ignored. |
| A6 | BUG | Source-proven | FT unique-ID allocation failure is ignored. |
| A7 | BUG if reproduced | Hypothesis | FT scan failure may not restore temporary GC state. |
| A8 | HARDENING | Source-proven | A GIL path silently removes a freed GC-list entry. |
| A9 | HARDENING | Partly repaired | Collection-phase failure injection and dynamic coverage incomplete. |
| A10 | HARDENING | Partly repaired locally | Unreferenced helpers and the separate FT marking implementation removed; residual warnings and other weak test stubs remain. |
| A11 | HARDENING | Source-proven | The GC barrier duplicates CPython's condition-variable layer. |
| A12 | BUG | Source-proven | Worker-join failures are ignored before shared state is freed. |
| A13 | BUG | Repaired locally | Missing parallel-GC header prerequisites allowed stale objects after incremental rebuilds. |

**A1 (repaired).** Concurrent FT `enable_parallel`/`disable_parallel` aborted
with thread-state assertions. `6ce79c0c65` serializes lifecycle operations,
makes pool ownership per-interpreter and publishes the pool only after every
helper is ready; matrix run `36922821632` passed on Linux. *Remaining:*
current-checkpoint Windows and Linux repeats.

**A2 (repaired).** Helpers created before a failure blocked on a full-size
startup barrier and cleanup joined uninitialized handles. `7ec0874a7d` uses a
cancellable handshake, counts created handles and enters `FAILED`; tests fail
all 16 thread-state and 16 native-thread positions, plus resource and warning
failure, no automatic retry and explicit retry. GIL ASan lifecycle/fork and
TSan focused selections pass.

**A3 (repaired).** FT rollback freed arguments, workers and the pool while
started helpers still referenced them, and thread-state creation failure was
unreported. `6ce79c0c65` and `195830171f` shut down and join created helpers
before freeing, pre-create thread states and add lazy start; tests inject all
15 positions of each kind. FT debug and ASan: 368 tests, 39 skips; TSan
lifecycle/fork/deque: 155 tests, 25 skips, no diagnostic.

**A4 (repaired).** File-static `_pool_worker_args` let one interpreter free or
overwrite another's storage. Arguments now live in `_PyGCThreadPool`; a test
runs two live interpreters with independent pools. Does not establish the
skipped subinterpreter/fork behaviour.

**A5.** `update_refs_with_splits()` ignores `_PyGCSplitVector_Push()` failure
for the initial, periodic and end markers, so a vector can look usable but lack
the true end. *Falsifier:* fail growth after several entries; the collection
must use a complete serial path or fail safely, and cycles in the unrecorded
tail must not be retained or corrupted. *Accept:* an incomplete vector is never
dispatched.

**A6.** `par_disable_deferred_collect_ids()` discards
`worker_collect_unique_id()` failure after clearing the object's ID, which can
leak the ID; `error_flag` is not set. *Falsifier:* fail the first allocation
and each growth; every cleared ID must be released exactly once. *Accept:*
clearing and recording an ID are transactional.

**A7.** Pre-dispatch allocation failures in `_PyGC_ParallelScanHeapWithPool()`
return `-1` after earlier phases wrote temporary state; the outer path clears
ALIVE but restoration of `ob_tid`, UNREACHABLE, worklist links, deferred
references and unique IDs is undemonstrated. *Falsifier:* inject at every
allocation, then validate heap invariants and run repeated serial collections,
allocation, unique-ID use, weak references and destruction under ASan.
*Accept:* injection proves rollback complete, or one explicit rollback path
restores every invariant before the world restarts.

**A8.** `update_refs_with_splits()` detects `_PyObject_IsFreed(op)`, unlinks
the entry and continues; a worker path skips freed objects. Upstream does not
treat this as recoverable, so silent continuation may hide corruption, but the
check may encode a real requirement. *Investigation:* find the motivating
commit and reproducer; reproduce in serial and parallel modes. *Accept:*
documented and tested response; no silent normalization of unexplained
corruption. Behaviour change requires explicit approval.

**A9.** Startup injection exists in both builds and focused selections pass
ASan and TSan. Missing: systematic split-vector, scan-array and unique-ID
allocation failure; some weak falsifiers (the statistics test accepts an
unchanged `collections_attempted`); `gc.collect_async()` has no focused tests.
*Accept:* every resource-failure repair has a deterministic pre-fix failure;
tests prove the parallel path ran; `collect_async` scoped and tested or
separated; ASan and TSan for lifecycle and collection in both builds, with
suppressions recorded.

**A10 (partly repaired).** The GCC 11.5 FT release baseline emitted twelve
unused-function/variable warnings. CPython `442a97213f` removes helpers with no
surviving references; four fresh before/after builds pass focused tests with
unchanged exported GC symbols, and the unused-code gates pass. CPython
`0fc7b3ccb9` removes the separate non-pool marking implementation and its test
stub. Marking tests now exercise production and compare with serial
recomputation, with mutation checks and sanitizer evidence
([cleanup report](../benchmarks/results/investigations/dead-code-cleanup-2026-10-16/README.md),
[verifier report](../benchmarks/results/investigations/production-verifier-integration-2026-10-16/README.md)).
Remaining: FT debug's startup assertion has a signedness warning; GIL
feature-off has an unused `move_unreachable` label. Both predate integration.
Other weak page-assignment/test stubs still need audit. The new GCC/Clang
workflow is unrun on the hosted source pair and gates unused functions and
variables, not all warnings. *Accept:* no project-introduced warnings in GIL,
FT and feature-off builds; each removal proven unreachable; tests exercise
production paths; cleanup remains separate from behaviour changes.

**A11.** `pycore_gc_barrier.h` defines its own pthread/SRW mutex and condition
operations instead of CPython's `PyMUTEX_*`/`PyCOND_*` (`Python/condvar.h`),
bypassing its error conventions and `_PY_EMULATED_WIN_CV`. Not a demonstrated
failure. *Accept:* one authoritative layer, or a documented and tested reason
for two, with explicit failure policy for init, wait, broadcast and teardown.
Changing internal layering requires discussion.

**A12.** Both pools call `PyThread_join_thread()` without checking the result,
then free storage the helper may still reference. Distinct from A2/A3.
*Falsifier:* a debug join-failure hook for each helper during disable and
rollback must show no helper-referenced storage is freed unless termination is
known. *Accept:* every join result checked; if recovery is impossible, the
boundary (fatal error or deliberate retention) is explicit and tested. Policy
decision required.

**A13 (repaired locally).** Five added internal headers were absent from
Makefile prerequisites. A debug structure extension left stale objects:
an invalid participant count and a lifecycle crash disappeared after a clean
build. Before the repair, pretending any of those headers changed scheduled no
GC recompilation in GIL or FT; the existing `pycore_gc.h` dependency did.
CPython `388fd5bb46` adds five paths to the existing `PYTHON_HEADERS` list.
Afterwards all five trigger recompilation. Actual dependency-driven rebuilds,
links and focused tests pass in four feature-on configurations and two
feature-off debug controls. No collector code changed
([evidence](../benchmarks/results/investigations/header-dependencies-2026-10-16/README.md)).
Fresh hosted builds remain pending.

**CPython documentation.** `Doc/library/gc.rst` still describes child recovery
as creating helpers and a disabled GIL configuration as reporting retained
capacity. Source arms the child without helpers and reports zero workers while
disabled.

**Windows source audit.** `331aaae905` fixed MSVC issues (an unused
`<stdatomic.h>`, test-only VLAs, missing random-walk header in project files).
Production code uses CPython's portable thread, mutex, atomic and memory APIs.
The custom counting semaphore is not replaceable by `_PySemaphore`, whose
Windows maximum is ten while parallel GC may post sixteen tokens. Source review
is not execution evidence.

## 2. Performance defects and regressions

Evidence: [PERFORMANCE.md](PERFORMANCE.md) §4 and
[scaling review](reviews/2026-10-15-claude-scaling-review.md) §7–8 (where P1–P3
appear as D1–D3).

| ID | State | Issue |
|----|-------|-------|
| P1 | Measured; mechanism inferred | FT propagation workers leave permanently after `2 × num_workers` failed steal sweeps. With module-rooted live data, helpers exit before work becomes stealable: graph 0.61–0.83× serial at 16 workers (3.39× when frame-rooted). In the project suite, module-rooted collections spend 27–51% of their time in propagation at 16 workers, against 9–20% when frame-rooted. A fix (helpers wait until all work is finished) was tried and dropped; see below. |
| P2 | Measured | Work in the 1024-entry private buffer is unstealable until overflow. A deep, narrow tree never overflows: 1.22× for both holders. Publishing work to idle workers was tried and dropped: it reopens the steal contention the buffer exists to avoid. |
| P3 | Measured | Per-object stealing on fine-grained heaps is slower than one thread: lists 0.62× when stealing is active (0.15–0.31× with experimental sharing). Profiled: about 31% of samples in the steal CAS on the victim's `top` and about 17% polling deque sizes. Splitting large lists into index ranges removed it but was dropped as container-specific. |
| P4 | Measured; cause hypothesised | Single-worker parallel propagation is slower than serial (123 ms vs 76 ms on the global graph). The serial path prefetches above 200,000 long-lived objects; the parallel path does not and marks with atomics. |
| P5 | Open | FT sustained `ai_workload` −9.9% throughput, mean interval +116%. Per-collection latency about 1.5–2× serial; serial runs bimodal. Untested explanations: finalizers, BRC, cache-line ownership, mimalloc abandonment (PERFORMANCE.md §5). |
| P6 | Open | FT pyperformance `float` −10.5%. Work-distribution explanation is a hypothesis. |
| P7 | Unmeasured risk | GIL pre-mark and residual mark never steal (DESIGN.md §2.4, §2.6); root-placement dependence is untested there. |

**Attempted responses (15–16 October 2026), all dropped.** Four changes were
measured in the project suite with module-rooted variants:

1. helpers wait until all work is finished;
2. busy workers publish part of their private buffer to idle workers;
3. large lists split into stealable index ranges;
4. release stores in the work queue (needed only by the list splitting).

Results:

- the realistic module-cache workload gained +6.4% throughput and −13.4%
  mean latency;
- module-rooted collection shapes ran 12–26% faster;
- frame-rooted workloads were mostly neutral;
- sustained `ai_workload` mean latency rose 11.1%, flagged in three
  campaigns.

The combined candidate was dropped: improvements in module-rooted cases did
not justify the observed regression and additional coordination. Publishing
work reintroduces contention that the private buffer avoids; list splitting
adds a container-specific mechanism. This is evidence about these candidates,
not proof that all additional coordination is harmful or the existing design
is universally robust. The root-placement weaknesses remain open. Evidence:
[root-placement campaigns](../benchmarks/results/investigations/root-placement-campaigns-2026-10-15/README.md).

## 3. Decisions for core-developer review

These are discussion items, not authorization by themselves; collector changes
follow the change rule in §5.

- **Public surface:** whether the first proposal exposes `--with-parallel-gc`;
  `enable_parallel`, `disable_parallel`, `get_parallel_config`; diagnostic
  `get_parallel_stats` (stable schema or private name); and the orthogonal
  `gc.collect_async()`, which the discussion draft excludes. No startup
  environment variable, `-X` option or `PyConfig` field exists.
- **Worker-count contract:** fixed maximum 16 participants (16 GIL helpers; FT
  collecting thread plus 15 helpers); random walk from four; candidate-count
  normalization. Whether 16 should stay the maximum is a policy question for
  benchmark evidence. Fixed 16 beat adaptive in the tested FT phases.
- **Diagnostics:** names and schema of `pool_active`, `startup_failed`,
  `pool_startup_failures` and `last_pool_startup_error`; whether FT's inherited
  `parallel_cleanup` key belongs in the contract.
- **Scope:** GIL parallelizes interpreter-root marking, subtraction and
  reachability marking above 16,384 candidates; FT parallelizes `update_refs`,
  `mark_heap` and `scan_heap` and dispatches known-root propagation to the
  pool, where its scaling is conditional (§2, P1–P3). Finalization and
  deletion stay serial in both.
- **Failure and compatibility:** join-failure policy (A12); split-vector,
  unique-ID and scan-rollback fault injection (A5–A7); an agreed extension
  `tp_traverse` compatibility test set, given that traversal runs on helper
  threads and FT helpers do not fully bind thread states; exact CinderX
  source, provenance and licensing mapping; the subinterpreter/fork skip until
  the feature-off control stops crashing.
- **Performance limit:** PERFORMANCE.md §6 records review-work proposals for
  the open "low overhead" requirement; agree the next campaign's criteria
  before measuring.

## 4. Landing gates

Design discussion is not blocked on these; landing is.

| Gate | State |
|------|-------|
| GIL and FT ASan/TSan | Local focused selections pass; phase allocation failures untested. |
| Linux AArch64 correctness and performance | Six local focused configurations pass after integration; GIL/FT ASan/TSan selections pass at the verifier commit. Full suites and matched-harness PGO+LTO comparisons remain pending. |
| Linux hosted CI and Windows | Earlier successes reported for `38730251690`, `38730312362` and `38730315605`; their detailed evidence needs examination. No hosted run validates the integrated source pair (VALIDATION.md). |
| Native macOS active collector | First run built all four ARM64 configurations, then failed before tests due to the executable path; workflow corrected. Rerun `38880079592` feature-off passes reported; final feature-on outcomes unconfirmed. |
| Source failure policies | A5, A6, A7, A8, A12 open. |
| Performance limits and adaptation | Review-work criteria recorded for discussion (PERFORMANCE.md §6); root-placement weaknesses P1–P4 open (experiments dropped); P5–P6 open; no convergence claim. |
| Current GIL full pyperformance | Pending; focused SQLite neutral. |
| Optimized feature-off controls | Pending. |
| First-use latency and memory | Not measured. |
| Extension compatibility and provenance | Pending. |
| Public API, CPython issue, PEP metadata, NEWS | Pending; discussion draft is provisional. |
| Reviewable patch series | Future work: dependency order in `PATCH_SERIES.md` (removed; `git show 724b74b:docs/PATCH_SERIES.md`); generated files via canonical generators; every patch builds and passes the focused suite in all four configurations. |
| Legacy tooling | The root `Makefile` and `tools/` describe an older workflow and must not be used; replace or retire them so no advertised command changes the submodule revision or builds without the feature flag. |

## 5. Change and evidence rules

- **Design changes require discussion with Alex.** The approved integration
  preserves active atomics, barriers, phase structure, thresholds and adaptive
  policy. Evidence for a future change must include a meaningful falsifier,
  correctness checks and representative-workload measurements. The review
  clone recorded a broader evidence-led authorisation rule; this documentation
  import does not silently adopt it (PERFORMANCE.md §6).
- Repair one issue, or one inseparable ownership group, per commit.
- Demonstrate the pre-fix failure before the repair; keep the focused test with
  it.
- Do not mix readability cleanup, behaviour repair, performance work and
  documentation.
- Record exact commands, exit status, failures and skips.
- Alex performs remote pushes; assistants prepare local commits.
