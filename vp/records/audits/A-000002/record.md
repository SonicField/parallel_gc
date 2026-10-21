# A-000002: Independent documentation and records assessment

**ID:** A-000002  
**Type / audit kind:** A Project Audit; project  
**Created:** 2026-10-21 16:14:50 UTC  
**Sealed:** 2026-10-21 16:16:42 UTC  
**Author/operator:** Fresh-context Codex documentation auditor, session task `/root/documentation_auditor`  
**Status:** Terminal assessment — nonconformant with the bounded commissioned documentation checks; findings open  
**Origin / request:** [immutable commissioning request](request.md), input commit `40bfdcd41462caafb0f1fc38856529d4739cf48e`  
**Goal served:** [DOC-000001](../../changes/DOC-000001/record.md): make the reviewer documentation useful, supported, navigable and consistent without changing collector behavior or adopting full-project VP conformance  
**Evidence:** [checks.json](../../../artefacts/A-000002/assessment/checks.json)

## Scope and method before audit

The request fixes a documentation assessment, risk level D for prospective explanatory repairs, one assessment within 45 minutes. Its scope and authority were read first from the immutable commit. I then read the current VP skill, standard, routing, record-audit playbook and three audit templates myself. The selection was complete structural coverage of the named prose directories and current reviewer-facing documents, with semantic sampling by investigation/decision rather than a code audit. This report completes that bounded assessment; it does not commission repairs or spend the repair budget.

The assessed parent is `40bfdcd41462caafb0f1fc38856529d4739cf48e`, tree `0d2a45c2ff7a607155cdf0f7a3b0d004c2df3ab1`; request blob `5ec765f8d4e4d912ebc895c65c0903f88bf5f6f0`. Its CPython gitlink is `b91445e0b95454e32b982770f6e3c864beb5a528`, pyperformance gitlink `ccc0aeb7ad46d65b6dcd4160e0fdda4d885852dd`. These identify inputs, not tested checkout behavior. Input document locators below refer to this commit; use `git show 40bfdcd41462caafb0f1fc38856529d4739cf48e:<path>` when the live checkout advances.

The standard is **Verifiable Practice project-records 1.1**, at declared revision `c100fbd7f7a735e8216156223c59aa97f9ad8fa6` in `/home/alexturner/verifiable-practice`. Initially that repository was clean at the declared revision. During assessment it advanced through `87fb8eb4b7c1b6f1177c5902796b48bcba94441e` and `c6937f896fd6a64c4cb10295e1adb8c0e7175ea9`; the latter check showed untracked `vp/artefacts/D-000028/`. The tracked differences inspected were VP project records and A-000011/D-000028 records/evidence, not instruction files. The final 16:16:42 check was clean at `b9984e5833258ff138a290680140f0467f0f5758`. These seven complete instruction files were still byte unchanged against the declared revision:

- `SKILL.md`, `standards/project-records.md`;
- `playbooks/audit-routing.md`, `playbooks/record-audit.md`;
- `templates/project-records/audit-request.md`, `audit.md`, `audit-response.md`.

The fixed instruction bytes remain the assessment basis. Unrelated VP record changes were not imported as new requirements.

### Independence, authority and access limits

This is a separate auditor session, supplied no worker/owner conversation. I authored none of the assessed input. The commissioning handoff supplied scope, immutable identities and operational recovery metadata, not findings to ratify. The worker's preparation checks are not this independent assessment. The auditor remains an AI agent operating on the same host/workspace; this is session/author separation, not an independently administered custodian or proof of independence from the underlying model family. No separately authenticated served-model build or historical author identity is established.

DOC-000001 preserves the attributed owner instruction, D reason and prospective boundary in one record. Its date is given, but the original instruction's timestamp is unavailable. That limitation is explicitly recorded; attribution is not an independent capture of the conversation. The open prospective record is appropriate before repairs. This stage does not require the worker to pretend repairs or successor closure already happened.

Immutable Git objects were read through Git; document bodies and existing captured reports are evidence of what is recorded. Git hashes/digests detect byte changes but do not authenticate authors, original executions or chronology. Named external custody metadata was inspected read-only. No network source/job verification was attempted. No project script, test, build, benchmark, binary or archived environment was run or extracted. CPython/core content and its AI-policy reading are excluded; metadata existence of one referenced upstream object was checked without reading its source. The old A-000001 copied input packet was deliberately not expanded.

### Structural coverage and semantic trace selection

The complete focused Git inventory is in checks.json: **89 Markdown/RST documents**, including the four selected commissioning/audit records and one additional linked performance report. It comprises root README/SKILL (2), docs (13), dependency-repair (14), pyperformance investigations (7), repaired-source ABBA (17), other result investigations (31), records (4), and the additional linked PGO report (1). This is not an inventory of every historical project action or of submodule documentation.

| Selection | Semantic coverage |
|---|---|
| Current reviewer set | Entire README, SKILL, DESIGN, GETTING_STARTED, OPEN_ISSUES, PERFORMANCE, TESTING, VALIDATION, integration plan, handoff, pyperformance campaign, CI conclusions, GIL-build-effects status, and PEP-shaped RST discussion draft. |
| Independent supporting investigation families | All seven pyperformance investigation READMEs: exact-container traversal, clean baseline, exploratory/inlining, and SQLite/lazy startup. All dependency repair decisions and evidence READMEs. Root READMEs for scaling, root placement/retention, dead-code cleanup, header dependencies, production verifier/tests, CI probes and wrapper repair. All three root-placement campaign summaries. |
| Integration validation | Status opening/current checkpoints, structural headings and conclusion ranges; build, hook, preparation, native-failure, default-compatibility, focused, repeated-full, local-full, debug and GIL-comparison summaries; selected outcomes and numeric result tables. Supporting long result bodies were sampled, not all read linearly. |
| Repaired source ABBA | All four campaign READMEs; each checkpoint README's opening/status selection; structural assessment of all analysis Markdown, selected numeric rows and immutable analysis JSON. |
| Historical support | Scaling review lines 1–200 and 380–653, not 201–379; selected linked PGO report lines 1–90 and 170–222. All ten distinct explicit historical Markdown/RST Git locators checked for object existence, not a semantic reconstruction of the historic tree. |
| Prior audit and authority | Entire preserved A-000001 request/report, current A-000002 request and DOC-000001. No old copied input packet or independently replayed historical observations. |
| Latest GIL follow-up | Entire status record; named external README/SHA manifests, Git identity/status and evidence-bundle digest. Underlying observation/runtime archives were not extracted or independently interpreted. |

Structural checks parsed **391 inline Markdown/explicit RST local-link occurrences**: 372 resolve to files/directories in the fixed tree; 19 do not, all in the historical A-000001 report pointing into its excluded old packet/assessment. Both parsed local heading links resolve. Markdown fences balance. This scanner does not certify all prose paths, reference-style links, rendered anchors or external URLs; submodule targets are not semantic source checks. All ten distinct explicit historical prose Git locators resolve, including the recorded root locator `724b74b:AUDIT-TODO.md`. The referenced upstream `333071231d` object locator also exists. Existence is narrower than access to all past evidence or complete historical review.

For arithmetic, I independently recomputed nine selected rows in each of four immutable analysis JSONs: subparsers, btree, btree_gc_only, bench_mp_pool, dask, dulwich_log, html5lib, connected_components and k_core. Pooled and half ratios match the stored percentages in all **36 rows**, maximum difference zero at represented precision. The four stored geometric means round to the published −0.21%, +0.33%, +0.23%, −0.25%. This checks derived consistency, not every raw program, independence of samples, original runtime or a performance acceptance gate. The recorded 100 programs/127 results and sixteen completed suites remain supported worker captures/analyses, not an auditor rerun.

### Recovery and original-input checks

The same-host bundle `/home/alexturner/local/parallel-gc-doc-audit-20261021.bundle` verifies as complete Git history with the input ref. Its independently checked SHA256 is `351318813618b913c50a629c6584491d16f71631c510893f8702d00baa70e4d9`.

Against `/home/alexturner/local/parallel-gc-doc-audit-restored-20261021`, I independently compared immutable object bytes for A-000002/request, DOC-000001/record, A-000001/record, README, PERFORMANCE and the GIL investigation; all six standalone comparisons returned success. Their SHA256 values and command results are in checks.json. An initial restored-clone HEAD diagnostic failed because HEAD was not selected; accessing the specified immutable commit succeeded. That was not a failed byte-recovery check.

This is independently checked selected document recovery from a coordinator-prepared same-host replica, not an independently administered restore, whole-host-loss protection, recovery of all referenced evidence or executable environments. For the GIL custody follow-up I checked metadata in recovery repository `parallel-gc-gil-recovery.iJz6nj` at `091100291cfb7ff83f48ba52c8e01f8e7d0d2818` and evidence repository `parallel-gc-gil-evidence.2Cwhq4` at `c5987dd1cbcd6175e1b0d6ef12d4530f619df4bd`. The v2 evidence bundle digest matches `6e8f58355b0cb542f6d7691f04c48b421d83153fad0a76ba6cab592e4a4a33bc`. These locators/manifests identify two recovered original GIL binaries and new reconstructed-runtime observations; they do not recover the original complete runtime or establish original FT binary custody. Worker archive/recovery checks remain attributed.

At **16:16:42 UTC**, after assessing and drafting the report, the original fixed tree, request blob and documentation bundle digest still matched the initial values, and the seven VP instruction files still had no difference against the declared revision. Earlier checks at 16:11:42 and 16:14:21 also matched. The output report/evidence are deliberately outside the original immutable tree. No blanket clean-worktree claim is made about concurrent project owner work.

## Findings

“Mandatory” below means required by this commission's consistency/support/navigation goal, not mandatory full-project VP adoption. No finding retroactively imposes D record rules on collector experiments.

| Finding | Classification | State |
|---|---|---|
| A-000002/F-001 | Required documentation consistency repair: competing current-status assertions | Open |
| A-000002/F-002 | Required navigation/current-evidence repair: latest GIL follow-up disconnected | Open |
| A-000002/F-003 | Historical evidence-access limitation; companion navigation disposition requested | Open, scope-limited |
| A-000002/F-004 | Required claim-support qualification: three unlike campaign signals collapsed | Open |
| A-000002/F-005 | Advisory explanatory risk: nominal lifecycle/fallback described too generally | Open |

### A-000002/F-001: Competing “current” status without a reliable latest-status route

**Requirement:** A reviewer should distinguish completed work, unresolved verification and historical checkpoints across the requested current documentation.

**Observation:** [PERFORMANCE](../../../../docs/PERFORMANCE.md), line 222, says in bold “Full-default pyperformance remains incomplete”; lines 226–237 and 362 report the completed sixteen repaired suites. [Integration plan](../../../../docs/CLAUDE_INTEGRATION_PLAN.md), lines 5 and 108, still describes matched-harness campaigns/hosted runs as pending. [Dependency plan](../../../../benchmarks/dependency-repair/PLAN.md), line 35, labels the six-repair/SQLAlchemy-awaiting state “Current status”, immediately followed by approval/readiness completion, and line 39 still leaves rigorous suites outstanding. [VALIDATION](../../../../docs/VALIDATION.md), line 41, preserves the 19 October readiness snapshot with sixteen rigorous comparisons outstanding, without a local successor route to completion. [TESTING](../../../../docs/TESTING.md), line 182, says the first hosted result is pending; the [19 October CI conclusions](../../../../docs/ci-results-2026-10-19.md) report newer successful workflow conclusions, explicitly without source/job-level verification.

Dated old snapshots are legitimate history, not erroneous merely because time passed. The defect is the unqualified current wording and incomplete successor routing in the current reviewer set. The dated VALIDATION gitlink warning correctly distinguishes its historical `388fd5bb46` from the live selector; it is not itself a pin defect.

**Impact / unknowns:** Readers can misidentify the next task as running suites already completed, or confuse reported CI success with verified job evidence. This does not prove those jobs or measurement executions independently.

**Response / closure:** Establish a dated current overview or explicit successor pointers at these current-status assertions. Preserve failed dependency/native histories. Distinguish (a) sixteen completed source comparisons, (b) unresolved individual increases/acceptance, (c) owner-reported hosted conclusions and (d) still-unverified source/job artifacts. Ensure the reviewer can reach the latest state without reconciling contradictory “current/pending” statements manually. No CI fetch, benchmark rerun or deletion of history is required for this explanatory repair.

**Confidence:** High: direct text cross-check in the immutable reviewer set.

### A-000002/F-002: Latest material GIL investigation is absent from the reviewer route

**Requirement:** Readers must find material follow-up outcomes and remaining unknowns, including narrowed custody claims.

**Observation:** [GIL build effects status](../../../../docs/investigations/gil-build-effects/INVESTIGATION-STATUS.md), lines 3–22 and 203–219, records completion of four focused blocks/sixteen invocations on 21 October. The earlier GIL-enabled `btree_gc_only` +12.70% and `connected_components` +6.48% increases did not reproduce in the reconstructed shared-runtime experiment. Its conclusions explicitly deny equivalence, a stable smaller regression, cleanup causation or proof that the missing original runtime caused the difference. Lines 106–179 preserve the recovered two original GIL binaries, missing original runtime and authorized reconstruction, including failed preparations.

A literal search of all 89 assessed documents found **no incoming `gil-build-effects` path reference** to this record. The current README performance follow-up, PERFORMANCE §4.1/§7, OPEN_ISSUES and campaign route do not mention this latest follow-up. They retain the earlier negative results/general repetition request and broadly unverified present-binary custody. The original data are not invalidated; the absence of the follow-up route is the defect.

**Impact / unknowns:** A reviewer misses both newly completed work and its essential changed-runtime limitation, and may commission an already completed focused stage. Conversely, an indiscriminate custody update could falsely imply all FT/original environment bytes were recovered.

**Response / closure:** Add a discoverable current route from the reviewer overview/performance/open-issue or campaign documents, with a concise dated disposition: the earlier increases remain recorded; the four focused reconstructed-runtime blocks did not reproduce their original pattern; cause, equivalence and acceptance remain unresolved; only the identified GIL binary pair is recovered, not the original complete runtime or all FT assets. Mark any next investigation as conditional/uncommissioned as appropriate. Preserve the earlier observations and authority amendments. No technical investigation is commissioned by this finding.

**Confidence:** High for omission and recorded conclusions; independently verified only metadata/selected document recovery, not the archived experimental observations.

### A-000002/F-003: Preserved historical audit links do not travel with the bounded bundle

**Requirement:** Reviewer navigation and custody statements should distinguish available reports from unavailable/excluded supporting bytes.

**Observation:** The preserved [A-000001 report](../A-000001/record.md) contains 19 local link occurrences absent from this input tree, at lines 8, 18, 22, 34, 42, 50, 52, 54, 74–75 and 167. They target `vp/artefacts/A-000001/input/` or `assessment/`, including original authority, old standard, copied source, pre/post checks and manifest. This old packet is expressly excluded here; its existence or deletion outside the fixed tree was not assessed. There are no parsed missing local links elsewhere in the 89-document selection.

**Impact / unknowns:** The old report remains readable, but its linked evidentiary packet cannot be followed from the bounded restored Git input. This is not evidence of fabrication or deletion, and does not automatically fail current D record discipline or satisfy the old custody finding.

**Response / closure:** Provide a companion current navigation/custody disposition identifying which preserved report/reference locators are available from the fixed Git input and which old packet/supporting bytes are outside this assessment or require another named custodian/location. If availability is unknown, say so. Preserve the original report/seal. A fresh reader should understand the access limit without a recursive historical reconstruction. Importing the excluded packet, rewriting the historical auditor report or establishing off-host custody is not required by this bounded explanatory commission.

**Confidence:** High for missing fixed-tree targets; intentionally inconclusive about their custody elsewhere.

### A-000002/F-004: The three-campaign latency summary elides metric and protocol differences

**Requirement:** Current explanatory learning must match the support and uncertainty of the underlying investigations.

**Observation:** [SKILL](../../../../SKILL.md), lines 65–66, says a sustained AI-workload latency regression was flagged in three campaigns; [OPEN_ISSUES](../../../../docs/OPEN_ISSUES.md), lines 208–209, and PERFORMANCE line 299 associate the +11.1% mean-latency increase with “flagged in three campaigns”.

The [first full summary](../../../../benchmarks/results/investigations/root-placement-campaigns-2026-10-15/suite-abba-1/SUMMARY.md) records AI throughput −4.0% and mean latency +1.5%, labeled not significant. The [quick summary](../../../../benchmarks/results/investigations/root-placement-campaigns-2026-10-15/suite-quick-module-1/SUMMARY.md) records +15% mean latency but expressly calls the run a machinery check, “not evidence”, with large serial-control variation. The [full module-rooted summary](../../../../benchmarks/results/investigations/root-placement-campaigns-2026-10-15/suite-abba-module-1/SUMMARY.md), lines 26–40, records +11.1% mean latency, halves +5.2%/+16.6%, and itself calls the three unlike signals “independent campaigns”. All use the same candidate/control build pair; the quick and full protocols differ. The current shorthand promotes three warning signals into an apparently repeated supported latency finding without these qualifications.

**Impact / unknowns:** The candidate's recorded rejection remains an understandable conservative decision; this audit does not overturn it or infer a true unmeasured effect. The learning overstates replication/metric uniformity and can teach a misleading evidence rule.

**Response / closure:** Distinguish the first full throughput signal, quick machinery-only warning, and final full mean-latency result. State the shared binary pair and differing protocols if discussing recurrence/independence. Keep the rejection and all old summaries as history; a current explanatory note may qualify their stronger historical language. Do not count the quick sanity run as an additional rigorous latency replication. No rerun is needed to repair this claim.

**Confidence:** High for recorded metrics/protocols; no independent reanalysis of original campaign raw samples.

### A-000002/F-005: Qualify nominal lifecycle/fallback narration with recorded exceptions

**Classification:** Advisory explanatory risk, not a newly discovered source defect.

**Observation:** DESIGN §2.8, lines 162–165, broadly describes serial fallback when the split vector cannot describe usable work. §5.2, lines 401–409, describes failure joining created helpers and freeing all resources. Its lifecycle description, lines 387–389, gives enable/no-op and disable transitions without the active-collection exception. By contrast, [PEP-shaped draft](../../../../docs/pep-parallel-gc-v2.rst), lines 273–274, records unchecked joins as an unresolved implementation defect; lines 285–289 specify RuntimeError during active collection even for a would-be no-op; lines 494–500 explicitly deny complete partial-mutation recovery. OPEN_ISSUES A5–A7 preserves corresponding incomplete-vector/rollback questions.

These are differences between the explanatory nominal path and already documented qualifications, not proof here of what every source error path does.

**Response / closure:** Qualify the design narrative as nominal/implemented-under-stated-conditions where appropriate, link the existing unresolved failure-path issues, and state the existing active-collection call guard. An explanation reconciling the claims with their conditions also suffices. Do not change the operative failure policy, collector behavior or acceptance requirement under this D commission. Such changes require owner authority and technical work.

**Confidence:** High for document omission; deliberately no independent source correctness conclusion.

## Follow-up review of A-000001

No audit response closing the six prior findings was supplied/reviewed. The historical inconclusive verdict is preserved for its original revision, scope and older standard. This audit does not relabel it a pass or retroactively apply current D requirements to all old actions.

| Prior finding | Bounded follow-up disposition |
|---|---|
| F-001: complete project-unit coverage/adoption | Not closed. No full-project adoption is claimed; the 89-document inventory is not all-unit lifecycle coverage. |
| F-002: historical authority/independence | Not closed. The current commission preserves attributed authority and fresh-session separation; unavailable original historical authentication is not reconstructed. |
| F-003: old prospective chronology/validity records | Not closed for the old audit. Current D discipline is assessed under 1.1; do not import obsolete broad lifecycle/calendar requirements into ordinary D documentation repair. |
| F-004: missing historical records/source/environment support | Not closed. The selected old Git prose locators and upstream object now resolve; this narrows particular access observations, not the complete historical support/environment condition. |
| F-005: custody/retention/independent recovery | Not closed. Independently checked selected same-host document recovery and attributed GIL recovery improve narrow support; original complete runtime, all FT assets, whole-host survival and broad historical custody remain outside the established evidence. |
| F-006: remaining performance/hosted/landing trajectory | Not closed. Sixteen repaired source suites are recorded complete and newer workflow conclusions are owner-reported; negative individual results, source/job verification and acceptance remain distinct. Product landing readiness is not this audit's verdict. |

These are scope-limited follow-up observations, not six automatic failures of this explanatory repair. Corrections or full closure of old findings need a separately commissioned successor with the appropriate inputs, not worker self-closure or this report's inference.

## Documentation strengths and useful learning

The principal reviewer set already does substantial work well:

- README's question-based reading route, source/gitlink instructions and explicit “discussion, not ready to land” framing separate goals from established results. Historical measurements are identified by mode/source and do not masquerade as current universal claims.
- The design explains why private buffering, steal policy and authoritative versus optimization marks exist. Rejected coordination mechanisms are connected to measured costs, not treated as proof that complexity can never help. Root placement changes dispatch opportunity; it is not a general scalability guarantee.
- Exact list/tuple/dict investigations and mutation checks distinguish traversal contracts. Later test-phase recovery can hide a missed edge, so a passing whole-collection test alone is not enough for the direct-traversal claim. The supporting narrative preserves this learning rather than suppressing it.
- The creation-worker retention error is explicitly corrected as an unknown unintended retained fraction, not automatically “100% live”. Deterministic producer-release checks isolate the error; mixed/sustained/pyperformance workloads are not incorrectly invalidated with that creation pool.
- Dependency decisions preserve rejected alternatives: Coverage's different engine, Dulwich fallback and incompatible SQLAlchemy API migration. The approved pure-Python SQLAlchemy implementation is consistently applied across both sources/modes; readiness is not speed evidence, and FT attestation is not bypassed.
- Performance comparisons distinguish source ABBA from same-binary activation, compile-time overhead and pauses. Negative rows, halves, serial controls and contradictory unchanged-FT repeats remain visible rather than pooled into an invented cause. One binary pair with repeated process samples is not independent build replication; aggregate near-zero change does not establish neutrality.
- The latest GIL record carefully distinguishes recovered original binaries from a reconstructed runtime, preserves failed preparations and the owner amendment, and does not attribute nonreproduction to cleanup or the old runtime. Its rigor deserves a visible reviewer route.

The repair should mainly expose/reconcile this existing evidence, not produce new favorable outcomes. The useful general lesson is to maintain one discoverable latest-status disposition while retaining dated failures, and to preserve metric/protocol/context distinctions when compressing investigation narratives.

## Verdict and next action

**Nonconformant with the commissioned documentation consistency, navigation and claim-support checks at `40bfdcd41462caafb0f1fc38856529d4739cf48e`.** F-001, F-002 and F-004 are concrete explanatory repairs; F-003 is an explicit historical access disposition, and F-005 is advisory qualification. All are open. There is no full-project VP conformance verdict, code correctness verdict, performance-neutrality conclusion or release authority here. Broader historical support remains inconclusive outside this scope.

The prospective D commissioning record and selected immutable recovery discipline are present and usable. The negative verdict is not a demand for full record adoption, six mandatory views, every historical unit, new experiments, off-host backup or retroactive lifecycle paperwork.

**Observable handoff:** The worker should preserve this seal, record disposition of every recommendation, make bounded explanatory/nav repairs under DOC-000001, and provide exact repaired revision and actual checks. A fresh successor auditor can close findings when the stated reviewer routes/qualifications/access dispositions are observable at that revision. Worker acknowledgement is not independent closure. Escalate separately only if closure is made dependent on new technical experiments, collector/failure-policy changes, broader historical reconstruction/adoption, externally authenticated job evidence or materially expanded custody work.

**Role compliance:** Only this report and unique A-000002 assessment evidence were written. No input repair, project execution, remote write, old-packet expansion, CPython source/policy assessment or further agent delegation occurred. The report is a Project Audit, not a substitute Code Audit. The original input post-check matched. This one assessment is sealed and ends here.
