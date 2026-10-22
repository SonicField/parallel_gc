# REC-000001 — Reform records for VP 1.2 evidence roles

ID: `parallel_gc:records:REC-000001`. Owner: Alex Turner. Worker: Codex.
Created: 2026-10-22T13:36:23Z. Status: plan for owner review; execution not authorised.

## Mandate, outcome and boundary

Authority: Alex's current request, “Please make a vp complient plan to reform
the vp records according to the new clarification of the standard.” This is
attributed transcription; the original message timestamp is unavailable.

Baseline: `SonicField/parallel_gc` commit
`6a08e9e6f4e8c7a555e14ebcd7b81127673d9ee7`. Governing guidance: VP standard
1.2, especially §§1.1, 6.1, 9 and 11, in `SonicField/verifiable-practice`
commit `b068e9cbe245bcdc039993020befb594a795bff3`, local clone
`/home/alexturner/verifiable-practice`. Remote availability was not checked.

Outcome: a reviewer can identify what is needed to repeat and examine each
recorded investigation, what merely identifies a past executable, what is
disposable, and what remains untested or unavailable. Routine build products
must not acquire indefinite retention obligations merely because they were used.

Scope: the [current VP views](../../../README.md),
[investigation register](../../../REGISTRY.md), current audit dispositions,
and the experiment records/manifests they rely on. This is bounded reform,
not whole-project VP adoption or certification. CPython source, collector
behaviour, benchmarks, parameters, measurements and workflows are unchanged.
No builds, benchmark runs, remote writes, archive extraction or deletion are
authorised by this planning request. Alex controls execution and disposal.

## Consequence and approach

Drafting this proposal and linking it from STATE are level D: reversible
explanatory additions, with no changed retention obligation or acceptance gate.
Before writing, tracked parent state was clean; baseline README and STATE
were byte-compared successfully with the existing restored documentation replica.

For implementation, explanatory corrections remain D. Changing a live retention
obligation or record-control contract is a proposed C stage, requiring Alex's
approval and a fresh Project Audit before acceptance. Do not relabel such changes
as D because they are prose. Any later disposal requires separate exact-target
authority and consequence assessment; uncertain unique-evidence loss stops it.

Alternative rejected: archive every executable/environment. VP 1.2 expressly
does not require that. Blanket deletion is also rejected: raw measurements,
unique inputs and patches may live beside build products. Classify by role and
consumer, not extension. No per-temporary-file inventory or new six-view system.

## Proposed stages and atomic commits

All implementation stages below are pending owner approval. Use this combined
plan/log for progress, attempts and decisions rather than creating parallel logs.

| Stage | Action and deliverable | Check / exit condition | Worker budget |
|---|---|---|---|
| 1. Discover obligations | Read current views and each family linked by REGISTRY; fix the actual affected-path list. Add one compact family-level table here: required records/results, provenance-only identities, working resources, explicit byte obligations, consumers and unknowns. Inspect named manifests/archive indexes only where needed; do not run or unpack binaries. | Every in-scope family has a disposition. Unknown ownership, sole-copy measurements and explicit retention clauses are identified, not assumed away. Alex reviews proposed obligation changes before stage 2. | 45 minutes |
| 2. Correct current guidance | Separate commits for reader guidance and approved live-obligation changes. Update README/STATE/REGISTRY, current access companions and successor manifests where needed. Identify 1.2 as the prospective scoped rule; preserve earlier standard/revision verdicts. | No default executable, compiler, container or complete-machine archive requirement. Actual byte exceptions have a purpose, consumer and period. Raw results remain protected. No acceptance gate is silently weakened. | 60 minutes |
| 3. Reconcile reproduction support | In existing investigation records, add dated successor notes for missing or misleading support. Link source/patches, dependency/toolchain specifications, build/run commands, workload inputs, controls, raw outcomes, analysis and environment limits. Describe recorded recipes, tested reconstruction, repeated experiments and byte recovery separately. | Evidence supports each stated status; no new recipe is reported as an old execution. Missing recipes/inputs/results remain explicit gaps. A retained executable or archive is not called successful reproduction. | 45 minutes |
| 4. Verify and prepare handoff | Check all changed paths, immutable references, original seals, result preservation and current-reader routes. Produce a proposed resource-disposition list by family; do not perform cleanup. Commit checked groups atomically and verify recovery of retained record changes. | No code/result/workflow changes or copied source/audit packets. Required evidence has identified custody and recovery limits. A reader can distinguish disposable resources from unresolved obligations. | 30 minutes |
| 5. Independent changed-control gate | After approval, commission one fresh-context Project Auditor using current VP and a fixed recoverable revision. Full changed-path/operative-clause inspection; semantic samples include each evidence role and the GIL follow-up, a full source-ABBA family and legacy access. No technical execution. | Sealed scoped verdict and finding dispositions. Only the auditor can close prior findings; Alex accepts or defers the C-stage outcome. No blanket closure of all six old findings. | One audit, 45 minutes |

Maximum worker execution budget: three active hours, plus the one audit.
Checkpoint after discovery and whenever a stage budget is exceeded; do not expand
scope or commission repeated audits automatically. No agents are commissioned
by this plan alone. Recheck source, standard and obligations at approval/resume;
proposed C-stage review by 29 October reflects the recently changing guidance.
The D planning record itself has change-trigger review, not calendar expiry.

## Specific records and checks

Start with [A-000001/ACCESS](../../audits/A-000001/ACCESS.md): F-004/F-005
need scoped reassessment of reproducibility and retention, not blanket closure.
Other authority, chronology, coverage, performance and CI gaps are not solved
by changing the definition of evidence. Preserve A-000001–A-000003 reports,
requests and seals; use successor entries and immutable locators.

The [GIL follow-up](../../../../docs/investigations/gil-build-effects/INVESTIGATION-STATUS.md)
declares project-life-plus-one-year evidence retention and references separate
observation/runtime archives. Inspect their existing obligations and contents
before proposing a successor policy. Keep raw measurements, failed attempts,
recipes and limitations; temporary recovered executables do not imply a perpetual
archive duty. Do not silently discard an archive containing both kinds of material.

Verification must try these counterexamples: a missing temporary executable
treated as a defect solely because its digest survives; missing unique raw data
treated as disposable; an unavailable environment claimed reproduced because a
binary restored; an explicit byte obligation silently removed; or an old audit
marked closed by the worker. Any occurrence fails the reform check.

## Completion, reversal and pending decisions

Done means approved current records express all three roles, required experiment
support is linked with honest gaps, old seals/results remain intact, recovery
covers retained record changes, and the changed-control gate is satisfied.
Actual experimental reproduction, benchmark neutrality, source correctness and
filesystem cleanup are not completion claims for this reform.

Reversal: revert individual new document commits, preserving their history and
evidence; never reset the worktree or rewrite sealed reports. No disposal means
this reform cannot lose build/data bytes. Missing support is escalated or reliance
bounded, not repaired with invented history.

Alex's pending decisions: approve execution scope/gate; approve any identified
live-retention changes; choose custody for genuinely unique untracked results;
and, separately afterward, authorise exact resource-cleanup targets if desired.

## Planning checks and progress

Planning inspection read current VP skill/standard/records playbook and relevant
templates, current parent views/access companion and the GIL retention entry.
Baseline reader-file recovery passed. This establishes planning inputs, not
classification of every workspace or a reproduction test. Final plan/link checks
found eleven resolving local destinations across this plan and STATE. All three
historical audit reports remain byte-identical to baseline; whitespace checks
pass. Planning completed at 2026-10-22T13:37:34Z; implementation remains pending.
The planning commit identifies both changed paths. Its exact bytes will be
compared from the existing separate restoration repository before handoff;
that check covers documents only, not experimental reproduction or host loss.

## Execution authority — 22 October

Alex clarified that correcting old AI-written defaults does not require approval
sentence by sentence, then instructed “Please execute.” This authorises the
planned records reform and its one scoped Project Audit, not filesystem cleanup
or new measurements. Execution baseline is planning commit
`6f9f7168013cab137a8a3d006b68345d1dafc6c2`; tracked parent state is clean.
Current VP is still clean at the pinned 1.2 revision. Historical reports/results
and external archives remain untouched.

Prospective implementation level: C for the evidence-role/retention control
correction as a group; separate explanatory reader updates are D. The declared
fresh changed-control gate applies before acceptance. Changing definitions could
otherwise hide a real raw-result obligation, so all required measurements,
inputs, recipes and explicit exceptions remain protected. No actual byte disposal
occurs. The 29 October review and earlier change triggers apply to this C-stage
decision; D prose keeps trigger-only review. Unknown genuine external obligations
are escalated, not removed under this authorisation.

Progress: discovery in progress; stages 2–5 not yet executed. The original plan
and its then-pending approval statements above are preserved as pre-action history.
