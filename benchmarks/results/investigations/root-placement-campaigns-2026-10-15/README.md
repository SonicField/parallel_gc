# Root-placement campaigns, 15–16 October 2026

These are project-suite ABBA campaigns comparing the FT collector against
experimental changes to known-root propagation. Those changes were:

- helpers wait until all propagation work is finished;
- busy workers publish part of their private buffer when another worker is
  idle;
- large lists are split into stealable index ranges;
- the work-queue index is published with release stores.

All four were **dropped** on 16 October 2026: they showed a benefit only on
module-rooted workloads; the list splitting is container-specific; and the
final full campaign recorded a sustained `ai_workload` mean-latency increase.
The data is kept as evidence for the open root-placement issues
(`docs/OPEN_ISSUES.md` §2).

## Current interpretation, 21 October 2026

The three campaign summaries are preserved historical interpretations. They
are not three independent rigorous latency replications: all use one binary
pair, and the quick run uses a different diagnostic-only protocol.

| Campaign | Recorded AI result | Interpretation limit |
|---|---|---|
| [First full](suite-abba-1/SUMMARY.md) | Throughput −4.0%, mean latency +1.5% | The original summary labels the signal not significant; it is not the later +11.1% latency result. |
| [Quick](suite-quick-module-1/SUMMARY.md) | Mean latency +15% | Machinery check with large control variation, not additional performance evidence. |
| [Final full module-rooted](suite-abba-module-1/SUMMARY.md) | Mean latency +11.1%, halves +5.2%/+16.6% | A same-pair full result, not independent build replication. |

The conservative candidate-rejection decision remains recorded. These results
do not establish that added coordination always harms performance.

| Directory | Contents |
|---|---|
| `suite-abba-1/` | `--full --include-synthetic`, benchmark `724b74b`. Collection-shape results did not establish the intended garbage fraction: creation helpers could retain their last batch, depending on scheduling. The actual historical retained fraction is unknown. Mixed and sustained workloads did not use that pool. [Ownership evidence](../creation-pool-retention-2026-10-16.md). |
| `suite-quick-module-1/` | `--quick` machinery check of the module-rooted variants (benchmark `306644b`). Not evidence. |
| `suite-abba-module-1/` | `--full --include-synthetic` with the module-rooted variants (benchmark `306644b`). Main evidence. |
| `hv-baseline.jsonl`, `hv-replicate.txt` | Baseline validity check: module-rooted collection heaps reproduce the propagation weakness; frame-rooted twins do not. |
| `tools/` | Driver (`suite_abba.sh`), CPU monitor, analysis scripts (`suite_analyse2.py` applies the pre-registered rules) and the validity check. |

Builds:

- baseline: FT PGO+LTO from cpython `ac53a434a0` (python sha256 `0780aa2f…`);
- candidate: `5bbc768d77` on local branch `investigation/C-candidate`
  (sha256 `c9933aaf…`).

Both were built with `--disable-gil --with-parallel-gc --enable-optimizations
--with-lto` and ran on cores 0–31 of the 72-core Neoverse-V2 host. Each
`SUMMARY.md` gives the per-workload results, including every regression.
