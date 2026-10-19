# CI conclusions reported on 19 October 2026

Alex supplied the GitHub run listing showing all five new workflows successful after pushing parent `90f8a50` and CPython `b91445e0b9`.

| Workflows | Run IDs | Reported conclusion |
|---|---|---|
| macOS parallel GC | [39291350469](https://github.com/SonicField/parallel_gc/actions/runs/39291350469) | Success, 26m19s |
| Windows parallel GC | [39291345902](https://github.com/SonicField/parallel_gc/actions/runs/39291345902) | Success, 44m25s |
| Full CPython test suite | [39291341827](https://github.com/SonicField/parallel_gc/actions/runs/39291341827) | Success, 20m04s |
| Automatic Linux matrix and compiler checks | [39291300028](https://github.com/SonicField/parallel_gc/actions/runs/39291300028), [39291299964](https://github.com/SonicField/parallel_gc/actions/runs/39291299964) | Both success; individual workflow mapping awaits untruncated metadata |

This records workflow-level conclusions from the supplied listing. Job-specific source artifacts, `headSha`, test counts, skips and rerun history have not been inspected for these five runs. Do not treat the expected pushed source pair as independently verified checkout evidence. A direct read of run 39291300028 was attempted and denied by the environment's GitHub destination filter; no alternate route was used.

## Failures preserved and explained

- Linux `39248590193`: feature-off GIL/FT hook probes selected runtime-disabled mode because they tested API presence rather than collector availability. Parent `d448e16` repairs the probe; all four local configurations pass the complete harness selection. [Evidence](../benchmarks/results/investigations/ci-probe-feature-off-2026-10-19/README.md).
- Compiler checks `39248590252`: Clang rejected the uncalled GIL wrapper in all four GIL/FT debug/release configurations. CPython `b91445e0b9` removes only that wrapper; 32 strict local compilation checks and fresh debug runtime selections pass. [Evidence](../benchmarks/results/investigations/ci-unused-wrapper-2026-10-19/README.md).
- macOS `39249638402`: the same one GIL and two FT feature-off hook-probe failures. Both failed jobs built successfully and passed their focused collector selections before the harness failed. The later macOS workflow is reported successful. No macOS-specific collector repair was made.

Previous Linux full-suite `39249631377` and Windows `39249634897` were also reported successful. They remain distinct from the new source-pair runs above.

These conclusions resolve the reported red workflows after the two local repairs. They do not establish performance neutrality or replace detailed source/job verification. The complete rigorous pyperformance comparisons remain separate work.
