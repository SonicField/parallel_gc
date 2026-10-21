# FT enabled — complete rigorous source ABBA

Completed 21 October 2026 at 05:50:38 UTC; arithmetic and record checks completed at 12:38:30 UTC. All four source-comparison campaigns, sixteen full suites, are complete.

## Compared inputs and scope

Frozen baseline `c67363fa59543ef5d572383af927f1cff88514a1` versus integrated `388fd5bb46fdda6b464db566faf818505c3d6eef`, in baseline/integrated/integrated/baseline order. Both ARM64 GCC 11.5 binaries are FT PGO+LTO builds with parallel-GC training. Parallel GC was enabled and the runtime GIL remained disabled in every saved run. This compares sources at a fixed runtime policy, not enabling/disabling one binary or compiling the feature. The binaries are not relabelled as the later CI-tested `b91445e0…` source.

Each leg retains all 100 original programs, 127 named results, 5,004 measured run records and 15,852 values. Original workloads and rigorous settings were unchanged. These records and values are not independent source replications. Both sources use the approved pure-Python SQLAlchemy implementation; measurements are not pooled with historical native-SQLAlchemy results. [Protocol and dependency boundaries](../../../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md).

## Observed execution-time changes

The geometric mean of 127 integrated/baseline time ratios is **−0.25%**. Positive time change means slower execution; null is 0% (ratio 1). It is not the corresponding throughput percentage. This summary does not establish neutrality or acceptance. Forty-one point estimates are positive; 47 results have opposing half-directions.

Largest time increases:

| Named result | Time change | Half 1 | Half 2 |
|---|---:|---:|---:|
| `dulwich_log` | +2.22% | +1.06% | +3.39% |
| `k_core` | +1.75% | +1.22% | +2.29% |
| `btree` | +1.52% | +2.77% | +0.27% |
| `stdlib_startup` | +1.20% | −0.05% | +2.47% |
| `chameleon` | +1.20% | +0.61% | +1.79% |
| `unpack_sequence` | +1.12% | +0.86% | +1.37% |

`stdlib_startup` has opposing halves. The upstream pooled comparison labels only `dulwich_log` significant among these six. Those labels are retained, not treated as independent source replications or a multiple-comparison-adjusted acceptance decision. Agreement in both halves alone does not establish causation. No universal noise floor or collector-specific cause is asserted.

Largest time decreases are `btree_gc_only` (−4.69%; halves −1.36%, −7.89%), `connected_components` (−2.38%; −2.69%, −2.06%) and `fannkuch` (−2.23%; −2.31%, −2.15%). `sqlite_synth` decreases −0.34% (−0.11%, −0.56%), labelled not significant by the pooled comparison. Positive results do not erase individual increases. [All 127 rows](analysis.md), [leg means, variation and counts](analysis.json), and original warnings are retained. GC pauses were not measured here.

## Verification and preservation

The complete-campaign reader checked all four raw suites and all 400 original-program files against recorded digests, matching names/work and explicit per-run collector/GIL/hook attestation. A separate arithmetic check, without importing that reader, recomputed every ratio, both halves and the geometric mean from raw pyperf values. It also checked all seven recorded result/comparison digests and matching package/direct-URL inventories across the four legs. This is a worker cross-check, not an independent assessor audit.

Initial, before-campaign and after-campaign input fingerprints match byte for byte. The controller exited successfully after checking the frozen binaries, tracked source inputs, runner and hooks. Continuous exclusive ownership of benchmark cores and independent monitoring of every installed dependency byte are not claimed.

At analysis time, the recorded build/driver root `/tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW` was no longer present. Its disappearance is unexplained; it was not removed in this analysis. The original raw measurements, fingerprints and campaign records remain. Analysis used a newly created, separate Python environment with pyperf 2.10.0, the same pyperf version as the original driver, and psutil 7.2.2. Its package inventory is archived. This does not recover the missing binaries or establish their present custody. No benchmark was rerun. The failed attempt to invoke the absent driver returned exit 127 before any analysis or measurement ran.

[evidence.tar.gz](evidence.tar.gz) preserves the four raw suites, all original-program files, execution records, pooled results/comparison, completed campaign, original log with warnings, fingerprints, FT package freezes, launch revision, complete controller-log snapshot, analysis outputs, reader/controller source and arithmetic-check source/output. Earlier checkpoint archives are not extra replications. Working results remain. These are local preservation checks, not an independently held backup claim.

SHA-256 identities:

- Evidence archive: `4dd0e6b815483211eac8ca7cf7b69f5da0ada482a3da6a98eaf44b21fa8dee26`.
- Completed campaign record: `9519d93a818dec8b98e02f28497d96684bd616ad8616417e5a7ff7c302b4da31`.
- Analysis JSON: `c880be28f11c3b209e100e5506281a8dfc94af2d54194b3efa3899941fbd2e68`.
- Analysis Markdown: `f53f056881e10e27693d4b47e51db392938a1f8e21735eb9dc3ceca137d51e4b`.

Gzip integrity passes. No full performance acceptance or VP-conformance verdict is claimed.
