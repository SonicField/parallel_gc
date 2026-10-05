# Exact-tuple traversal verification

## Verdict

Retain CPython commit `0205d62bcb` (`Specialize FT parallel traversal for exact tuples`). The candidate meets the fixed 20 percent enabled-mode improvement in both ABBA halves, is neutral when parallel GC is disabled, preserves tuple traversal and untracking behavior, and passes the focused correctness, sanitizer, assembly, counter, adaptive, and large-heap gates.

## Source and binaries

- Common base: CPython `ce39536ced` with the exact-list specialization retained.
- Retained candidate: CPython `0205d62bcb655e05d60bd5e7fa17cbe4bd7864a4`.
- Baseline executable SHA-256: `f9712352ebec25560ddb4b372ee71041f08dd09a7fcfe930d64b5c678e442cc1`.
- Measured candidate executable SHA-256: `3112f439dc1a9dd15f3fa976eb3e6c79118086ab3fc6b7ac03eed305d87153ec`.
- Final-source rebuilt candidate executable SHA-256: `e646d95f00eaede61f0a26921a6464d87fdee59dfc9c90482d800741404f5e75`.
- All executables are AArch64 free-threaded builds configured with `--with-parallel-gc --disable-gil --enable-optimizations --with-lto`.
- Both measured builds used CPython's unchanged standard PGO task. Parallel-aware PGO remains a separate later experiment.
- Benchmark affinity: logical CPUs `0-31`.

The measured candidate contained one additional `Py_DEBUG` statistic used during mutation development. It was compiled out of the measured optimized executable and was unused by the final tests, so it was removed before the retained commit. The final tree was rebuilt from a clean profile, passed the complete standard PGO task and focused optimized tests, and retained the same direct tuple loop in assembly. No release-mode collector logic changed after the ABBA campaign.

## Hypothesis and tests

An optimized profile of the list-retained build attributed 37.00 percent of samples to `propagate_pool_visitproc`, 13.61 percent to `tuple_traverse`, and 9.67 percent to `_PyGC_TryMarkAlive`. This kept the tuple callback-removal hypothesis alive before tuple code was written.

The dedicated tests cover reachable tuple graphs, reverse traversal of every tuple slot, repeated references, deep nesting, self and mutual cycles, tuple untracking, immediate alive-bit cleanup after untracking, unreachable cycles, and generic traversal of tuple subtypes with additional references.

Three temporary mutations established sensitivity:

- Omitting tuple index zero made the direct traversal probe observe 0 rather than 1 edge and 256 rather than 257 edges.
- Omitting the alive-bit clear after `_PyTuple_MaybeUntrack` made the immediate post-untrack probe observe the alive bit still set.
- Sending tuple subtypes through the exact-tuple path made the subtype-path assertion fail.

All mutations were removed before the final builds.

## Correctness and build results

- Free-threaded debug: all four focused files passed, 141 tests run and two skipped.
- GIL debug: applicable focused tests passed, 90 tests run and 49 skipped because the collector tests are free-threaded-only.
- AddressSanitizer free-threaded debug: all four focused files passed, 141 tests run and two skipped, with `detect_leaks=0` and `halt_on_error=1`.
- The fresh baseline and candidate standard PGO tasks each passed all 43 files: 10,470 tests run and 462 skipped.
- The final-source optimized build passed all four focused files: 141 tests run and 30 expected release-build skips.

## Binary ABBA

The enabled campaign is in `ft-exact-tuple-enabled-abba-2026-10-05/`. The disabled build-drift control is in `ft-exact-tuple-disabled-control-abba-2026-10-05/`.

| Mode and half | Baseline | Candidate | Result |
|---------------|----------|-----------|--------|
| Enabled AB | 2.29 ms | 1.40 ms | 1.64x faster |
| Enabled BA | 2.28 ms | 1.43 ms | 1.59x faster |
| Disabled AB | 1.64 ms | 1.64 ms | Not significant |
| Disabled BA | 1.64 ms | 1.65 ms | Not significant |

The combined enabled comparison is 2.29 milliseconds versus 1.42 milliseconds, or 1.61x faster. Pyperformance emitted stability warnings for the enabled endpoints, but the two baseline and two candidate endpoints agree closely and the result exceeds the fixed 20 percent gate in both halves.

## Assembly and hardware counters

The baseline `thread_pool_do_work` calls exact tuples through an indirect `blr` after `_PyTuple_MaybeUntrack`. The candidate compares the resolved traversal function with `PyTuple_Type.tp_traverse`, keeps the same untracking and alive-bit cleanup sequence, loads `ob_item` in a reverse-index loop, and calls `_PyGC_TryMarkAlive` directly. The generic indirect call remains for tuple subtypes and other types. The direct tuple loop does not depend on PGO devirtualization.

`perf stat -r 3` measured 500 benchmark iterations in baseline/candidate/candidate/baseline order. Endpoint means were:

| Counter | Baseline | Candidate | Change |
|---------|----------|-----------|--------|
| Cycles | 12.572 billion | 9.740 billion | -22.5% |
| Instructions | 28.778 billion | 19.532 billion | -32.1% |
| Branches | 8.773 billion | 6.205 billion | -29.3% |
| Branch misses | 33.152 million | 32.949 million | -0.6% |
| Cache misses | 182.809 million | 195.095 million | +6.7% |

The instruction and branch reductions match removal of the per-edge generic callback. Branch misses are flat and cache misses increase, so neither explains the speedup.

## Large-heap and adaptive guardrails

All eight established requested heap families ran at 500,000 requested objects with three samples per endpoint in baseline/candidate/candidate/baseline order. Generated object counts matched for every baseline and candidate sample. `ai_workload` deterministically generated 399,728 objects; every other family generated 500,000. Combined parallel-collection means were:

| Heap | Baseline | Candidate | Candidate time change |
|------|----------|-----------|-----------------------|
| Chain | 89.690 ms | 90.156 ms | +0.5% |
| Tree | 101.015 ms | 102.382 ms | +1.4% |
| Wide tree | 100.461 ms | 101.592 ms | +1.1% |
| Graph | 129.926 ms | 126.007 ms | -3.0% |
| Layered | 111.447 ms | 109.196 ms | -2.0% |
| Independent | 111.005 ms | 111.022 ms | +0.0% |
| AI workload | 142.725 ms | 145.391 ms | +1.9% |
| Web server | 115.718 ms | 116.271 ms | +0.5% |

The geometric-mean collection-time change is +0.03 percent, which is neutral. These short collection-only samples are guardrails, not publishable throughput or pause claims.

The final candidate also completed one fixed-seed adaptive cycle with five collections in each of the dense, shallow-wide, and allocation-spike phases. Active workers stayed within the specified 2-16 range and changed in every phase. The tuple change does not alter the controller, its timing inputs, or its selection rules.
