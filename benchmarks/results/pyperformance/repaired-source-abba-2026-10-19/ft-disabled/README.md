# FT disabled — complete rigorous source ABBA

Completed 20 October 2026 at 21:29:08 UTC; arithmetic and record checks completed at 21:39:34 UTC. Three of four campaigns are complete. FT enabled remains outstanding; this is not the final GIL/FT performance investigation.

## Compared inputs and scope

Frozen baseline `c67363fa59543ef5d572383af927f1cff88514a1` versus integrated `388fd5bb46fdda6b464db566faf818505c3d6eef`, in baseline/integrated/integrated/baseline order. Both ARM64 GCC 11.5 binaries are FT PGO+LTO builds with parallel-GC training. Parallel GC was disabled and the runtime GIL remained disabled in every saved run. This compares sources at a fixed runtime policy, not the cost of enabling parallel GC or compiling the feature. The binaries are not relabelled as the later CI-tested `b91445e0…` source.

Each leg retains all 100 original programs, 127 named results, 5,004 measured run records and 15,852 values. Rigorous settings and original workloads were unchanged. Worker records and values are not independent source replications. Both sources use the approved pure-Python SQLAlchemy implementation; these measurements are not pooled with historical native-SQLAlchemy results. [Full protocol and dependency boundaries](../../../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md).

## Observed execution-time changes

The geometric mean of 127 integrated/baseline time ratios is **+0.23%**. Positive time change means slower execution; null is 0% (ratio 1). It is not the corresponding throughput percentage. This summary does not establish neutrality or acceptance. Seventy-six point estimates are positive; 62 results have opposing half-directions.

Largest time increases:

| Named result | Time change | Half 1 | Half 2 |
|---|---:|---:|---:|
| `dask` | +4.55% | +2.27% | +6.80% |
| `k_core` | +2.51% | +6.55% | −1.39% |
| `html5lib` | +2.21% | +2.24% | +2.19% |
| `async_tree_eager_memoization` | +1.84% | +3.05% | +0.62% |
| `bench_mp_pool` | +1.69% | +2.02% | +1.36% |
| `shortest_path` | +1.67% | +6.86% | −3.24% |

`k_core` and `shortest_path` have opposing halves. `dask` and `html5lib` increase in both, but sign agreement alone does not establish causation. The upstream pooled comparison labels `dask`, `k_core` and `html5lib` significant, the other three not significant. Those labels are retained, not treated as independent source replications or a multiple-comparison-adjusted acceptance decision. The observations remain unresolved; no universal noise floor or collector-specific cause is asserted.

The largest time decreases are `async_tree_eager_cpu_io_mixed_tg` (−1.83%), `fannkuch` (−1.47%) and `pickle_list` (−1.29%). `sqlite_synth` increases +0.66% (+0.61%, +0.70%), labelled not significant by the pooled comparison. Positive results do not erase the individual increases. [All 127 rows](analysis.md), [leg means, variation and counts](analysis.json), and original warnings are retained. GC pauses were not measured by this comparison.

## Verification and preservation

The complete-campaign reader checked all four raw suites and all 400 original-program files against recorded digests, matching names/work and explicit per-run collector/GIL/hook attestation. A separate arithmetic check, without importing that reader, recomputed every ratio, both halves and the geometric mean from raw pyperf values. It also checked all seven recorded result/comparison digests and matching package/direct-URL inventories across the four legs. This is a worker cross-check, not an independent assessor audit.

Initial, before-campaign and after-campaign input fingerprints match byte for byte. They identify the frozen binaries, clean tracked source revisions, original tracked pyperformance inputs, runner and hooks. Continuous exclusive ownership of the benchmark cores and independent monitoring of every installed dependency byte are not claimed.

[evidence.tar.gz](evidence.tar.gz) preserves the four raw suites, all original-program files, execution records, pooled results/comparison, completed campaign record, original log with warnings, fingerprints, package freezes, launch revision, analysis outputs, reader/controller source and arithmetic-check source/output. The controller-log snapshot includes FT-enabled startup, not completion. Earlier checkpoint archives contain some of these same runs, not extra replications. Working files remain.

SHA-256 identities:

- Evidence archive: `ecc5ca23c0c18f4de678c600681e0c997d7a9ceff4d379b091558be41d7b1fb1`.
- Completed campaign record: `f1c0624f6852d2d1efa3df5199b7996aac7cd2d3aa7253fe639a65ba383ca0dc`.
- Analysis JSON: `0f91d9300c4abece1b3091ddffcc23605382b92249d5acd65fcd8254d806c6c4`.
- Analysis Markdown: `ec60bdb001e4bfcb117e6e237b9dafec015f7215814b2ce864bf4c7180458b41`.

Gzip integrity passes and extracted campaign/analysis identities match. These are local preservation checks, not an independently held backup claim. No full performance acceptance or VP-conformance verdict is claimed.
