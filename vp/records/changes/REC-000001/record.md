# REC-000001 — Reform records for VP 1.2 evidence roles

Current status, 22 October: implementation and scoped independent assessment
complete; ready for Alex's C-stage acceptance or deferral. The original plan's
then-pending status below is preserved history. Final progress and audit outcome
are at the end of this record. No cleanup or remote write occurred.

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

## Discovery checkpoint — 22 October, 13:47 UTC

Read-only discovery covered all 36 register families and their 54 distinct
primary targets (53 files and one directory). All targets are present. The
directory is the repaired source-ABBA family, with 34 tracked files. Structural
inspection covered every primary text target; semantic inspection concentrated
on the seven dependency decisions, readiness, build preparation, source-ABBA
support, GIL follow-up and named legacy manifests. This is not verification of
every historical output or every byte in an archive.

The existing REGISTRY supplies the support links for the groups below. Alex
is the decision owner; source/design consumers are implementers and reviewers,
and measurement consumers are reviewers repeating or examining the experiments.
Working-resource ownership/active consumers have not been checked for disposal:
there is no disposal in this task.

| Register families covered | Required durable support | Provenance / working-resource disposition and limits |
|---|---|---|
| GIL partitioning; marking/barriers/private work; adaptive search; inherited forkserver activation; container traversal/inlining; parallel PGO; SQLite/lazy startup; fork recovery | Source/design choices, patches, exact protocols and recorded tests/measurements, including rejected candidates | Executable/profile IDs identify runs; build trees, pools' test environments and installed tools are working resources. No default exact-byte retention duty. |
| FT root placement; four dropped coordination candidates; finalizer/BRC/float hypotheses | Workload definitions, protocols, raw outcomes and rejection/uncertainty explanations | Diagnostic builds are working resources. A hypothesis with a falsifier is not an executed experiment or established cause. |
| Creation-worker retention; module-rooted coverage; dead code; production verifier; header dependencies | Source changes, controls, failures, test logs and design reasoning | Compiled tests/sanitizer binaries are working resources, not substitute proof for logs or unique patches. |
| Native-decimal preparation; full project source ABBA; focused FT repeat; unchanged FT repeat; local full-suite/debug | Build specifications/commands, measured source identities, workload controls, raw legs/failed attempts, analysis and context limits | Build IDs are provenance. Original-environment reconstruction remains untested; a same-binary repeat is not independent rebuild replication. |
| Cloudpickle; Genshi; Coverage; MarkupSafe; Greenlet; Dulwich; SQLAlchemy | Version/engine choices, source patches, native/pure-Python constraints, build/run recipes, inventories and diagnostic outputs | Wheels, RPMs, compiler installs and virtual environments are working resources. “Retain native engine” specifies the measured implementation, not perpetual wheel custody. Retrieval/rebuilding was not tested by this reform. |
| Prepared runner/state validation; complete readiness | Runner source, exact selection/state constraints, per-run outputs, failures and package specifications | Disposable installed tools do not make missing raw outputs disposable. Diagnostic readiness is not performance evidence. |
| Repaired source ABBA, all sixteen suites | Source/build/protocol specifications, raw per-program and combined results, execution/fingerprint inventories, comparisons and arithmetic checks | Source/build IDs identify the measured pair. Recorded recipes and completed execution exist; reconstruction from them has not been tested here. Missing temporary FT executables alone are not an evidence defect. |
| GIL source-versus-build follow-up | Original and new raw observations, failed preparation, scripts, build/support specifications, fingerprints and analyses | Executable/runtime recovery is a past diagnostic result. The original complete runtime was unavailable; four new blocks used a different shared runtime. External archives are mixed as detailed below. |
| CI probe/wrapper; documentation audit; historical project audit; remaining source/API/performance decisions | Source/record history, logs, original reports/requests/seals, authorities and honest unresolved limits | Copied source/build packets are not the mandatory retention unit. Unique observations and capture/authority metadata must remain accessible; no blanket historical closure. Hosted job/source inspection remains outstanding. |

Named external manifests inspected: recovery store
`parallel-gc-gil-recovery.iJz6nj`, revision
`091100291cfb7ff83f48ba52c8e01f8e7d0d2818:README.md`, and evidence store
`parallel-gc-gil-evidence.2Cwhq4`, revision
`c5987dd1cbcd6175e1b0d6ef12d4530f619df4bd:README.md`, both under
`/home/alexturner/local/`. Their binary/runtime retention clauses are earlier
AI-written defaults, not an identified release, forensic, replay or external
byte obligation. Alex's execution authority permits correcting those defaults
through the dated parent successor, while preserving the historical manifests.
The required-record period in the GIL record remains project life plus one year
after retirement. No genuine external exact-byte exception was found within
the inspected scope; unknown obligations elsewhere are not waived.

Archive indexes, not extracted contents, distinguish 201 observation members
from 6,364 runtime members. The observations archive contains raw JSON/logs,
preparation/analysis scripts and fingerprints **and** a bz2 RPM, native extension,
header and package documentation. Therefore it is a mixed container: preserve it
until required records are safely separated before any separately authorised
cleanup. That does not make each contained build product durable evidence.
The runtime archive mainly contains installed runtimes/packages, but can also
contain configuration support. Index inspection alone does not establish that
every required configuration is recorded elsewhere. Its replacement or disposal
would need that check; no portable restoration/reconstruction was tested.

The legacy A-000001 input/assessment manifests were read in place; its whole
copied packet was not expanded. Unique capture/log/authority evidence remains
protected. Git source copies and executables are not automatically required,
but no complete selective-disposal assessment was done. There are also 111
untracked pyperformance result files: their durable custody and sole-copy status
remain unresolved. They stay untouched; this reform does not classify all of
them as disposable or claim off-host recovery.

Fixed affected paths: this record, vp/README.md, vp/STATE.md, vp/REGISTRY.md,
A-000001/ACCESS.md, root README.md, docs/PERFORMANCE.md, docs/VALIDATION.md,
docs/OPEN_ISSUES.md, docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md and the GIL
INVESTIGATION-STATUS.md. Add only the commissioned A-000004 request/reference
and report. Original dated experiment entries and sealed audit records remain
unchanged; current prose and dated successor entries carry the correction.

Stage 1 complete within its 45-minute budget. Stage 2 proceeds under Alex's
already clarified authority; no further approval of AI default clauses is
requested. One independent C-stage gate remains before acceptance.

## Repairs and checks — 22 October, 13:50 UTC

Stages 2–3 complete: reader guidance was committed separately at `77cb297`;
the current retention/control repair adds dated GIL/campaign/access successors
and reconciles root/performance/validation/open-issue prose. Required GIL records
retain the project-life-plus-one-year period; the old AI blanket rule no longer
requires retaining working binaries/runtimes. No actual exception was removed
and no archive or original manifest was edited. Recipes, clean reconstruction,
the actual different-runtime repeat and byte recovery are separately described.

Ordinary external Git/text checker
`/home/alexturner/local/parallel-gc-record-reform.0E3W5s/check_records.py`
passed: eleven allowed document paths, 987 protected tracked paths plus gitlinks
unchanged, 240 resolving local links, original dated GIL/campaign prose and
original access table preserved. Its evidence-role assertions check the five
declared counterexamples through recorded clauses, not new experiments. This is
a structural operator check; the independent auditor supplies semantic scrutiny.
Whitespace checks pass. No build, benchmark, extraction, archive edit, remote
write or deletion ran. The checker is an ordinary disposable verification tool,
not a required executable artefact.

Proposed resource disposition: retain source/patch/protocol/raw/log records in
the nine family groups above; treat build trees, installed tools/environments,
compiler/package caches and recovered executables as working resources, with
disposal pending exact-target authority and active-consumer/dependency checks.
Keep mixed containers and the unmapped legacy packet intact until unique records
have verified custody; preserve the 111 untracked results while their custody
is decided. There is no per-file cleanup queue or new default archive duty.
Missing clean-environment reconstruction and off-host protection remain limits,
not claims this document reform has repaired them.

Stage 4 recovery and stage 5 audit are next. No stage budget was exceeded.

## Independent gate and handoff — 22 October, 13:57 UTC

Stages 4–5 complete. Fixed input
`7a9ebfb247d3709d4b59e45b4a341c850f54748c` was fetched locally into the
existing separate replica's `refs/records-reform/audit-input`; all thirteen
changed files were byte/mode-compared successfully and Git connectivity passed.
Repeatable method: `git diff --name-only <baseline> <input>` selects paths;
compare `git show <input>:<path>` bytes and `git ls-tree <input> -- <path>`
mode/object entries between source and replica; run
`git fsck --connectivity-only --no-dangling <input>` there. The final handoff
commit is likewise fetched/compared after committing this entry; its exact
revision and observed check belong to the handoff, not a self-referential hash.
This verifies records on a separate same-host repository, not clean experimental
reconstruction or whole-host protection.

[A-000004](../../audits/A-000004/record.md) independently assessed that fixed
input and sealed at 13:56:46 UTC. The report is preserved at
`f932b7580bc556583b066027d6613b2a23a6be63`, SHA-256
`029e5ba2d993e1cfee0c06ef36696292e37b128ba6d44e3a8c48c665d9a5b6b5`.
Verdict: conformant within the commissioned record-control scope; no new
mandatory findings. Its own thirteen-file recovery, all-tree comparison,
semantic role checks, dependency/patch and archive-identity/index checks passed.
It inspected every changed clause and the declared semantic traces, without
executing product code, archived runtimes or experiments. Its 4:55 elapsed
assessment is within the one-round 45-minute budget. No further audit was spawned.

Only the prospective blanket binary/environment implications of A-000001/F-004
and F-005 are independently superseded under 1.2. Their real historical-record
access/custody gaps remain open, as do F-001/F-002/F-003/F-006. Missing original
HV raw data, the undetailed scratch failure, unmapped legacy unique support,
111 untracked results' custody, runtime configuration dependencies and untested
clean reconstruction are not repaired by this change. Off-host protection is
unverified, not a generic newly imposed duty for every resource.

The declared assessment gate is satisfied; Alex retains acceptance or deferral
of the C-stage outcome. The 29 October/earlier-change review remains. Current
views now route the scoped result without changing old reports. Required-record
periods, results, source, workloads, workflows and gitlinks stay intact. No
filesystem cleanup, executable retention mandate, new experiment or remote write
was added. Future custody work or disposal needs its own exact bounded scope.
