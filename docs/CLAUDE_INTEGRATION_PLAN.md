# Integrating the beneficial review work

Status: execution approved by Alex, 16 October 2026. Local imports and atomic commits are authorised; remote pushes remain Alex's responsibility.

## Goal and method

Give core developers a clearer, better-tested discussion starting point while preserving the collector's working design and recording what the experiments taught us.

Use [Verifiable Practice](https://github.com/SonicField/verifiable-practice): define the outcome of each step, attempt a meaningful falsification, record failures and uncertainty, then make an independently reviewable commit. Passing tests support proceeding; they do not prove correctness or performance neutrality.

The useful general lesson is that additional coordination must earn its cost across workloads. The rejected experiments improved some cases but did not meet the wider requirements. This does not make complexity inherently wrong, or establish that the remaining weaknesses are unfixable.

## Starting point and boundaries

The primary parent is `bb87205168d9097c3201081a05e43bea2e9fdef1`; its CPython gitlink and checkout are `c67363fa59543ef5d572383af927f1cff88514a1`. Both tracked worktrees were clean when this plan was written. Existing untracked builds and result directories must be preserved.

Candidate work is local in `/home/alexturner/local/parallel_gc_claude`:

| Work | Candidate | Intended disposition |
|------|-----------|----------------------|
| Documentation consolidation and experimental records | Parent `claude/A1-docs-consolidation`, `c21af71` | Keep, with the review adjustments below |
| Unreferenced-code removal | CPython `b3b5557ed5` | Keep after reachability and build checks |
| Production marking verifier and retirement of test-only marking implementation | CPython `ac53a434a0`, final test correction `be478ea017` | Keep as a coherent tested change |
| Creation-pool retention fix | Parent benchmark commit `6c8bf14` | Keep with scheduling-sensitive regression coverage |
| Module-rooted workloads | Parent benchmark commit `306644b` | Keep the dimension; resolve the root-test definition before integration |
| Waiting, private-work publication, list splitting and queue-store experiments | Local `investigation/*` branches | Preserve their evidence; do not integrate collector changes |

Reviews: `.vp/reviews/peer-review.md` and `peer-review-technical-checks.md` in the candidate clone. Detailed original commands and results are in its `.vp/prs/` directory.

No change to active atomics, barriers, phase structure, thresholds, adaptive policy or failure semantics is authorised by this plan. Do not import new project-wide acceptance or authorisation rules as a side effect of documentation consolidation: reconcile recorded decisions with Alex explicitly. Execution and commits require approval; Alex performs remote pushes. Work remains on the fork, not upstream CPython.

## Step 0 — Record the integration manifest

Before executing, recheck both worktrees and resolve the full candidate hashes. Record source commits, their dependencies, imported paths and excluded experiments. Use current primary `main`, not the candidate's older parent base `724b74b`.

**Stop if:** tracked user changes overlap, a candidate has changed since review, or an active collector change appears among the intended cleanup. Discuss it rather than silently adapting it.

## Step 1 — Consolidate the documentation

Adopt the README reading route and the GETTING_STARTED, DESIGN, PERFORMANCE and OPEN_ISSUES structure. Retain TESTING, VALIDATION and the handoff log, reconciling their links and newer platform evidence. Keep historical evidence at its measured revisions; preserve explicit `git show 724b74b:<path>` destinations where necessary. Superseded plans can leave the active tree after this check.

In the consolidated material:

- Put optional activation, automatic tuning and progressively useful parallelism near the README opening.
- Retain the reasons behind the marking protocols, local buffers, serial crossover, lazy startup and fork recovery.
- Add the architecture of exact-container traversal and shared dictionary-layout logic; explain why parallel-aware PGO supplements explicit fast paths.
- Record root placement as a benchmark dimension and the costs revealed by the rejected experiments, without declaring the current design universally robust.
- Qualify historical collection-shape results as having unintended retention and stack roots; the actual retained fraction in old runs is unknown. Do not discard unrelated results.
- Correct the validity prediction/verdict and remove the unsupported claim that the quick smoke comparison excludes regressions above 5–6%.
- Review SKILL guidance for the same evidence-led lesson, not a presumption against future changes.

**Check:** local links and anchors; rendered Markdown/RST where tooling permits; evidence destinations; no unrelated CI/source changes. Walk through five reviewer questions using the new documents: obtain the full project, build both modes, explain the two marking protocols, interpret performance results, and identify discussion versus landing blockers. A missing answer or lost design reason requires correction.

**Commit:** documentation consolidation and learning record. Keep PEP navigation/claim corrections in a separate commit, preserving attribution and its discussion-only status.

## Step 2 — Remove genuinely unreferenced code

Integrate B1 independently. Verify every removed symbol against all platform and preprocessor paths; do not infer that a function is unused merely because one local build omits it.

**Check:** reproduce the focused unused-function/variable compilation failure before removal, then require clean GC-object builds afterward in GIL/FT debug/release configurations. Compare focused outcomes and defined global symbols. A surviving reference, unexplained outcome change or active-path edit blocks this step. Document the compiler check's blind spots for unused typedefs and inline functions.

**Commit:** CPython dead-code cleanup, followed by its own parent gitlink update. This is not a performance optimisation claim.

## Step 3 — Make marking tests exercise production

Integrate B2 together with `be478ea017`'s final correctness test; do not adopt its superseded work-balance expected failure. Retain the serial-recompute ALIVE verifier and checks that a parallel pass actually ran. Worker balance and optimiser effectiveness remain benchmark questions, not deterministic correctness assertions.

**Check:** reproduce root/edge mutations in scratch builds, recording which tests detect them and which do not. Require zero missing/extra marks on unmutated graphs and cover module/frame roots, supported worker bounds and untracked objects. Confirm the verifier is opt-in and debug-only, and release code has no added verifier traversal. Run focused GIL/FT tests, fork tests and applicable ASan/TSan selections, with skips, suppressions and allocation-failure limits stated.

**Commit:** the coherent production-test/verifier change and retirement of the redundant test-only implementation; then a separate parent gitlink update. Refresh the documentation's current-source descriptions without relabelling historical evidence.

## Step 4 — Repair benchmark ownership, then add rooting coverage

First integrate the creation-pool fix alone. Test schedules where one worker processes several tasks and where tasks spread across workers. Dropped objects must become collectible while helpers remain alive; seed/order behaviour and exception propagation must remain intact. Record the pre-fix failure and post-fix result.

**Commit:** retention fix and regression tests.

Use the contract agreed with Alex: sustained heaps are held in module state between operations; shuffle and churn may temporarily hold stack references. A separate controlled collection checks module-only roots at its collection boundary. The sustained test must detect a persistent whole-heap local, not reject a temporary new batch. Include a planted-reference positive control; do not merely exclude another local from the old, stronger assertion.

**Check:** collection-boundary observations appropriate to that contract, holder cleanup, identical seeded heaps, separate result keys and compatibility of existing keys. Repeat the harness suites in GIL/FT debug/release builds. Require no unexplained failure; repeated passes alone do not settle a race.

**Commit:** module-rooted workloads and their tests, separately from the retention fix. Update the documented full-run duration, approximately 95 minutes per invocation on the measured host.

## Step 5 — Validate the integrated source and measurements

Add a focused GCC/Clang warning check in its own CI commit, without imposing those flags on unrelated upstream sources. Then publish the CPython commits before the parent gitlinks, and run Linux, Windows and macOS workflows for the actual integrated source pair. Retain focused activation tests, feature-off controls and both feature-on full CPython suites; report job-level skips and failures, not just workflow conclusions.

For performance, build clean matched PGO+LTO GIL and FT binaries, confirming that parallel paths are trained. Run standard full project ABBA campaigns and pyperformance comparisons. To isolate the source cleanup, compare pre-integration `c67363fa59` and the final source **using the same corrected benchmark harness**. Comparing old results from the retaining harness with new corrected results cannot identify a collector performance change.

Agree measurement acceptance criteria before the campaigns. Report per-workload throughput and the distinct collection/callback timing metrics, serial controls, both ABBA halves, raw data and build provenance. Investigate unresolved regressions; do not classify every difference as build noise. An exclusion bound requires a suitable uncertainty analysis, not the largest difference observed in a smoke run.

**Commit:** new validation and measurement records separately from implementation. No formal upstream proposal is part of this step.

## Progress log

For each completed step record: imported commits, destination commits, exact checks and exit status, failures/skips, what was learned, remaining uncertainty and the next action.

| Step | State | Evidence / next action |
|------|-------|------------------------|
| Plan | Approved | Alex authorised proceeding with VP and regular atomic commits |
| 0: manifest | Complete | Tracked worktrees clean; candidate identities and exclusions recorded below |
| 1: documents | Complete locally | Consolidation and separate PEP navigation/qualification commit; historical evidence retained in git |
| 2: dead code | Complete locally | CPython `442a97213f`; four before/after feature-on builds and two feature-off controls; warning gates and symbol checks |
| 3: production tests | Pending | Recheck mutation sensitivity and dynamic analysis |
| 4: benchmarks | Retention repair verified; rooting agreed | Module-held sustained heap with temporary stack references; separate module-only controlled collection |
| 5: validation | Pending | Fresh candidate-source CI and matched-harness measurements |

### 16 October: manifest and execution approval

Local fetch imported parent candidates into `integration/claude-docs` and `integration/claude-benchmarks`; no working files changed. Primary changes since candidate base `724b74b` are confined to the macOS workflow, VALIDATION and the handoff log, which will be preserved.

Resolved candidate identities:

- Documentation: `c21af71d3d88c11cfb6ee14a9a3438ca561441fb`.
- Benchmark additions: `306644b59682223980fd08cf2262d3b8e40a3eb5`.
- Dead-code cleanup: `b3b5557ed5afdb88e3a01f4fcc244a87fab0fcfe`.
- Production verifier: `ac53a434a09d5082cd4a001997855f9a3dc44da3`.
- Final correctness test: `be478ea01733664477eed823f5e85a2fbaa0f89f`.

Excluded: every experimental collector change on `investigation/*`; no blanket merge of candidate parent gitlinks. PEP edits remain a separate unit from the documentation consolidation.

### 16 October: preserve experiment evidence before consolidation

Imported 42 historical evidence files from documentation candidate `c21af71` into the two dated investigation directories. Git blob comparisons match all 42 original files; all 12 campaign JSON files parse. The initial import appended final newlines to twelve JSON files; the byte comparison detected this and the original endings were restored before commit. No measurements were rerun or relabelled. Recorded patch files are experimental evidence, not changes to collector source.

The repository ignores JSON/log results by default; these specific imported evidence files are explicitly included in the evidence commit. Historical patch/analysis files contain original trailing whitespace, reported by `git diff --check` and retained to preserve their bytes. New documentation is checked separately.

### 16 October: documentation consolidation

Adopted the five-document structure from `c21af71`, with integration-specific corrections: design intent up front; explicit container traversal architecture checked against current source; retained-buffer and termination tradeoffs; qualified historical garbage fractions; candidate-only module benchmarks; no inferred 6% exclusion bound; and preservation of the current design-change discussion requirement. Newer Linux/Windows reports and macOS executable-path repair remain recorded. Alex's captured macOS rerun reports feature-off passes; active-collector final outcomes remain unknown.

Navigation walkthrough: README identifies all repositories and the gitlink; GETTING_STARTED gives four isolated builds; DESIGN §2.7/§3.3/§3.6 distinguish the marking protocols; PERFORMANCE separates program throughput, callback intervals and stopped-world work; OPEN_ISSUES separates discussion from landing gates. Added DESIGN §3.9 so the retained traversal/PGO reasoning is not available only through old plans.

Checks: 17 active/review documents, 99 local file destinations and 14 historical `git show` destinations resolve, including one CPython-history destination. The initial checker incorrectly looked for that CPython object in the parent repository; repository-aware resolution corrected the check. `git diff --check` passes on new/modified active material. Markdown/RST renderers (`markdown_it`, `docutils`) are unavailable, so rendering and external URLs are not verified. CPython, its gitlink, benchmark workloads and CI files remain unchanged; the pyperformance runner changed only its documentation-path error message. Historical raw evidence remains byte-identical. Temporary redirects keep the unchanged PEP's old links valid until its separate commit.

### 16 October: discussion draft navigation and qualifications

Updated the draft separately: links use the consolidated documents, FT propagation scaling is qualified, historical creation-pool limitations are stated, and proposed numerical criteria are not represented as newly adopted policy. AI attribution, VP link and discussion-only status remain. Removed the five temporary redirects after replacing their active links; original audit and lifecycle records remain available through the recorded git-history commands. No implementation or benchmark workload changed.

### 16 October: independent benchmark repair while source edits are held

The repository instructions require reading CPython's linked AI policy before source edits. HTTPS retrieval returned 403 and the knowledge reader refused external access; requested a local copy or clarification from Alex. CPython candidates are locally fetched but unapplied. Also requested the intended sustained module-rooting contract before changing its scheduling-sensitive test.

Completed the independent creation-pool fix and strengthened its tests: controlled schedules fail before the repair with 10/40 and 40/40 retained heads; the caller-survivor case fails with 40 retained instead of 32. All ten tests pass after the repair on the host interpreter. Mode-specific repeats and binary provenance are recorded in [the ownership report](../benchmarks/results/investigations/creation-pool-retention-2026-10-16.md). No collector behaviour, heap generator, benchmark duration or output schema changed. This is not a performance claim.

Final repeat outcome: 40 full harness suites per reused GIL/FT release/debug binary (20 disabled, 20 armed), 400 tests each, 1,600 in total, zero failures/errors. The reused binaries report dirty source stamps, so this is harness ownership evidence, not fresh clean-source CPython validation. Active-document whitespace checks pass. Remaining decisions: access to the policy required by repository instructions, the precise sustained rooting contract, and campaign acceptance criteria before performance measurement.

### 16 October: source work and rooting contract unblocked

Alex explicitly instructed proceeding without the repository AI-policy check. The sustained rooting contract is module ownership between operations, allowing temporary stack references while the heap is mutated. Controlled single-collection tests retain the stronger module-only boundary check. Neither decision authorises active collector-design changes. Campaign acceptance criteria still need agreement before performance measurements.

Started four fresh, non-PGO baseline builds from a detached `c67363fa59` worktree in `/tmp/parallel-gc-integration-fKKFb7/source`. The local check script records configure/build logs, focused unused-function/variable diagnostics, defined global GC symbols, and focused test outcomes for GIL/FT release/debug. These are cleanup correctness checks, not benchmark builds.

### 16 October: unreferenced-code cleanup committed independently

CPython `442a97213f` adopts B1, with empty preprocessor guards and orphan headings removed. All removed names have no surviving repository references. Four fresh before/after configurations pass focused tests with identical counts/skips and unchanged defined global GC symbols; the focused warning gate fails on the baseline and passes after cleanup. Both feature-off debug controls also pass. A misspelled local test-module argument initially failed imports and was corrected without changing project tests. Full logs, build limitations and reproduction are in [the cleanup report](../benchmarks/results/investigations/dead-code-cleanup-2026-10-16/README.md). No performance claim, active collector change or remote write. The parent gitlink update is kept separate from benchmark additions.
