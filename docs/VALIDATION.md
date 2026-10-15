# Parallel GC validation record

## What this record means

This is the single entry point for validation evidence, not a claim that the
latest branch tip is green. The parent repository's `cpython/` gitlink selects
the source. A branch name or an earlier successful run does not identify what
was tested in a later checkout.

From the parent repository, identify the checkout with:

```bash
git rev-parse HEAD
git ls-tree HEAD cpython
git -C cpython rev-parse HEAD
git -C cpython status --short
```

The gitlink and checked-out CPython commit must match. A dirty CPython worktree
is not evidence for that clean commit. Do not put the parent commit's own hash
inside this record: CI identifies its parent revision through the run's
`headSha` and checkout evidence.

Benchmark and local-test reports retain their measured revisions permanently.
Documentation-only commits do not change those measurements or the CPython
gitlink. Collector changes need new evidence; a claim that older results still
apply requires an explicit account of the intervening changes.

## Recorded evidence: 15 October 2026

The source reviewed in the October handoff is CPython
`c67363fa59543ef5d572383af927f1cff88514a1`. This is a dated evidence baseline,
not a second mechanism for selecting the current source. Check the gitlink
above when using a later parent revision.

| Evidence | Source and outcome | Limits |
|----------|--------------------|--------|
| [Local lifecycle and failure tests](LAZY_POOL_CREATION_PLAN.md) | Recorded GIL and FT debug, optimized lifecycle, ASan and TSan selections pass. | Exact selections and source revisions are in the linked record. ASan leak detection was disabled; TSan options and suppressions are recorded. Not a full cross-platform validation. |
| [GIL performance](../benchmarks/results/arm64-316-669ed6b-full-analysis-2026-10-08.md) | Collector `669ed6b17e`, including throughput improvements and callback-interval regressions. | One AArch64 host; no full GIL pyperformance sweep after lazy startup. |
| [FT performance](../benchmarks/results/arm64-316-1958301-ft-lazy-analysis-2026-10-08.md) | Collector `195830171f`, including full project and pyperformance ABBA results. | One host; negative results and exclusions remain in the report. `c67363fa59` subsequently changes release-build test guards only. |
| [Earlier Linux full suite](https://github.com/SonicField/parallel_gc/actions/runs/37615265794) | Recorded success at `d396f837b9`. | Before the current lazy-pool work; not current-source evidence. |
| [Earlier Windows full suite](https://github.com/SonicField/parallel_gc/actions/runs/37615268403) | Recorded success at `d396f837b9`. | Same limitation. |
| [Earlier four-build matrix](https://github.com/SonicField/parallel_gc/actions/runs/37663869128) | Recorded success in all four jobs at the preceding published checkpoint. | The exact source pair has not been recovered into this record; the run predates the current local commits. |

These remote outcomes come from previously captured results. Live GitHub status
was unavailable during reconciliation; it has not been rechecked here.

## Required remote runs

For the source pair selected by the parent being published, these outcomes are
still pending:

| Platform and workflow | Required coverage | Recorded status |
|-----------------------|-------------------|-----------------|
| Linux, `parallel-gc.yml` | GIL and FT, feature-on and feature-off; focused collector and parent harness tests. | Pending new run. |
| Linux, `full-cpython-tests.yml` | GIL and FT feature-on builds; full default CPython suite. | Pending new run. |
| Windows, `windows-parallel-gc.yml` | GIL and FT feature-on builds; focused collector and parent harness tests, then full default CPython suite. | Pending new run. |
| macOS | GIL and FT builds; focused collector and parent harness tests, feature-off controls, and full default CPython suite in feature-on builds. | Workflow not yet present at this documentation checkpoint. |

Full default-suite runs begin with parallel policy disabled. Focused tests
explicitly exercise activation and parallel dispatch. Report skipped tests,
rerun failures and dependency exclusions, not just the workflow conclusion.
Linux hosted CI and local AArch64 evidence are different platform records;
record the actual runner architecture rather than inferring it from the OS.

## Recording a run

Each result must identify:

- run URL, attempt number and actual parent `headSha`;
- the parent's recorded CPython gitlink and the checked-out CPython revision;
- OS, architecture, GIL/FT mode, feature-on/off setting and build flags;
- test commands, outcomes, skips, reruns and retained log/artifact links.

Record job-level outcomes even when a workflow has mixed results. Keep failed
attempts when adding a successful repair run. A pass on an older source pair
does not validate a newer pair. Do not call the publication checkpoint
validated until all required jobs for that pair have recorded passes and
remaining coverage limits are stated.

Source-pair capture in the workflows is a CI follow-up, not something these
documentation edits have implemented. [TESTING.md](TESTING.md) gives dispatch
and log commands; the [handoff log](HANDOFF_RECONCILIATION_PLAN.md) tracks
publication work. Updating this evidence record does not require rewriting
the architectural narrative or changing hashes in historical reports.
