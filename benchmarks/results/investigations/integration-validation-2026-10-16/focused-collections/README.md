# Focused FT controlled-collection reproduction

## Question and falsifier

The completed full project ABBA finds all eight FT module-rooted controlled collections slower in the current binary, in both halves (+18.72% to +34.81%). Frame-layered collection is also slower in both halves. Can the same directional pattern be reproduced when the existing controlled-collection functions run without the preceding sustained workloads?

The source-associated hypothesis predicts positive current/baseline duration changes in both halves for those cases, without comparable serial-control movement. Opposite signs or failure to reproduce that pattern weaken this attribution. They do not erase the original measurements or prove neutrality. Report every case, sample, both halves, counts and serial controls. The null ratio is one; no new significance or acceptance cutoff is adopted.

## Protocol

1. Use the existing baseline/current FT PGO+LTO binaries and clean source pair, not rebuilt copies: `c67363fa59543ef5d572383af927f1cff88514a1` and `388fd5bb46fdda6b464db566faf818505c3d6eef`.
2. Require the original binary hashes, native/runtime preflights, unchanged benchmark checksum and no other active measurements. All local full-suite controllers have completed; pyperformance is stopped pending dependency agreement.
3. In each fresh process, call the existing `run_collection_benchmark()` for all eight frame-rooted shapes followed by all eight module-rooted shapes, in the full suite's order. Do not copy or alter its traversal, construction, rooting, survivor selection, timing, alternating serial/parallel pairs, warmups or cleanup.
4. Preserve the full controlled-case parameters: five measured pairs, three warmups per arm, nominal 500,000-member heaps, four persistent creation threads, seed 42 and 80% surviving clusters. Worker choice remains adaptive. The legacy `parallel_workers` function parameter receives the same reported ceiling as the full suite; it does not pin workers.
5. Execute baseline–current–current–baseline sequentially with CPU affinity 0–31 and NUMA CPU/memory node 0. Check binary and harness hashes after every leg. Preserve complete logs and JSON, including any failure.
6. Validate complete sixteen-case coverage, five finite samples per arm, matching generated-member sequences within arms and across legs, intended compiled/runtime mode, source identity, placement and parameters before comparing means. Give legs equal weight; report both halves and serial controls. Do not pool individual collections as independent build experiments.

## Scope differences and limits

This is a focused diagnostic, not another full project suite or a replacement for its results. It omits the mixed workload and sustained chain/graph/finalizer phases that precede module collections in the original invocation. Consequently heap/allocator state and adaptation exposure differ. It imports the unchanged benchmark as a normal module registered in `sys.modules`, rather than executing it as `__main__`; that process context is another limitation. No driver frame holds generated clusters or survivor references.

The existing full suite is already complete and remains preserved. The focused result cannot validate module-cache throughput, explain worker-count effects, prove original performance neutrality, or authorize collector changes. If the negative pattern repeats, independently rebuilt PGO binaries and generated-code/perf inspection remain the next questions. If it does not, investigate process context rather than declaring the original result noise.

## Implementation verification

Write wrapper/validation tests first, then implement the external driver. Check that it calls the real benchmark entry point with every unchanged parameter and case, refuses incomplete/invalid result data, and keeps the benchmark registered as a module. Those machinery tests do not establish performance. Real native/runtime preflights and complete focused legs provide the integration evidence. The benchmark implementation and all CPython source/tests remain unchanged.

## Progress

Protocol recorded before execution. The driver and analyser tests were written before their implementations; initial runs fail because each module is absent. A later planted disabled/inactive end-of-run pool initially passes analysis incorrectly; two subcases fail before the corresponding validation is added. All nineteen machinery tests now pass, along with all twenty-four existing full-analysis tests. The analyser reuses the full-analysis arithmetic rather than recomputing source effects differently.

Real optimized GIL, debug FT and wrong-affinity optimized FT invocations each refuse before any case or JSON result. The launcher refuses a missing build root before creating output; shell syntax passes. Refusal logs remain in `/tmp/parallel-gc-focused-refusals-20261017-YtNbJv`. These checks do not establish collection performance. No focused timing result is claimed yet. Current hosted CI and dependency-repair approval remain separate outstanding requirements.

From the parent root, after those checks:

```bash
focused_out=$(mktemp -d /tmp/parallel-gc-focused-ft-20261017-XXXXXX)
bash benchmarks/results/investigations/integration-validation-2026-10-16/focused-collections/run_focused_abba.sh \
    /tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW \
    "$focused_out" \
    /data/users/alexturner/parallel_gc
```

The launcher writes every raw leg, provenance, original fingerprints and the complete checked sixteen-row analysis to that owned directory. A failed/incomplete campaign does not produce an accepted analysis. Preserve it separately from the full-suite campaigns.

The four legs now completed with exit 0. [Results and limitations](RESULTS.md) preserve all sixteen cases. The broad full-invocation slowdown was not reproduced in this isolated context; the original negative data remain valid observations, not dismissed as noise. No collector or benchmark implementation changed. Repeat the original full invocation before assigning a cause.
