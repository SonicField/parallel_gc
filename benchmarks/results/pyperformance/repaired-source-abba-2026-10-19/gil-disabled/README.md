# GIL disabled — complete rigorous source ABBA

Completed 20 October 2026 at 05:15:34 UTC; arithmetic and record checks completed at 05:18:43 UTC. This is the first of four required campaigns, not the completed GIL/FT performance investigation.

## What was compared

Baseline source `c67363fa59543ef5d572383af927f1cff88514a1` versus integrated source `388fd5bb46fdda6b464db566faf818505c3d6eef`, in baseline/integrated/integrated/baseline order. Both frozen ARM64 GCC 11.5 binaries are PGO+LTO builds with parallel-GC training. Parallel GC was compiled in but disabled throughout every saved run. This is a source comparison under serial execution, not a within-binary enable/disable comparison or a feature-off compilation comparison. The binaries are not relabelled as the later CI-tested `b91445e0…` source.

Each leg contains all 100 original programs, 127 named results, 5,004 measured run records and 15,852 values. Upstream rigorous parameters and original workloads were unchanged. Measured run records are not independent source replications. SQLAlchemy uses the approved pure-Python implementation on both sources; historical native-SQLAlchemy timings are not pooled here. The complete [protocol](../../../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md) records dependencies, affinity and limitations.

## Observed execution-time changes

The geometric mean of the 127 integrated/baseline time ratios is **−0.21%**. Positive percentages below mean longer execution, not reduced throughput by the same percentage. The null time ratio is 1 (0% change). This descriptive summary does not establish neutrality or acceptance. Fifty point estimates are positive; 39 results have opposing ABBA half-directions.

The five largest time increases are:

| Named result | Time change | Half 1 | Half 2 |
|---|---:|---:|---:|
| `bench_mp_pool` | +6.98% | +12.80% | +1.03% |
| `shortest_path` | +3.15% | +1.25% | +5.07% |
| `dulwich_log` | +1.81% | +1.20% | +2.44% |
| `coverage` | +1.57% | +1.82% | +1.32% |
| `deepcopy_reduce` | +1.40% | +1.28% | +1.52% |

The upstream pooled comparison labels `bench_mp_pool` and `shortest_path` significant; it labels the other three not significant. Those labels are retained, not treated as causal attribution or a multiple-comparison-adjusted acceptance decision. In particular, the pool result differs substantially between its two halves. Agreement in sign alone does not prove a reproducible effect. No universal noise floor is assumed.

The largest time decreases are `btree_gc_only` (−5.12%), `async_tree_eager_io` (−3.75%) and `connected_components` (−3.00%). These do not erase the individual increases. [All 127 results](analysis.md) and [machine-readable leg means, variation and counts](analysis.json) are retained. GC pauses were not measured by this pyperformance comparison.

## Verification and preservation

The complete-campaign reader checked all four raw suites and all 400 original-program files against recorded digests, matching names/work and explicit per-run collector/GIL/hook attestation. A separate arithmetic check, without importing that reader, recomputed every time ratio, both halves and the geometric mean from raw pyperf values. It also checked all seven recorded result/comparison digests and matching package/direct-URL inventories across the four legs. This is a worker cross-check, not an independent assessor audit.

The controller's initial, before-campaign and after-campaign input fingerprints match byte for byte. The frozen binaries, clean tracked source revisions, original tracked pyperformance inputs, runner and hooks therefore match those recorded fingerprints. This is not an assertion of continuous exclusive ownership of the benchmark cores or proof that every installed dependency byte was independently monitored.

[evidence.tar.gz](evidence.tar.gz) preserves all four raw suites, original-program files, execution records, pooled suites/comparison, completed campaign record, original log with stability warnings, fingerprints, package freezes, launch revision, analysis outputs, reader/controller source and cross-check source/output. Its controller-log snapshot includes the subsequent GIL-enabled start; it is not evidence that that campaign completed. Earlier checkpoint archives duplicate some of these same runs and are not additional replications. All working files remain.

SHA-256 identities:

- Evidence archive: `1bd196fe349b5cab90da0ed881b50d86a81f989680da2eb63913cc4bfc50e3c1`.
- Completed campaign record: `965f04ac1bd14b95994ffd98b5437ca8220f52601caceb6e9873932c0fc3b225`.
- Analysis JSON: `d6635430e00e2f5fe232af67c495d92a9aee499ef2119fe0db4b43208b3d2ecd`.
- Analysis Markdown: `7a0ac242b105e9cdce4213bfe717f0574219fab784a38f71006858555b0911ec`.

Gzip integrity passes and extracted campaign/analysis identities match. These are local preservation checks, not an independently held backup claim. Remaining campaigns are GIL enabled, FT disabled and FT enabled; no full performance or VP-conformance verdict is claimed here.
