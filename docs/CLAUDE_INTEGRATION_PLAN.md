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

Then define module-rooted precisely with Alex: absence of persistent heap-holder locals, or absence of every transient stack reference at collection. The current probe sometimes sees another worker's `new_clusters`; it also excludes shuffle frames. Make a deterministic test of the agreed contract, with a planted-reference positive control. Do not hide the failure by simply excluding another local.

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
| 1: documents | Pending | Preserve the useful consolidation and apply review adjustments |
| 2: dead code | Pending | Establish reachability and focused warning baseline |
| 3: production tests | Pending | Recheck mutation sensitivity and dynamic analysis |
| 4: benchmarks | Pending | Resolve the rooting contract before fixing its test |
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
