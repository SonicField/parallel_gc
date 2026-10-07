# Parallel-aware PGO and runtime ABBA results

This report records the design and verification of the parallel-GC PGO workload, two experiments that test its effect on ordinary runtime-disabled performance, and two experiments that measure the effect of enabling parallel GC. It preserves negative results and experimental limitations as well as improvements.

## Questions

The work answered two separate questions.

1. Does adding a parallel-GC workload to CPython's PGO training change ordinary interpreter performance when parallel GC is compiled in but disabled at runtime?
2. After that PGO training, what changes when parallel GC is enabled in GIL and free-threaded builds?

The first question used distinct control and candidate binaries. The second used one candidate binary per build and changed only runtime collector activation.

## Source and machine

The experiments ran on `devbig340.ncg1.facebook.com`, a 72-logical-CPU AArch64 machine, under Linux `6.16.1-0_fbk3_0_gd6c130b80483`. Every measured worker was restricted to CPUs `0-31`. GCC was `11.5.0 20240719 (Red Hat 11.5.0-15)`.

The PGO implementation is CPython commit `d396f837b9ab1f23573b404f70848584dff83bc7` (`Train parallel GC in optimized builds`). The binaries were built immediately before that commit from the recorded dirty tree at `3459fbefd8a11d39b5c46774e05ba28352fef943`. The substantive PGO source and workload became `d396f837b9`; the only post-build changes were removal of blank lines at the ends of generated `configure` and `pyconfig.h.in` files. Those whitespace changes cannot affect the binaries.

The pyperformance runner and activation hook came from parent revision `d05ec88b193bb9ed468198858f7caac2344f252d`. The pinned pyperformance revision was `ccc0aeb7ad46d65b6dcd4160e0fdda4d885852dd`. Campaign files record the complete repository states, including unrelated untracked results and generated package metadata.

## Builds

All four binaries used `--with-parallel-gc --enable-optimizations --with-lto`. Free-threaded builds also used `--disable-gil`. The dependency prefix, compiler flags, interpreter version, and executable hash are retained in each `campaign.json`.

| Build | PGO training | SHA-256 |
|---|---|---|
| GIL control | Standard CPython task only | `bc7ed956fa5a1c0baebcd58acdb9f91242d1358caee8767f27c91ae8f4d8b3b7` |
| GIL candidate | Standard task plus parallel-GC task | `58ab3f1160542d3ecf804202d3d586234759a33424659364525e66b0dedaa47c` |
| FT control | Standard CPython task only | `7e732087dab5f45b85167c1067537a27809afe40cc3d0df0d741e16f7a6f3e2b` |
| FT candidate | Standard task plus parallel-GC task | `ff5b3b4570fec2e6b7c0f1b202f41a933b3163718ac24d7052e247612c5715f8` |

Control builds set `PARALLEL_GC_PROFILE_TASK=` at the make invocation. Candidate builds used the configured default. Both therefore compiled identical source with identical configure arguments; only the PGO training samples differed.

CPython's standard PGO task completed 43 test files and 10,470 tests in every build. Candidate builds then ran `Tools/build/parallel_gc_profile.py` before profile merging and final compilation.

## Parallel-GC PGO workload

The supplementary workload explicitly enables parallel GC, keeps a live graph of 9,000 `ProfileNode` instances reachable through the measured collections, and constructs one unreachable cycle containing 2,250 nodes. It performs an initial live collection and one garbage collection. Eight examples of each exact container layout exercise list, tuple, combined-Unicode dictionary, general-key dictionary, and split dictionary traversal without allowing container construction to dominate the training distribution.

The task rejects a run that does not enter the parallel collector. GIL builds verify an increase in `collections_succeeded`; free-threaded builds verify recorded parallel phase time. Feature-off builds skip the supplementary work cleanly.

Profile inspection confirmed that the task changed collector coverage:

| Build | Parallel collector functions with nonzero profile counts | Recorded arc-count sum |
|---|---:|---:|
| GIL control | 2 | 8,176 |
| GIL candidate | 33 | 1,474,205 |
| FT control | 1 | 109 |
| FT candidate | 52 | 2,012,887 |

### Workload calibration

Earlier workload shapes over-weighted exact-container construction and changed runtime-disabled focused measurements. Those shapes were rejected. The final `9,000 nodes / 1 garbage collection / 8 layout samples` shape produced these focused results:

| Build and runtime mode | Focused observation |
|---|---|
| GIL, disabled | Split-dictionary traversal was 1.01 times faster; not significant. |
| GIL, enabled | Split-dictionary traversal was 1.15 times faster; significant. |
| FT, disabled | General-dictionary traversal was 1.02 times slower and split-dictionary traversal was 1.01 times faster; neither was significant. |
| FT, enabled | General dictionaries were 1.07 times faster, split dictionaries 1.04 times faster, Unicode dictionaries 1.34 times faster, lists 1.52 times faster, and tuples 1.02 times faster; all were significant. |

Raw focused campaigns:

- [GIL disabled control](investigations/pgo-gil-split-disabled-abba-v3-2026-10-05/)
- [GIL enabled result](investigations/pgo-gil-split-enabled-abba-v4-2026-10-05/)
- [FT disabled control](investigations/pgo-ft-dicts-disabled-abba-v4-2026-10-05/)
- [FT enabled result](investigations/pgo-ft-containers-enabled-abba-v2-2026-10-05/)

These focused measurements established that the final training workload reaches the intended collector paths without a statistically significant change in the selected disabled controls. They did not establish whole-interpreter neutrality; the full experiments below tested that separately.

## Experimental method

All complete experiments used pyperformance `rigorous` mode, CPU affinity `0-31`, and a 3,600-second per-benchmark timeout. The campaign included every available benchmark except `dask`, `fastapi`, `genshi`, and `xdsl`; those four were unavailable or unsuitable in the local environment. The resulting 96 benchmark programs reported 122 named measurements.

The runner retained all four raw suites, combined the same-condition suites, generated the standard pyperformance comparison, recorded commands and state attestations, and stored SHA-256 hashes in `campaign.json`.

On 2026-10-07, every result hash recorded by the eight campaigns cited in this report was recomputed from the retained file and matched its `campaign.json` value.

The ABBA order cancels first-order linear drift. It does not remove nonlinear machine interference, correct for 122 simultaneous significance tests, or turn pyperformance into a cyclic-GC pause benchmark.

## Experiment 1: effect of supplementary PGO training

### Null hypothesis

For each named measurement, the candidate/control time ratio is 1.0 when parallel GC is disabled. The experiment estimates the ratio and applies pyperformance's reported significance test. Failure to reject this null is not proof of exact equality.

The order was control, candidate, candidate, control. Parallel GC was disabled and preflight reported zero workers in all eight legs across the two builds.

| Build | Geometric mean candidate/control time | Significant faster | Significant slower | Not significant |
|---|---:|---:|---:|---:|
| GIL | 0.993831, or 0.62% faster | 7 | 3 | 112 |
| FT | 0.998143, or 0.19% faster | 3 | 2 | 117 |

The GIL significant slowdowns were `async_tree_eager_memoization_tg` at 2%, `k_core` at 3%, and `sqlalchemy_imperative` at 3%. The FT significant slowdowns were `nbody` at 3% and `shortest_path` at 2%. No slowdown reproduced in both builds. The experiments also reported significant improvements, including large changes in a few process- or startup-sensitive benchmarks.

With 122 simultaneous uncorrected tests, isolated significant results are expected even when the family of null hypotheses is true. The mixed directions and lack of cross-build reproduction do not support a common PGO regression. They also do not establish that each benchmark is unchanged. A claimed benchmark-specific PGO effect requires a focused repetition.

Raw complete experiments:

- [GIL PGO regression experiment](investigations/pgo-gil-full-disabled-abba-2026-10-05/)
- [FT PGO regression experiment](investigations/pgo-ft-full-disabled-abba-2026-10-06/)

## Experiment 2: effect of runtime activation

The order was disabled, enabled, enabled, disabled. Each build used the candidate binary on both sides, eliminating compiler, link, and PGO differences within that comparison. Every disabled leg reported `enabled: false` and `num_workers: 0`. Every enabled leg reported `enabled: true`, a pool ceiling of 16, and an adaptive starting count of four.

| Build | Geometric mean enabled/disabled time | Significant faster | Significant slower | Not significant |
|---|---:|---:|---:|---:|
| GIL | 1.000720, or 0.072% slower | 6 | 12 | 104 |
| FT | 0.966212, or 3.38% faster | 28 | 3 | 91 |

### GIL observations

The aggregate GIL result was close to one, but that aggregate conceals large benchmark-specific effects.

| Measurement | Enabled/disabled result |
|---|---:|
| `btree_gc_only` | 1.96 times faster |
| `gc_traversal` | 1.28 times faster |
| `btree` | 1.03 times faster |
| `create_gc_cycles` | 20.1% slower |
| `sqlite_synth` | 38.1% slower |
| `sqlalchemy_declarative` | 3.2% slower |

The remaining significant changes are retained in the comparison file and include both 2-4% improvements and regressions.

Raw experiment: [GIL runtime ABBA](baselines/pgo-gil-full-abba-2026-10-06/)

### Free-threaded observations

The free-threaded aggregate decreased measured time by 3.38%. Twenty-eight measurements improved significantly and three regressed significantly.

| Measurement | Enabled/disabled result |
|---|---:|
| `gc_traversal` | 1.60 times faster |
| `btree_gc_only` | 1.28 times faster |
| `create_gc_cycles` | 1.22 times faster |
| Async-tree family | 1.06 to 1.18 times faster |
| `float` | 11.4% slower |
| `sqlite_synth` | 10.4% slower |
| `sqlalchemy_declarative` | 2.6% slower |

Raw experiment: [FT runtime ABBA](baselines/pgo-ft-full-abba-2026-10-07/)

## Cross-build result: `sqlite_synth`

`sqlite_synth` regressed in both builds and in both halves of each ABBA sequence.

| Build | First disabled/enabled pair | Second enabled/disabled pair | Combined |
|---|---:|---:|---:|
| GIL | 37.7% slower | 38.4% slower | 38.1% slower |
| FT | 10.0% slower | 10.7% slower | 10.4% slower |

The direction, size within each build, and two-pair reproduction make this a strong shared investigation target. The result does not identify the cause. It is consistent with a shared activation, collection-entry, bookkeeping, or object-traversal cost, but each of those explanations remains a hypothesis until measurements locate the additional time.

## Correctness verification

The optimized candidate builds passed the focused collector and PGO workload suites after the performance runs.

| Build | Files | Tests run | Expected skips | Result |
|---|---:|---:|---:|---|
| GIL | 5 | 103 | 57 tests across two FT-only files | Pass |
| FT | 5 | 154 | 34 | Pass |

The files were `test_gc_parallel`, `test_gc_parallel_properties`, `test_gc_ws_deque`, `test_gc_ft_parallel`, and `test_parallel_gc_profile`.

## Reproduction commands

The control and candidate builds differed only in the make-time value shown below.

```bash
# Configure GIL; add --disable-gil for FT.
../cpython/configure \
    --with-parallel-gc \
    --enable-optimizations \
    --with-lto

# Standard-PGO control.
make -j36 PARALLEL_GC_PROFILE_TASK=

# Parallel-aware-PGO candidate.
make -j36
```

The complete PGO regression command was:

```bash
<driver-python> benchmarks/run_pyperformance.py binary-abba \
    --baseline-python <standard-pgo-python> \
    --baseline-source cpython \
    --candidate-python <parallel-pgo-python> \
    --candidate-source cpython \
    --mode disabled \
    --benchmarks=-dask,-fastapi,-genshi,-xdsl \
    --run-style rigorous \
    --affinity 0-31 \
    --timeout 3600 \
    --output-dir <result-directory>
```

The complete runtime comparison command was:

```bash
<driver-python> benchmarks/run_pyperformance.py abba \
    --python <parallel-pgo-python> \
    --source cpython \
    --benchmarks=-dask,-fastapi,-genshi,-xdsl \
    --run-style rigorous \
    --affinity 0-31 \
    --timeout 3600 \
    --output-dir <result-directory>
```

## Conclusions and limits

The supplementary workload demonstrably supplies PGO data for both parallel collectors. The full runtime-disabled experiments found no shared slowdown attributable to that training, so the PGO integration was retained.

Runtime activation was aggregate-neutral in the GIL build and improved the FT aggregate on this AArch64 machine. Both builds contain important positive and negative regions. These measurements do not replace the project-specific throughput and pause suite, do not generalize beyond the tested host, and do not prove causes for any individual result.

The next performance investigation should begin with a focused same-binary ABBA reproduction of `sqlite_synth`, followed by collection-count and timing attribution. No collector change is justified until that evidence distinguishes time inside collection from activation, bookkeeping, or unrelated benchmark work.
