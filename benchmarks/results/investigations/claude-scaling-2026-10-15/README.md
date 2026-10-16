# Root-propagation scaling investigation, 15 October 2026

Raw data and scripts behind the
[scaling review](../../../../docs/reviews/2026-10-15-claude-scaling-review.md)
§7–8. Release builds (`--disable-gil --with-parallel-gc`, no PGO) of CPython
`c67363fa59`, baseline and with the experimental patch, ran on one 72-core
Neoverse-V2 host pinned to cores 0–31; each cell is the median of 9
collections in a fresh process. `scale.py` builds a live 1M-object heap
(graph, tree, lists or chain) held by a module global or frame local and
reports wall time and `gc.get_parallel_stats()['phase_timing']`. `cpu.py`
reports per-thread CPU across one collection. `run.sh` and `summarise.py`
drive and summarise the alternating baseline/patch matrix
(`results-v1.jsonl`, `results-v2.jsonl`; produced by an earlier `scale.py`
equivalent to the `global` holder). `holder.jsonl` compares holders.
`patch-v1.diff` and `patch-v2.diff` are the experimental propagation changes
(a demonstration, not a proposal; tested only with the five FT GC suites).
`run.sh` names the original `/tmp/gcscale/build-{base,patch}` directories;
adjust them to reproduce. No significance tests were run.
