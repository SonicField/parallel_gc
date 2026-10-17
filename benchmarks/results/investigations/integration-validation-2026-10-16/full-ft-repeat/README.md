# Unchanged full FT repetition

## Scope

Repeat the original full FT invocation after the [focused diagnostic](../focused-collections/RESULTS.md) did not reproduce its broad module-rooted slowdown. The focused run changed process context by omitting preceding sustained phases and importing the benchmark as a normal module. This repeat uses the original `__main__` entry point, workload sequence and parameters. No collector or benchmark source changed.

Baseline/current/current/baseline use the same existing GCC 11.5 AArch64 PGO+LTO FT binaries at `c67363fa59543ef5d572383af927f1cff88514a1` and `388fd5bb46fdda6b464db566faf818505c3d6eef`. Every invocation is unchanged `--full --include-synthetic --json`: five runs, 60-second sustained phases, four application/creation threads, nominal 500,000-member heaps, seed 42, three controlled warmups and 80% surviving clusters. Affinity is 0–31 and NUMA CPU/memory node 0. Worker choice remains adaptive, not fixed sixteen.

The question is whether the original negative pattern repeats in the original invocation context. A failed repeat weakens source attribution without erasing old data. A repeat still does not distinguish source from this PGO binary pair; independent rebuilt profiles and generated-code inspection remain possible follow-ups. No acceptance cutoff, significance claim, noise floor or automatic code repair is adopted.

## Completed and live work

| Leg | Source | Observed state |
|-----|--------|----------------|
| 1 | Baseline | Complete, 09:58:22–11:32:48 UTC on 17 October 2026; 94 min 26 sec. Native/source/binary/benchmark checks pass. |
| 2 | Current | Complete, 11:32:48–13:07:08 UTC on 17 October 2026; 94 min 20 sec. Source/binary/benchmark fingerprints and document checks pass. |
| 3 | Current | Started at 13:07:08 UTC; still running at this record. |
| 4 | Baseline | Not started at this record. |

Scratch root: `/tmp/parallel-gc-ft-full-repeat-20261017-NZLRWT`. Controller execution session: 74721. Its output is consumed by the live wait cell 569; do not start a second session consumer or restart the benchmark because an observation wait expires. On a process check at 11:32:19 UTC, baseline was active at about 249% CPU and its log had reached the final module-cache mixed workload. It subsequently completed normally. No source-effect conclusion is inferred from one leg.

Baseline records parent `ebdba89d428d1b0ff53a396edff22390c40b9ae2`, dirty with unrelated untracked directories. The measured benchmark and CPython content remain unchanged, independently checked. Preserve that parent observation; do not call it a clean parent checkpoint. Source is clean, its patch digest empty, and native/runtime preflights pass.

## Completed-leg checks and evidence

[Evidence](evidence/) preserves the complete baseline leg 1 and current leg 2 JSONs and logs, both preflights, source revisions, original fingerprints and parent/host provenance. Copies are byte-identical; compressed logs decompress byte-identically to scratch originals. `SHA256SUMS` covers the archives and `ORIGINAL-SHA256SUMS` the decompressed logs. No scratch originals were removed.

The first completed document contains all eight sustained comparisons and sixteen controlled cases, with five valid samples per arm. Standard parameters, source/compiled mode, affinity and NUMA policy match the original full experiment. All controlled generated-member sequences also match the original data in both arms. `leg-1-checks.json` binds those checks to the raw input hash. Counts are generated cluster members, not all supporting GC containers or reclaimed objects.

Leg 2 passes the same single-document checks. Its sixteen controlled generated-member sequences match both the original full data and repeat leg 1, in both arms. `leg-2-checks.json` binds the checks to its raw input hash. These are document-integrity checks, not a two-leg source-effect result. The controller's successful post-leg fingerprint output and start of leg 3 were observed on its existing handle.

The preserved complete-project analyser refusal was taken after leg 1, when leg 2 was absent. The repeat still lacks complete legs 3 and 4. No missing leg was manufactured or source-effect comparison reported from incomplete data.

A host process-name/CPU snapshot is an observation at launch, not evidence of continuous complete machine isolation. No other project measurement was observed at launch. Numerical validation runs use spare CPU 32; lightweight artifact copying and hash checks were not affinity-pinned. No builds or competing benchmark campaigns run during measurement.

## Completion and replay

The controller runs all four original full commands, checks source/binary/benchmark fingerprints after every leg, then runs:

```bash
python3 \
    benchmarks/results/investigations/integration-validation-2026-10-16/analyse_project_abba.py \
    /tmp/parallel-gc-ft-full-repeat-20261017-NZLRWT \
    --mode ft
```

After all four documents are archived here, the same command can target `full-ft-repeat/evidence`. Preserve every sample, both halves, serial controls and original/archived hashes. Keep this repetition separate from the original full ABBA and focused diagnostic rather than merging different time windows silently.

Hosted Linux/Windows/macOS evidence and the dependency-blocked sixteen pyperformance suites remain separate incomplete requirements. Two completed repeat legs do not finish this repetition or the handoff goal.
