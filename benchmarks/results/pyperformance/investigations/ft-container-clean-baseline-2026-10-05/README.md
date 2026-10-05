# Clean free-threaded container-traversal baseline

## Purpose

This campaign establishes the pre-optimization behavior of the free-threaded parallel collector on controlled exact-list, exact-tuple, and exact-dictionary graphs. It compares the same optimized binary with parallel GC disabled and enabled in disabled/enabled/enabled/disabled order. It does not compare a source candidate with the baseline.

## Target

- Source: clean detached CPython worktree at `01a89cbeb84b41931a3f30875022cc854d210fc8`
- Executable: `/tmp/parallel-gc-container-baseline-build/python`
- Executable SHA-256: `54a5fb0602314f62d5aa4a4dd0d1593ad15fbd681e1eba65d3272074a1f2fbee`
- Configuration: `--with-parallel-gc --disable-gil --enable-optimizations --with-lto`
- Architecture: AArch64
- Affinity: logical CPUs `0-31`
- Run style: pyperformance `--rigorous`

The `cpython_repository` field in `campaign.json` describes the active submodule checkout, which contains the protected experimental list patch. It is not the source of this binary. The authoritative target provenance is `target.source_repository`; it records the separate clean worktree and an empty status.

## Result

| Workload | Disabled 1 | Enabled 1 | Enabled 2 | Disabled 2 | AB result | BA result |
|----------|------------|-----------|-----------|------------|-----------|-----------|
| General-key dict | 3.26 ms | 3.56 ms | 3.56 ms | 3.30 ms | 1.09x slower | 1.08x slower |
| Split dict | 1.87 ms | 1.47 ms | 1.48 ms | 1.87 ms | 1.27x faster | 1.26x faster |
| Unicode-key dict | 1.55 ms | 1.13 ms | 1.14 ms | 1.55 ms | 1.37x faster | 1.36x faster |
| Exact list | 1.54 ms | 2.22 ms | 2.22 ms | 1.55 ms | 1.44x slower | 1.43x slower |
| Exact tuple | 1.65 ms | 2.30 ms | 2.27 ms | 1.64 ms | 1.39x slower | 1.38x slower |

### Observation

Both halves agree in direction and magnitude. The two disabled legs and the two enabled legs also agree closely. Pyperformance reported within-run stability warnings for most workloads, especially the enabled dictionary workloads, so the raw samples remain part of the record.

### Interpretation

The result supports investigating explicit list and tuple traversal: the generic parallel path adds a large reproducible cost on these controlled graphs. It also shows that dictionaries cannot be treated as one case. Parallel traversal improves split and combined-Unicode dictionaries in this workload but slows the general-key layout. This campaign does not establish that any proposed source change is beneficial.

## Verification

The SHA-256 values of all seven result and comparison files were recomputed after the run and match the values recorded in `campaign.json`.
