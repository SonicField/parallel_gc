# Informal review handoff reconciliation

## Goal and scope

Prepare a reproducible starting place for Matt and Pablo to understand, build,
test and discuss parallel GC. This is an informal engineering review, not a
formal PR or a claim of landing readiness.

Alex authorized the original documentation pass on 12 October 2026, initially leaving it uncommitted for evening review. He subsequently approved discrete local commits. Alex performs remote pushes. Collector source, benchmark programs and raw measurements are outside a documentation-only pass; later validation work has its own evidence records.

## Original documentation baseline and authority

The hashes below identify the 12 October baseline, not the current checkout. Use the parent gitlink and [VALIDATION.md](VALIDATION.md) for source selection and current evidence.

- Parent: `ce6dcecbdf1ed6fa8270ea1928cd1e339262a784`, branch `main`.
- CPython: `c67363fa59543ef5d572383af927f1cff88514a1`, branch
  `parallel-gc-upstream-port`; the parent records this exact submodule pointer.
- Upstream base: `333071231d3a46cccc32d7f44b99328c3299d0b1`.
- Verifiable Practice: `38d28d10035462e4c67f4b08d66638d3a4858216`, especially
  [document planning](https://github.com/SonicField/verifiable-practice/blob/38d28d10035462e4c67f4b08d66638d3a4858216/playbooks/document-planning.md)
  and [engineering standards](https://github.com/SonicField/verifiable-practice/blob/38d28d10035462e4c67f4b08d66638d3a4858216/concepts/engineering-standards.md).

Source defines implemented behavior. Tests define the exercised cases. Result
records define measured outcomes and their revisions. Proposed API decisions
remain proposals. Earlier results must retain their original provenance.

## Execution plan

| Step | Work | Observable completion condition | State |
|------|------|---------------------------------|-------|
| 1 | Establish source, evidence and publication state. | Exact revisions, local commits, CI limits and remaining defects are recorded. | Complete locally |
| 2 | Add one reviewer entry page. | A reader can identify the repositories, design intent, reading order, evidence and open issues without conversation history. | Complete |
| 3 | Reconcile lifecycle and adaptation descriptions. | Parent review documents describe lazy GIL/FT startup, warning/fallback/retry, child recovery and the deliberate FT parallel-only search consistently. | Complete |
| 4 | Select and reconcile the discussion draft. | One draft remains; its lifecycle, evidence and limitations agree with the implementation. Superseded drafts are removed and the README links the starting point near the top. | Complete; committed `9449cea` |
| 5 | Reconcile audit, source inventory and readiness records. | Repaired items cite evidence; unresolved defects and landing gates remain visible; informal review does not require completion of all landing work. | Complete |
| 6 | Reconcile benchmark and testing entry points. | Current summaries link exact raw evidence, retain regressions and exclusions, and label earlier CI correctly. | Complete |
| 7 | Verify and record the handoff. | Active local links resolve, documentation diffs pass whitespace checks, source/benchmarks/results are unchanged, and publication steps are explicit. | Complete locally |

## Failure conditions

The handoff fails if a reviewer follows an active link to an obsolete contract,
mistakes an older benchmark or CI run for current-revision evidence, cannot
obtain the pinned source, reads an unresolved defect as repaired, or infers
that the adaptive controller guarantees a global optimum.

## Publication follow-up

After evening review and local commit, push the CPython branch first and the
parent commit second. Verify a fresh public recursive clone, then run the
four-build matrix and manual Linux and Windows full-suite workflows against
that parent/submodule pair. Record their actual revisions, outcomes and skips.
These remote steps are pending, not passed by documentation reconciliation.

Use explicit ref names when pushing, after reviewing and committing the parent
documentation:

```bash
git -C cpython push origin \
    refs/heads/parallel-gc-upstream-port:refs/heads/parallel-gc-upstream-port

git push origin refs/heads/main:refs/heads/main
```

From the development host, trigger the matrix and three platform workflows with HTTPS:

```bash
HTTPS_PROXY=http://fwdproxy:8080 \
HTTP_PROXY=http://fwdproxy:8080 \
gh workflow run parallel-gc.yml \
    --repo SonicField/parallel_gc --ref main

HTTPS_PROXY=http://fwdproxy:8080 \
HTTP_PROXY=http://fwdproxy:8080 \
gh workflow run full-cpython-tests.yml \
    --repo SonicField/parallel_gc --ref main

HTTPS_PROXY=http://fwdproxy:8080 \
HTTP_PROXY=http://fwdproxy:8080 \
gh workflow run windows-parallel-gc.yml \
    --repo SonicField/parallel_gc --ref main

HTTPS_PROXY=http://fwdproxy:8080 \
HTTP_PROXY=http://fwdproxy:8080 \
gh workflow run macos-parallel-gc.yml \
    --repo SonicField/parallel_gc --ref main
```

For each run, verify the parent `headSha` and checked-out CPython commit, not
just the branch name. Record job outcomes and retained evidence in
[VALIDATION.md](VALIDATION.md). [TESTING.md](TESTING.md) explains how to find and
watch the runs. A new public recursive clone must obtain the same CPython pointer.

## Progress log

### 12 October 2026: baseline and plan

The parent has seven local commits ahead of its origin tracking ref and CPython
has four. Tracked trees were clean; unrelated untracked builds/results and the
newer PEP draft were present. Main documents still described eager FT startup
and older performance results. The source retains unchecked split-vector
allocation results, unique-ID allocation results and thread-join results.
GitHub API access was blocked by the environment destination filter, so live CI
status could not be checked. No remote write was attempted.

### 12 October 2026: reconciliation executed

Added `REVIEW_HANDOFF.md` (historical: `git show 724b74b:docs/REVIEW_HANDOFF.md`), selected the newer discussion PEP
and marked the older draft historical. Reconciled README, Getting Started,
Architecture, Design Post, fork/lazy plans, decisions, inventory, testing,
benchmarking, audit and readiness status. The inventory now describes all 56
paths in the upstream-base diff: 40 modified and 16 added.

Current benchmark summaries use the October GIL and lazy FT records, retaining
negative throughput/callback results, the FT float regression, exclusions,
limited convergence evidence and the missing current full GIL pyperformance
sweep. GIL/FT startup and local sanitizer repairs are distinguished from open
phase allocation and join-failure risks. FT serial exclusion is recorded as a
deliberate response to discontinuity/local-minimum risk, without promising a
global optimum.

### 12 October 2026: local document verification

- `git diff --check`: passed, no whitespace errors.
- `git -C cpython diff --name-status 333071231d3a46cccc32d7f44b99328c3299d0b1 HEAD`:
  all 56 changed paths appear in the inventory.
- Automated local-reference/fence checks: 17 Markdown files, 103 local links,
  no missing or untracked file targets and no unbalanced fences.
- Extracted Bash code blocks checked with `bash -n`: all 37 examples passed,
  including the publication commands above. One generic `<build>` block was
  reviewed as placeholder text rather than executed.
- RST heading adornments and inline-literal balance passed structural checks.
  No RST renderer is installed; rendered RST was not verified.
- `git -C cpython status --short`: empty. Parent changes are documentation
  only. Benchmark programs, raw results, source and submodule pointers match
  the baseline. No collector tests or benchmarks were rerun for prose edits.

### 15 October 2026: discussion-draft review and revision

Alex approved the six-point review and asked for explicit AI authorship,
Verifiable Practice attribution and starting-point status. Revised
[the discussion draft](pep-parallel-gc-v2.rst) to state that OpenAI Codex wrote
it under Alex's guidance, link the VP repository, and distinguish this
PEP-shaped discussion document from a formal proposal. Led with the design
goal, qualified compatibility claims, clarified conditional API behaviour,
separated controller invariants from performance measurements, linked evidence,
summarised bounded local validation and older CI, and removed the speculative
default-enablement roadmap. Collector behaviour and measurements are unchanged.

Local checks passed: all nine local RST link targets resolve; content assertions,
heading adornments, inline-literal balance, whitespace and configure-example
shell syntax pass. `git diff --check` passes and CPython's worktree remains
clean. No RST renderer is installed, so rendered appearance is not verified.
The documentation remains uncommitted; publication and current-checkpoint CI
are still pending.

### 15 October 2026: one visible discussion draft

Alex requested removal of superseded PEP documents and a prominent README
link. Deleted `docs/pep-parallel-gc.rst` and the obsolete `docs/PEP_OUTLINE.md`
stub; their committed versions remain in Git history. Kept
`docs/pep-parallel-gc-v2.rst` as the sole discussion draft and linked it
immediately after the README's project introduction. Removed the surviving
draft's reference to the deleted file and aligned entry-page descriptions with
its starting-point status. Earlier progress entries describe the work at their
recorded dates, not the current file set. No collector or benchmark changes.

CPython-facing `Doc/library/gc.rst` still contains stale child-recovery and
disabled-worker wording; the audit records that separate reference-doc task.
The handoff directs readers to the reconciled parent architecture/draft.
Evening review and commit, publication, a fresh public clone and remote
current-checkpoint runs remain pending. Nothing was staged, committed or pushed
during this pass.

Final combined validation passed for all 19 changed/new documents (17 Markdown
and two RST), including tracked evidence beneath linked result directories.
All 56 inventory paths were checked against the actual source diff. The staged
diff and CPython worktree remained empty.

### 15 October 2026: discrete commits and revision-aware evidence

Alex requested separate commits for the handoff docs, the discussion draft,
and revision tracking. Committed handoff documentation as `93bc7d1`, then the
discussion draft and removal of superseded PEP files as `9449cea`. Both are
parent documentation commits; the CPython gitlink is unchanged.

Added [VALIDATION.md](VALIDATION.md) as the single evidence/status entry point.
The README and handoff now identify source through the parent gitlink; dated
benchmark and inventory hashes remain historical provenance. Marked the
readiness checkpoint as its dated baseline instead of a live commit count.
Recorded the required Linux, Windows and macOS runs without claiming new passes.
Source-pair capture in CI and a macOS workflow are follow-up CI work, not part
of this documentation commit. Alex still performs remote pushes.

### 15 October 2026: CI preparation after documentation commits

Committed revision-aware documentation as `333f4dd`. Started CI work separately:
added a manual macOS four-build workflow with full-suite tests in both
feature-on builds, and one shared source-record action used by all platform
workflows. The macOS dependency/configuration setup follows the checked-in
CPython macOS workflow. Source evidence is retained before compilation, and
checkout mismatches stop the build. Local fixture and syntax checks are
recorded separately from hosted results; no remote workflow has been started
by the assistant. Alex must push CPython first, then the parent, and dispatch
the manual Linux full-suite, Windows and macOS workflows.

Local CI checks: all four workflow YAML files and the composite action parse;
20 POSIX workflow blocks plus the source action pass `bash -n`; the macOS
manual trigger, four build combinations and conditional full-suite selection
pass structural checks. The source-record fixture suite covers matching
revisions, wrong workflow SHA, unpinned CPython HEAD and dirty tracked source.
PowerShell execution, artifact upload and hosted compilation/tests are not
verified locally. These checks do not establish a passing platform matrix.

### 16 October 2026: first platform results and macOS path correction

Alex reported success for Linux focused run `38730251690`, Linux full-suite
run `38730312362` and Windows run `38730315605`; detailed source/artifact and
skip/rerun examination is still pending. Read the failed macOS log for
`38730319127`: all four ARM64 configurations built and imported their 116
modules, then failed before tests when the workflow executed the `Python/`
directory as `build-macos/python`. The build commands identify the actual
executable as `python.exe`. All four source records identify parent `724b74b`
and CPython `c67363fa59`.

Corrected the six macOS workflow invocations to `build-macos/python.exe` and
recorded the failure without claiming tests passed. The intended falsifiable
next step is a hosted rerun that gets past configuration verification and
executes the selected tests. No collector code, test selection or benchmark
implementation was changed.

### 17 October 2026: integration evidence and unresolved completion

Four fresh baseline/current GIL/FT PGO+LTO builds and selected tests passed. The repaired full project benchmark completed all eight ABBA legs. GIL and FT source comparisons record negative findings rather than a neutrality claim; the FT module-rooted controlled collections are consistently slower in both halves. [PERFORMANCE.md §4.1](PERFORMANCE.md) links both complete reports and their raw evidence.

The first corrected full-default pyperformance suite failed Dask and Genshi. All eight subsequent all-program compatibility checks reproduce these failures; FT additionally rejects five programs whose native dependencies enable the GIL. Evidence commits `cf7ac42` and `10015cf` preserve complete logs, partial results and the diagnostic scope. No dependencies or collector logic were repaired, no programs omitted, and no GIL-mode check bypassed. Dependency compatibility work awaits agreement; the sixteen rigorous comparisons remain incomplete.

Alex reported publication and new hosted dispatches for the integrated source, but current run IDs, source artifacts and job outcomes remain unavailable. Earlier platform passes do not satisfy this checkpoint. The main README, validation, performance and open-issue records now distinguish historical benefit measurements, completed integration measurements, diagnostic failures and missing CI evidence. This reconciliation is a documentation step, not completion of the tests/benchmarks/handoff goal.

Local documentation verification: all 74 local links across the five changed Markdown files resolve to tracked files/directories; code fences balance and all nine Bash examples pass `bash -n` without executing them. Quoted counts, ranges and paired percentages match the preserved GIL/FT machine analyses. The first numerical checker used the wrong row-kind spelling (`controlled` instead of the recorded `controlled_collection`) and failed; the corrected check passes without changing data or quoted results. `git diff --check` passes. Collector source, submodule pointers, benchmark code and raw results are unchanged by this documentation diff.

### 17 October: unchanged full FT repeat completed

The repeat ran all four original full invocations using the same optimized FT source/binary pair. Evidence commit `50bcd27` preserves the complete closing leg, all 72 analysis rows, raw logs, input/archive hashes and independent checks. All twenty-four analyser tests pass; archive replay reproduces every row and source/input metadata except expected input path changes.

The original broad module-rooted controlled slowdown does not reproduce: every module case has opposing ABBA halves. Seven frame controlled cases still increase in both halves (+2.43% to +5.91%), and three sustained throughput means decrease. The comparative write-up links the original full, focused and repeated full experiments without pooling them or claiming a repair. The main README, performance, validation and open-issue entry points record the follow-up. Collector and benchmark implementation remain unchanged. Pyperformance dependency agreement, all sixteen rigorous suites and current hosted CI evidence remain outstanding; this is not a completed handoff.

### Dependency repair follow-up, 19 October 2026

Dependency-only work was approved. Six separately committed repairs pass targeted baseline/current GIL/FT checks: Cloudpickle and Genshi compatibility patches; Coverage with CTracer; native Dulwich, MarkupSafe and Greenlet upgrades. The original benchmark programs and CPython are unchanged. [Plan, commands and evidence](../benchmarks/dependency-repair/PLAN.md).

Alex subsequently approved SQLAlchemy 1.4.19's [supported pure-Python build](../benchmarks/dependency-repair/SQLALCHEMY.md) consistently across both sources and build modes. [Repeated complete readiness](../benchmarks/dependency-repair/full-readiness-evidence/README.md) passes all 100 original programs in all eight contexts, with 127 named results each and zero failures. FT stays GIL-disabled and all four fresh complete environments pass `pip check`. The sixteen rigorous suites remain outstanding; diagnostic execution checks are not performance evidence. No workload rewrite or unsafe GIL override was made. Hosted CI outcomes remain unavailable. This is not a completed handoff.

Write-up verification: all 48 numerical table rows and the three-experiment count/direction summary match the preserved analyses. Across the nine changed documents, 101 local links resolve, code fences balance and thirteen Bash examples pass `bash -n` without execution. `git diff --check` passes. No benchmark parameters or measured data changed in this documentation commit.
