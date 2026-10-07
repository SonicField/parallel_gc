# GIL lazy-pool `sqlite_synth` ABBA

## Result

Arming GIL parallel GC without starting its helper pool did not produce a
statistically significant `sqlite_synth` regression.

| Run | Mode | Mean | Values |
|---|---|---:|---:|
| 1 | disabled | 1.422020 us | 120 |
| 2 | armed | 1.431112 us | 120 |
| 3 | armed | 1.427731 us | 120 |
| 4 | disabled | 1.420612 us | 120 |
| combined | disabled | 1.421316 us | 240 |
| combined | armed | 1.429422 us | 240 |

The combined difference is 0.57 percent. Pyperf reported `1.01x slower, not
significant`. The earlier eager-start campaign measured a 38.1 percent GIL
regression in this benchmark.

## Hypothesis

The earlier regression occurred because eager pool creation triggered glibc's
irreversible first-thread transition in a workload that performed no cyclic
collection. If `gc.enable_parallel()` only arms the GIL collector, this
workload should retain one OS thread and the former regression should disappear.

A separate run of the unmodified `bench_sqlite()` function at 131,072 loops
observed one `/proc/self/task` entry before and after the workload.
`gc.get_parallel_config()` reported `enabled == true` and
`pool_active == false` at both observations.

## Method

The campaign used the project runner's rigorous
disabled/enabled/enabled/disabled order:

```text
<driver-python> benchmarks/run_pyperformance.py abba \
    --python build-pyperformance-gil/python \
    --benchmarks sqlite_synth \
    --run-style rigorous \
    --output-dir \
    benchmarks/results/pyperformance/investigations/gil-lazy-pool-sqlite-abba-2026-10-07
```

The target was a GIL PGO+LTO build with parallel-GC-specific PGO training. Its
SHA-256 was
`65b174b0d9bdebade18a10eb905c7cfab7421be7256f2d48ab0272f0db0510b7`.
The source content was committed immediately afterward as CPython commit
`7ec0874a7d219108401b9dd3ff966db80958ecac`; the generated campaign metadata
therefore records the preceding commit plus a dirty worktree.

The machine's temporary development-prefix headers had disappeared before the
final rebuild. The `_sqlite3` and `zlib` extension binaries were restored from
the previous ABI-identical CPython 3.16 build. Both ABBA modes used the same
executable and extensions. This does not compare two CPython binaries; it
compares runtime policy in one binary.

## Files

- `01-disabled.json`, `02-enabled.json`, `03-enabled.json`, and
  `04-disabled.json` are the raw rigorous runs.
- `disabled-combined.json` and `enabled-combined.json` contain the paired
  conditions.
- `comparison.txt` is the standard pyperf comparison.
- `campaign.json` records commands, repository states, executable identity,
  configuration, and hashes.

This experiment tests armed-but-unused overhead. It does not measure first-use
pool startup or steady-state large-collection performance.
