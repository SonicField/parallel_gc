# DOC-000001 — Documentation audit and reconciliation

ID: parallel_gc:documentation:DOC-000001. Level: D.
Created: 2026-10-21T16:04:37Z. Author/operator: Codex root session
`01a0d2dd-cae0-7453-8afb-9a483d2d280a`. Owner: Alex Turner.
Status: open; prospective audit and repair record.

## Before work

Authority is the current user-provided goal: “get a 'new context' agent to
perform a documentation and compliance audit on parallel_gc and then merge
its recommendations with the issues tyou have found and use VP to repair the
issues. The new agent must read the current version of verifiable-practive
and apply risk level D.” This is an attributed transcription; the source
message timestamp is unavailable. Remote writes remain Alex's responsibility.

Baseline: SonicField/parallel_gc `eda5e00ad3aa243171a3a29fbcdad1706634567d`.
Tracked parent documents are clean. Existing untracked audit records, evidence,
builds and submodule metadata are preserved. The existing audit A-000001's
report/request will be added to history without rewriting their sealed text
or importing its approximately 3.8 GB input packet.

Current VP: SonicField/verifiable-practice
`c100fbd7f7a735e8216156223c59aa97f9ad8fa6`, standard 1.1, 21 October 2026.
This task applies bounded level-D documentation practice. It does not silently
adopt whole-project conformance, renew historical evidence or change authority,
contracts, acceptance gates, collector behaviour or benchmark parameters.

Direct consequence: minor reviewer confusion from explanatory/navigation
errors, corrected by small reversible document commits. Baseline record
recovery was verified through the bundle identified in the GIL investigation;
the audit candidate and repaired documents will also have tested recovery.
Any recommendation requiring a changed operative requirement, acceptance gate,
code, benchmark, new performance experiment or significant recovery work is
outside D repair authority and must be recorded for Alex rather than enacted.

## Plan and checks

1. Freeze an A-000002 Project Audit request and recoverable candidate revision.
2. Commission a distinct agent with no inherited conversation. It reads current
   VP itself, assesses documentation and record support, and writes only its
   report/evidence. No Code Audit or project execution is commissioned.
3. Reconcile every recommendation with the worker's identified documentation
   gaps; record repair, supported disagreement, historical unknown or escalation.
4. Make atomic documentation repairs. Preserve earlier measurements, negative
   outcomes, original audit verdicts and explicit technical unknowns. Link
   existing records rather than creating copied source/evidence archives.
5. Verify local/historical references, factual status against retained records,
   unchanged source/benchmark bytes and document recovery. Commission a fresh
   bounded successor audit to check the original findings and repaired scope.

Budget: one initial audit and one successor, up to 45 minutes each; up to three
hours of active documentation repair before an owner checkpoint. No build or
benchmark execution. Stop the affected repair on missing authoritative evidence
or a recommendation outside D; do not turn unknown historical events into facts.

Completion requires a written initial audit, a disposition for every finding
and worker gap, checked atomic repairs, and a successor report distinguishing
closed documentation defects from still-open historical/project limitations.
No full-project conformance or release decision is a completion requirement.

## Results and current action

Candidate `40bfdcd41462caafb0f1fc38856529d4739cf48e` was committed before
dispatch. Same-host replica `/home/alexturner/local/parallel-gc-doc-audit-20261021.bundle`
has SHA-256 `351318813618b913c50a629c6584491d16f71631c510893f8702d00baa70e4d9`.
A fresh clone in `parallel-gc-doc-audit-restored-20261021` recovered the
request, this commissioning record, prior audit report, README, PERFORMANCE
and GIL investigation; each was byte-compared with the candidate. Git emitted
its unsupported bundle-uri warning but completed cloning and all comparisons
passed. This is selected record recovery on the same host, not full-host or
legacy packet recovery. The fresh auditor `/root/documentation_auditor` has
no inherited conversation and is assessing that fixed revision.

The worker's separate baseline check inspected inline file destinations in
14 reviewer-facing Markdown documents: no missing file destination. It did
not check anchors, RST rendering or historical free-text locators. Phrase
inspection found stale current-status statements in README, PERFORMANCE,
VALIDATION, OPEN_ISSUES and the integration plan: some full comparisons remain
described as pending and binary custody as unverified despite later records.
These observations do not themselves close any independent audit finding.

Worker gaps to reconcile after the audit: W1 a central investigation/choice
register is missing; W2 current summaries conflict with dated successor
evidence; W3 audit records lacked Git custody (their sealed report/request
are now committed, but the large local legacy packet is not); W4 existing
audit findings need an explicit current disposition without invented closure.
Full-project six-view adoption was not established and is not a mandatory
repair imposed by this level-D task. A small linked register/current view is
an alternative to duplicating all investigation records.

Initial audit A-000002 sealed at 2026-10-21T16:16:42Z. Its fixed-input checks
pass. The VP checkout received unrelated record commits during assessment;
the auditor verified all seven instruction files remained identical to the
declared revision. The report preserves its own scope and uncertainty.

## Reconciled repair decisions — 21 October

The initial audit's five recommendations and all four worker gaps are accepted
for bounded explanatory repair. No implementation recommendation is enacted.

| Issue | Intended disposition and check |
|---|---|
| A-000002/F-001; W2 | Reconcile current status and mark dated pending entries as historical; completed comparisons, unresolved individual results and reported versus source-verified CI remain distinct. |
| A-000002/F-002; W1, W2 | Add a central linked investigation/choice register and current state; route the GIL follow-up from reviewer/performance/open-issue/campaign entry points, with changed-runtime and GIL-only custody limits. |
| A-000002/F-003; W3, W4 | Keep the original audit report untouched and add an access/disposition companion. Identify tracked reports versus untracked local legacy packet, and retain all six old findings as open. |
| A-000002/F-004 | Correct the current three-campaign shorthand: first full throughput signal, quick diagnostic-only latency warning, final full latency result, all from one binary pair. Preserve original summaries and candidate rejection. |
| A-000002/F-005 | Qualify nominal fallback/startup and state the already recorded active-collection API guard. Link unresolved allocation/rollback/join issues; do not change their policy or claim they are fixed. |

W3's report/request Git preservation is complete at `40bfdcd`; legacy packet
custody remains a stated limitation, not a D task to solve by importing it.
W4's broader historical gaps are not independently closed. The register is a
navigation aid to existing choices/evidence, not full maintained-source coverage
or retrospective authority reconstruction. No six-view project migration is
required for this bounded task. Each explanatory group gets its own commit.

Pending: these repairs, factual/link/source checks and the successor audit.
F-004 repair: checked all three original SUMMARY.md files, then corrected
SKILL, OPEN_ISSUES, PERFORMANCE and the root-placement entry record without
editing those historical summaries or raw results. The root entry's stronger
"every cluster" retention statement was also reconciled with the existing
ownership report: helpers retain their last batch, with scheduling-dependent
historical fraction. Candidate rejection remains unchanged. New-text whitespace
checks pass; successor assessment remains required for independent closure.
F-005 repair: DESIGN now distinguishes nominal startup and handled fallback
from the existing A5–A7/A12 gaps. The active-collection guard was checked
read-only in the selected `cpython/Modules/gcmodule.c`: both GIL and FT enable
and disable test `collecting` before the would-be no-op path and raise
`RuntimeError`. No core file, policy, test or failure semantics changed.
New-text whitespace checks pass; independent closure remains pending.
F-003 / W3 / W4 repair: added A-000001/ACCESS.md as a current companion,
identifying tracked report/request versus local untracked legacy inputs.
The three named legacy manifests were observed present, not rehashed as a
complete packet. The original report/request and their seal are unchanged;
all six historical findings remain open with narrow current dispositions.
New-text whitespace checks pass. Packet recovery/off-host custody and broad
historical closure were not performed or claimed.
W1 / F-002 navigation repair: added vp/README.md, REGISTRY.md and STATE.md,
linking existing design choices, rejected experiments, integration checks,
dependency alternatives, completed comparisons and open decisions by family.
README's reviewer route links the entry. Scope is explicitly explanatory,
not all-source lifecycle coverage or retrospective whole-project adoption.
Current-status reconciliation and complete link checks follow separately.
F-001 / F-002 / W2 repair: reviewer summaries now route current completion,
reported CI versus unverified job/source artifacts, and the four-block GIL
follow-up. Dated integration/dependency/handoff checkpoints retain their
historical failures but no longer masquerade as current pending work. GIL
custody is explicitly narrower than original-runtime/all-FT/whole-host recovery.
The first multi-file patch failed its exact-line check on a paragraph fragment
and changed no file; the paragraph was read and the correction reapplied.
No workflow, result JSON, original campaign summary, source, benchmark program,
acceptance rule or collector behavior changed. Final checks and successor
assessment remain pending; the worker proposes all five findings ready for
re-audit, not independently closed.

## Verification before successor assessment

At repaired revision `90b48cca79099ccb4faa957f4e30b3697c938561`, read-only
fixed-Git-tree checks cover 95 documents and 502 local inline links. No
nonlegacy destination or approximate heading mismatch is found. The 19 old
A-000001 packet-link occurrences remain excluded and explicitly dispositioned
in ACCESS.md. All fifteen explicit historical locator occurrences resolve
in the appropriate parent/core repository. The earlier parent-only diagnostic
misclassified the upstream source locator; repository-aware checking corrected
that check without changing the historical reference.

`vp/artefacts/DOC-000001/checks.json` retains the selection, identities, link
limits and changed paths. Command: `python3
/home/alexturner/local/parallel-gc-doc-reconciliation.9Du35R/check_documents.py`
from the parent. This is an operator's ordinary read-only document checker,
not execution of project tests or independent assessor evidence. Markdown/RST
render tools are absent; approximate slugs are not rendered-anchor proof and
external URLs were not fetched. The checker is outside the project source tree.

Changed paths are documents plus the identified new audit evidence JSON only.
CPython/pyperformance gitlinks, workflows, all benchmark programs/raw results
and the three historical root-placement SUMMARY.md files are unchanged.
The original A-000002 report hash still matches its seal. Core tracked status
is clean; unrelated parent untracked files remain preserved. New-text
whitespace checks pass. No acceptance rule or technical failure policy changed.

Manual evidence reconciliation preserves all original percentages while
distinguishing full versus quick protocols, fixed source versus runtime
comparisons, GIL-only reconstructed custody, and reported versus job-verified
CI. A fresh A-000003 now checks every initial finding, the worker gap
dispositions and the new register/current-state route. Any remaining finding
stays open; it is not waived by this self-check.
The first audit-output staging command rejected `checks.json` under the
existing ignore rule. Only that identified new assessment JSON is explicitly
included; the ignore policy and legacy packet remain unchanged.
Outcomes and failed checks will be appended here; final revisions are
identified in Git history.
Review triggers: changed document meaning, underlying evidence, owner scope,
contradictory findings or custody loss. D has no calendar expiry requirement.

## Successor dispatch and recovery

A-000003 is commissioned to distinct fresh-context agent
`/root/documentation_reauditor`, with no inherited worker/owner conversation.
Its fixed input is `eaa0b065922a08c6e51c79cc8856e82433fbcf48` and its request
is `vp/records/audits/A-000003/request.md` at that revision. Current VP was
rechecked as clean `b9984e5833258ff138a290680140f0467f0f5758` before dispatch;
the auditor must read and verify its instructions itself.

The repaired-input bundle is
`/home/alexturner/local/parallel-gc-doc-successor-20261021.bundle`, SHA-256
`86e746ea03bd7457286fb49ffda6d741b4a14971ac086a70da1b0e679c68b928`.
Fresh no-checkout restoration at
`/home/alexturner/local/parallel-gc-doc-successor-restored-20261021` recovered
every changed tracked document/evidence file since the baseline; exact-commit
byte comparisons passed. Git again emitted its unsupported bundle-uri warning
but cloning and all comparisons completed. This is a same-host documentation
replica check, not recovery of the legacy packet or original benchmark runtime.
The successor remains in progress; its verdict is not anticipated here.

## Independent successor outcome — 21 October, 16:34 UTC

A-000003 sealed its report at 16:32:59 UTC and rechecked inputs/outputs at
16:34:01 UTC. The entire report and its manifest were read by the coordinator;
report/checks digests match the seal. Outputs are retained unchanged in
`863f8ec` (parent repository, A-000003 report and assessment directory).
The report SHA-256 is
`f0d6283d187f8cdd4a703399bbb465e847f677e8ce7844c7a52032e6833d8561`;
checks SHA-256 is
`ff2eb72b955937e221d4aa40906e18f99df1608dd63ed1321ce16ed5b59b2032`.

All A-000002/F-001–F-005 are independently closed at
`eaa0b065922a08c6e51c79cc8856e82433fbcf48`; W1–W4 dispositions are satisfied.
F-003 closes only the companion/access explanation, not complete historical
custody; F-005 closes nominal-path qualification, not failure-path correctness.
All six A-000001 findings remain open. No new finding was raised. The verdict
is conformant with the commissioned bounded documentation checks, not with
whole-project VP adoption, source correctness, performance neutrality or
release requirements. The fresh assessor's cold-reader result identifies the
current stage, completed experiments, unresolved causes, custody limits and
Alex's uncommissioned technical choices from STATE and REGISTRY.

The current view and register now record that successor outcome. Final local
link/scope/seal checks and recovery of the handoff revision remain to be recorded.
No third audit is required or commissioned: the declared two-assessment gate
is satisfied. No source, benchmark, failure policy, operative gate or remote
state changed. The record remains open only for those final handoff checks.

## Current-view verification — 21 October

At `0ebeba2aea5104f43b56cd1b2d98c2047542b7aa`, the operator's final fixed-tree
check covers 98 documents and 508 local inline links: no missing nonlegacy
destination, approximate anchor mismatch or unexpected non-document change.
The nineteen excluded historical packet-link occurrences remain explained.
Both sealed audit report hashes match. Original summaries, gitlinks, source,
benchmark programs/raw results and workflows remain unchanged. No rendered
Markdown/RST or external URL claim is added; underlying evidence and technical
unknowns are not renewed by this documentation check.

Unique output: `vp/artefacts/DOC-000001/final-checks.json`, SHA-256
`d69ccfbdd5de79bc5114faaa06fa7b6687bda67ca5947edb44eb3d80b8f376a2`.
Command from the parent: `python3
/home/alexturner/local/parallel-gc-doc-reconciliation.9Du35R/check_documents.py`.
The ordinary operator checker was amended to permit only the specifically
identified new audit/check JSONs and verify the successor seal; its SHA-256
at this execution is
`b0c45130d0330f9d4e907fad2d17ebc49e8fbcf5431d5e3ff60db66370432333`.
It remains outside project source. Earlier check output is preserved unchanged.
These are worker handoff checks, not a third independent audit or technical run.
