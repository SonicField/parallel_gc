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
sustained `ai_workload` latency regression was flagged in three campaigns.
The data is kept as evidence for the open root-placement issues
(`docs/OPEN_ISSUES.md` §2).

| Directory | Contents |
|---|---|
| `suite-abba-1/` | `--full --include-synthetic`, benchmark `724b74b`. **Collection-shape results are invalid**: before benchmark commit `6c8bf14`, creation-pool threads kept every cluster reachable. Mixed and sustained results are valid. |
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
