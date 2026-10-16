# Quick ABBA sanity run: module-rooted suite (bench `306644b`)

- `--quick --include-synthetic` (2 runs × 10 s per mode); FT PGO builds
  `pgo-B2-ft` and `pgo-Ccand-ft` (unchanged from `suite-abba-1`).
  2026-10-15 10:37–11:05 PDT. Cores 32–71 were 2.4% busy on average
  (maximum 4.5%).
- **Purpose: check the machinery. These results are not evidence.**

## Machinery check: pass

- All 4 runs exited 0.
- Every new key was present (`mixed_workload_module_cache`,
  `synthetic_by_heap_module`, `collection_results_module`,
  `configuration.module_cache_size` = 500,000).
- `suite_analyse2.py` applied the HB/HN rules to all 40 rows.

## Noise level

Serial-control changes reach ±25% on means and ±49% on maxima, so quick
mode is far too noisy for HB/HN decisions. Rule outcomes are listed below
only as pointers.

- **HB passes (2):** synthetic graph (module) throughput +7.5%; module
  chain collection −11.0%.
- **HN failures (4):**
  - synthetic `ai_workload` (frame), latency mean +15.0% and maximum +27.0%;
  - `independent` collection +4.5%;
  - mixed+module-cache latency maximum +14.5%.
- **Recurring signal:** synthetic `ai_workload` flagged again (in
  `suite-abba-1`: throughput −4.0%). Watch it in the full campaign.
- Module-rooted collection shapes: 6 of 8 faster on the candidate, with
  both halves negative (chain, tree, wide_tree, graph, ai_workload,
  web_server, by 8–12%). Unproven at this noise level.
- Mixed+module cache mean latency: 0.0% change (halves +5.4% and −5.0%).
  No benefit visible here.
