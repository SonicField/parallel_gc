# Focused FT collection results, 17 October 2026

## Outcome

The isolated controlled-collection invocation does not reproduce the full suite's broad module-rooted slowdown. Five of eight module cases have lower current-binary means; three have higher means (+0.34% to +1.32%), with only module web-server higher in both halves. The full invocation previously showed all eight higher in both halves (+18.72% to +34.81%). Frame layered also does not reproduce its prior both-halves increase.

This is not proof that the original result was noise, that performance is neutral, or that a repair worked. No repair was made. The same source/binary pair produces a different pattern under a different invocation context. Preceding sustained workloads, heap/allocator state, adaptation exposure and importing the benchmark as a normal module rather than `__main__` remain uncontrolled differences. **Verdict: Inconclusive about cause.** The focused result weakens a context-independent explanation; repeat the unchanged full FT invocation before choosing a cause or a code change.

The focused experiment does record negative measurements: five of eight frame cases and three of eight module cases have higher overall current means. These are reported below, not described as an accepted null result. No significance, noise floor or acceptance threshold is assigned.

## Protocol and verification

The [pre-registered protocol](README.md) uses the existing controlled-collection function unchanged, all sixteen cases, five measured pairs per case, three warmups per arm, nominal 500,000-member heaps, four persistent creation threads, seed 42 and 80% surviving clusters. Worker choice is adaptive; sixteen is the reported ceiling, not a fixed active count. Each process starts at four. This campaign does not record a worker history during timed collections; its end-of-process snapshots are not a tuning explanation.

Four fresh processes used the same existing GCC 11.5 AArch64 PGO+LTO FT binaries in baseline–current–current–baseline order, with affinity 0–31 and NUMA CPU/memory node 0. Baseline is `c67363fa59543ef5d572383af927f1cff88514a1`; current is `388fd5bb46fdda6b464db566faf818505c3d6eef`. Parent tooling checkpoint is `f9924bc`. The parent retains unrelated untracked files; that dirty observation is recorded, not relabelled clean. Both CPython worktrees are clean.

Launcher timestamps from the execution tool output are 09:49:04, 09:50:00, 09:50:56 and 09:51:51 UTC for the four starts, closing at 09:52:47 UTC. An original controller log file was not captured; these timestamps transcribe the observed tool output. The execution session 20175 completed with exit 0.

All native/runtime preflights, four source/order checks, sixteen-case coverage, sample/parameter/placement checks and original binary/benchmark/driver fingerprints pass. Every leg remains compiled/runtime FT with an active, enabled helper pool at the end and no startup failure. Every controlled generated-member sequence matches both collector arms and all four focused legs. All sixteen sequences also match the original full-suite comparison. These counts are generated cluster members, not every supporting GC container or reclaimed object.

The analyser reuses the full analysis arithmetic. A separate jq calculation checks both source means, overall change and both half changes for both arms in all sixteen cases: 160 arithmetic fields agree within a floating-rounding tolerance of `1e-9`. This tolerance checks calculation consistency, not performance acceptance. All nineteen wrapper/analysis tests and twenty-four existing full-analysis tests pass. Machinery tests do not establish performance.

## All measured cases

Means are milliseconds inside the existing `gc.collect()` bracket. Source legs have equal weight. Change is `100 × (current / baseline − 1)`; positive is slower. Half 1 compares leg 2 against leg 1; half 2 compares leg 3 against leg 4. Serial GC is the separate control. These are not application-throughput measurements or FT stopped-world durations.

| Rooting / shape | Baseline parallel ms | Current parallel ms | Parallel change | Half 1 | Half 2 | Serial control change |
|-----------------|---------------------:|--------------------:|----------------:|-------:|-------:|----------------------:|
| frame / chain | 31.03 | 31.39 | +1.16% | -2.06% | +4.28% | +1.38% |
| frame / tree | 32.68 | 32.76 | +0.22% | +0.22% | +0.23% | +0.41% |
| frame / wide_tree | 31.28 | 31.89 | +1.95% | +3.16% | +0.76% | +0.65% |
| frame / graph | 39.48 | 37.34 | -5.43% | -9.71% | -0.89% | -3.05% |
| frame / layered | 43.07 | 40.99 | -4.82% | -10.98% | +1.83% | -14.73% |
| frame / independent | 31.43 | 31.48 | +0.16% | +0.27% | +0.05% | +0.81% |
| frame / ai_workload | 42.88 | 41.47 | -3.27% | -5.32% | -0.98% | +2.68% |
| frame / web_server | 31.54 | 32.24 | +2.22% | +4.14% | +0.31% | +0.70% |
| module / chain | 34.69 | 34.89 | +0.55% | -0.90% | +2.04% | -1.25% |
| module / tree | 37.04 | 37.17 | +0.34% | +3.40% | -2.57% | +1.21% |
| module / wide_tree | 37.67 | 35.76 | -5.06% | -10.50% | +1.06% | -2.18% |
| module / graph | 44.68 | 43.99 | -1.53% | -2.56% | -0.48% | +0.37% |
| module / layered | 51.05 | 48.87 | -4.26% | -5.44% | -3.04% | -8.44% |
| module / independent | 36.53 | 36.32 | -0.58% | -4.74% | +3.90% | +0.01% |
| module / ai_workload | 49.95 | 45.12 | -9.66% | -13.64% | -5.09% | -7.79% |
| module / web_server | 36.01 | 36.48 | +1.32% | +2.21% | +0.42% | +0.74% |

Five samples within one leg share a process and time window; they are not independent source-build experiments. There is still only one PGO binary per source. Serial controls also move, particularly layered and module finalizers. Lower focused means are not claimed as collector-specific benefits. The full module-cache throughput regression was not measured here.

## Evidence and replay

[Evidence](evidence/) preserves four complete raw JSONs, case logs, native/runtime preflights, host/parent provenance, exact fingerprints, the complete sixteen-row analysis and independent arithmetic checks. Raw JSON copies are byte-identical to `/tmp/parallel-gc-focused-ft-20261017-m22NM3`; gzip logs decompress byte-identically. Refusal logs from the real GIL/debug/wrong-affinity and missing-build checks are also preserved. No scratch originals were removed. `SHA256SUMS` covers all archived files; `ORIGINAL-SHA256SUMS` records decompressed logs.

Replay from the parent root:

```bash
focus=benchmarks/results/investigations/integration-validation-2026-10-16/focused-collections
python3 "$focus/analyse_focused_collections.py" \
    "$focus/evidence/ft-1-baseline.json" \
    "$focus/evidence/ft-2-candidate.json" \
    "$focus/evidence/ft-3-candidate.json" \
    "$focus/evidence/ft-4-baseline.json"
```

Input path names in a replay differ from the scratch-path names in the original analysis. Input content hashes and all result rows must match; do not require byte identity of the path metadata.

Follow-up: the [unchanged original full FT ABBA](../full-ft-repeat/RESULTS.md) completed later on 17 October. It also does not reproduce the broad module pattern, while seven frame cases increase in both halves. Keep these different invocation contexts and time windows separate. No atomic, barrier, traversal, queue, threshold, adaptation or failure-policy change follows from this diagnostic. Hosted CI and dependency-blocked full pyperformance remain outstanding.
