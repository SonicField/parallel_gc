# Project-suite ABBA: baseline B2 vs candidate (C1+C3+C2+deque fix), FT PGO+LTO

- Date: 2026-10-15, 05:13–08:23 PDT. Host: 72-core Neoverse-V2. Cores 0–31
  pinned for benchmarks; cores 32–71 were 2.4% busy on average (maximum
  7.5%, never above 20%).
- Builds: `pgo-B2-ft` (cpython `ac53a434a0`, python sha256 `0780aa2f…`) and
  `pgo-Ccand-ft` (`5bbc768d77`, sha256 `c9933aaf…`). Both
  `--disable-gil --with-parallel-gc --enable-optimizations --with-lto`;
  the parallel-GC PGO task ran.
- Command: `benchmarks/gc_perf_benchmark.py --full --include-synthetic --json`
  from parent `main` `724b74b`. Order: B, C, C, B. About 47 minutes per run.
- Analysis: `suite_analyse.py`, output in `analysis.txt`. Two-sided permutation
  test on means of pooled per-run (or per-sample) values.

## Statistical caveat

The serial-mode rows are a control: the serial code is identical in both
builds. Several control rows still show p < 0.01 or close to it:

- mixed serial throughput +1.1% (p = 0.002);
- mixed serial latency −2.4% (p < 0.001);
- `web_server` serial +2.5% (p = 0.002);
- `graph` and `layered` serial −4% to −5% (p ≈ 0.02–0.05).

Pooled samples are not independent (within-run correlation, and drift
between runs), so the test is **anti-conservative**. Treat a
candidate-vs-baseline difference as real only when it clearly exceeds the
corresponding control difference.

## Results (candidate vs baseline)

| Workload | Parallel-mode change | Serial control | Reading |
|---|---|---|---|
| Mixed throughput | +2.1% | +1.1% | within about 1% of the control; **no material change** |
| Mixed latency mean | −3.5% | −2.4% | **no material change** |
| Mixed latency maximum | +50% (p = 0.25) | +3% | not significant; maxima are noisy (two runs per build) |
| Synthetic `ai_workload` | throughput −4.0% (p = 0.25), latency +1.5% | ≈ 0 | not significant |
| Synthetic `chain` | throughput +2.1%, latency +3.5% (ns) | — | not significant |
| Synthetic `graph` | throughput +2.2%, latency −4.5% (ns) | — | not significant |
| Collection `graph` | −7.7% (p = 0.001) | −4.3% | net about −3% |
| Collection `layered` | −11.5% (p = 0.002) | −5.2% | net about −6% |
| Other collection shapes | within ±1.2% | — | no change |

Within-build parallel vs serial:

| | Mixed throughput | Mixed latency | Collection geomean |
|---|---|---|---|
| Baseline | +24.0% / +25.4% | −26.7% / −27.3% | 1.24× / 1.26× |
| Candidate | +25.9% / +25.9% | −27.7% / −28.0% | 1.28× / 1.28× |

## Verdict

- On the project's own suite, the candidate is **neutral**: no regression
  beyond the noise floor that the control establishes, and no material
  improvement.
- The 7–10× micro-benchmark gains **do not appear** here. This is
  consistent with the findings' root-placement analysis (§7.4): the
  project suite holds live data in frame locals (`keep_refs`) and uses
  clustered, shallow heaps, which is the case where baseline PROPAGATE
  already parallelises.
- **Not demonstrated:** any benefit for realistic workloads. The candidate's
  benefit is so far confined to heap shapes and rootings that the project
  suite does not exercise.
