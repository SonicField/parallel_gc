# GIL enabled — complete rigorous source ABBA

Completed 20 October 2026 at 12:55:46 UTC; arithmetic and record checks completed at 13:01:56 UTC. Both GIL campaigns are complete. The two FT campaigns remain outstanding, so this is not the final GIL/FT performance investigation.

## Compared inputs and scope

Frozen baseline `c67363fa59543ef5d572383af927f1cff88514a1` versus integrated `388fd5bb46fdda6b464db566faf818505c3d6eef`, in baseline/integrated/integrated/baseline order. Both ARM64 GCC 11.5 binaries are PGO+LTO builds with parallel-GC training. Parallel GC was enabled in every saved run. This compares sources at a fixed runtime policy; it does not measure the effect of enabling parallel GC within one unchanged binary. The binaries are not relabelled as the later CI-tested `b91445e0…` source.

Each leg retains all 100 original programs, 127 named results, 5,004 measured run records and 15,852 values. Rigorous settings, original workloads and measurement inputs were unchanged. Worker records and values are not independent source replications. Both sources use the approved pure-Python SQLAlchemy implementation; do not pool these measurements with historical native-SQLAlchemy results. [Full protocol and dependency boundaries](../../../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md).

## Observed execution-time changes

The geometric mean of 127 integrated/baseline time ratios is **+0.33%**. Positive time change means slower execution; null is 0% (ratio 1). It is not the corresponding throughput percentage. This summary does not establish neutrality or acceptance. Sixty-two point estimates are positive; 40 results have opposing half-directions.

Largest time increases:

| Named result | Time change | Half 1 | Half 2 |
|---|---:|---:|---:|
| `subparsers` | +15.29% | +0.003% | +30.75% |
| `dask` | +13.86% | −0.23% | +28.04% |
| `btree_gc_only` | +12.70% | +17.25% | +8.16% |
| `connected_components` | +6.48% | +8.49% | +4.46% |
| `shortest_path` | +5.32% | +11.41% | −0.73% |
| `stdlib_startup` | +2.37% | +0.73% | +3.99% |

`subparsers` and `dask` have sharply unequal halves; `shortest_path` has opposing directions. Do not present these as stable causal effects. `btree_gc_only`, `connected_components` and `stdlib_startup` increase in both halves, but agreement alone does not establish causation. The upstream pooled comparison labels all six except `subparsers` significant. Those labels are retained, not treated as independent source replications or a multiple-comparison-adjusted acceptance decision. The observed increases remain unresolved and need focused repetition before attribution or repair.

The largest point-estimate decrease, `async_tree_cpu_io_mixed_tg` (−5.21%), also has opposing halves (+0.80%, −10.59%). `k_core` decreases −3.35% in both halves. `sqlite_synth` increases +0.34% (+0.47%, +0.21%), labelled not significant by the pooled comparison. No universal noise floor is assumed. Positive results do not erase individual increases. [All 127 rows](analysis.md), [leg means, variation and counts](analysis.json), and the original warnings are retained. GC pauses were not measured by this comparison.

The [GIL-disabled source control](../gil-disabled/README.md) has geometric-mean time change −0.21%, with its own individual increases and uncertainty. The campaigns ran sequentially; subtracting their summaries is not a controlled estimate of activation cost.

## Verification and preservation

The complete-campaign reader checked all four raw suites and all 400 original-program files against recorded digests, matching names/work and explicit per-run collector/GIL/hook attestation. A separate arithmetic check, without importing that reader, recomputed every ratio, both halves and the geometric mean from raw pyperf values. It also checked all seven recorded result/comparison digests and matching package/direct-URL inventories across the four legs. This is a worker cross-check, not an independent assessor audit.

Initial, before-campaign and after-campaign input fingerprints match byte for byte. They identify the frozen binaries, clean tracked source revisions, original tracked pyperformance inputs, runner and hooks. Continuous exclusive ownership of the benchmark cores and independent monitoring of every installed dependency byte are not claimed.

[evidence.tar.gz](evidence.tar.gz) preserves the four raw suites, all original-program files, execution records, pooled results/comparison, completed campaign record, original log with warnings, fingerprints, package freezes, launch revision, analysis outputs, reader/controller source and arithmetic-check source/output. A failed summary-display command and its corrected output are separately documented; that failure changed no measurements. The controller-log snapshot includes FT-disabled startup, not FT completion. Earlier checkpoint archives contain some of these same runs, not extra replications. Working files remain.

SHA-256 identities:

- Evidence archive: `4d2c43049ef0523b7696f8139806a93c54080e147f5d245d65bde3ac1ae80d6e`.
- Completed campaign record: `3018aa2f2810b72e7960f1922f4fe721345db7466f20b6bf43f91c8a9cafed48`.
- Analysis JSON: `708ee60c2827cfaa301038f1d8218664a79b0e589f4396a21e9dd46aab976564`.
- Analysis Markdown: `4f3f8015ace0f735d807353cd854953c9a4a6d3122bac98aa213e738f7a868ab`.

Gzip integrity passes and extracted campaign/analysis identities match. These are local preservation checks, not an independently held backup claim. No full performance acceptance or VP-conformance verdict is claimed.
