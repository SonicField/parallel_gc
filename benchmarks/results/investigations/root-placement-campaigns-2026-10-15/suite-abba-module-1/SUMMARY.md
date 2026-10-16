# Full ABBA campaign with module-rooted workloads (bench `306644b`)

- `--full --include-synthetic` (5 runs × 60 s per mode); FT PGO+LTO
  `pgo-B2-ft` (cpython `ac53a434a0`) and `pgo-Ccand-ft` (`5bbc768d77`).
- 2026-10-15 11:30–17:50 PDT, about 95 minutes per run, order B C C B, cores
  0–31. Cores 32–71 were 2.2% busy on average (maximum 5.5%).
- Rules pre-registered in `.vp/plans/bench-rooting-plan.md`; analysis
  `suite_analyse2.py` → `analysis.txt`.

## Benefit (HB): 10 passes, all module-rooted

| Workload | Candidate vs baseline | ABBA halves | Serial control |
|---|---|---|---|
| Mixed + module cache, throughput | **+6.4%** | +6.6%, +6.2% | −0.9% |
| Mixed + module cache, mean latency | **−13.4%** | −14.3%, −12.6% | 0.0% |
| Module-rooted collection shapes, all 8 | **−12% to −26%** | both halves negative for every shape | −7.1% to +2.3% |

Within-build parallel vs serial, mixed + module cache:

| | Throughput | Latency |
|---|---|---|
| Baseline | +21% | −29% |
| Candidate | +30% | −39% |

## No harm (HN): 3 failures

| Workload | Candidate vs baseline | ABBA halves | Control | Limit | Reading |
|---|---|---|---|---|---|
| Synthetic `ai_workload` (frame), mean latency | **+11.1%** | +5.2%, +16.6% | +0.6% | 3% | consistent direction |
| Synthetic `ai_workload` (frame), maximum latency | +18.5% | +4.9%, +31.8% | +6.6% | 13.2% | consistent direction |
| Synthetic chain (module), mean latency | +6.1% | +17.4%, −3.9% | +3.0% | 6.0% | halves disagree: noise-like, but a fail by rule |

**`ai_workload` has now been flagged in three independent campaigns:**

- `suite-abba-1`: throughput −4.0%;
- quick run: latency +15%;
- this campaign: latency +11.1% (throughput −1.8%, not a fail).

**Treat it as a real candidate regression**, not noise. Under the Engineer's
"no worse" criterion the candidate does not yet pass.

## Other existing (frame-rooted) workloads

| Workload | Change | Control |
|---|---|---|
| Mixed, throughput | +2.1% | −0.1% |
| Mixed, mean latency | −3.9% | −0.4% |
| Synthetic graph | about 0 | — |
| Synthetic chain, throughput | +19.7% | +3.7% |
| Synthetic chain, mean latency | −14.1% | −1.3% |
| Collection shapes | −1% to −9% | mixed |

No other HN failures.
