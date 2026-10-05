# Exact-dictionary traversal verification

## Verdict

Retain CPython commit `3459fbefd8` (`Specialize FT parallel traversal for exact dictionaries`). All three layouts exceed the fixed 5 percent enabled-mode threshold in both ABBA halves. The change preserves `dict_traverse` layout rules and subtype handling, is neutral when parallel GC is disabled, and passes the focused correctness, mutation, sanitizer, assembly, counter, adaptive, and large-heap gates.

## Source and binaries

- Baseline source: clean CPython commit `0205d62bcb`, with the exact-list and exact-tuple specializations retained.
- Candidate source: the runtime source committed as `3459fbefd8`. The candidate binary identifies the preceding commit plus a dirty tree because it was built before the verified source and tests were committed. The only source addition after the build was the final Python unreachable-cycle test.
- Both binaries are free-threaded CPython 3.16 PGO+LTO builds configured with `--with-parallel-gc --disable-gil --enable-optimizations --with-lto` and the same dependency prefix.
- Baseline executable SHA-256: `e646d95f00eaede61f0a26921a6464d87fdee59dfc9c90482d800741404f5e75`; build ID: `43eb324d091b95eca6421170df8a862cde3d2d18`.
- Candidate executable SHA-256: `df62624d4a891d99a988642f4fce31a65a862f7c2f029ba792c37229d8b23796`; build ID: `7e1b4dce3b3607569dc87030d8810169ef0aa229`.
- Host: 72-logical-CPU AArch64 Linux, with benchmark processes restricted to CPUs 0-31.

## Approved design boundary

One internal macro owns the reference-enumeration rules for split tables, combined Unicode-key tables, and general-key tables. Serial `dict_traverse()` supplies `Py_VISIT`; the FT propagation phase supplies a direct `propagate_pool_visit` operation. The macro evaluates the dictionary once and preserves slot order, null handling, live-entry selection, and the general-table value-before-key order.

The optimized collector selects the path by comparing the resolved traversal function with `PyDict_Type.tp_traverse`. A dictionary subtype or any type with a different traversal function remains on the generic callback path. No atomic, queue, threshold, adaptive, phase-order, or object-layout rule changed.

## Pre-code profile and test sensitivity

The tuple-retained baseline profile identified a material dictionary cost in every layout:

| Layout | Generic visit callback | `dict_traverse` | `_PyGC_TryMarkAlive` |
|--------|------------------------|-----------------|----------------------|
| General keys | 18.8% | 4.0% | 10.1% |
| Combined Unicode keys | 29.5% | 9.5% | 5.8% |
| Split table | 25.0% | 9.4% | 9.3% |

Before implementation, the behavior-only tests passed while four structural assertions failed because no direct dictionary path existed. After implementation, temporary compiled mutations proved that the tests detect each central contract:

- Starting the split-table loop at slot one failed the edge-count assertion.
- Starting the Unicode-table loop at slot one failed the edge-count assertion.
- Visiting a general entry's key before its value failed the first-edge assertion.
- Selecting the direct path with `PyDict_Check()` instead of exact traversal-function identity failed the subtype assertion.

All mutations were removed. The retained tests cover all three storage layouts, deleted and missing entries, repeated references, deep reachable graphs, unreachable self and mutual cycles, value-before-key order, and generic subtype traversal.

## Correctness and sanitizer results

- FT debug focused suite: 148 tests, 2 expected skips, success.
- GIL debug focused suite: 97 tests, 56 expected skips, success.
- FT ASan focused suite: 148 tests, 2 expected skips, success.
- FT optimized focused suite: 148 tests, 34 expected release-build skips, success.
- A fresh standard PGO task completed 43 test files, 10,470 tests, and 462 expected skips before the final test-only addition.

The focused suite consists of `test_gc_ft_parallel`, `test_gc_parallel`, `test_gc_parallel_properties`, and `test_gc_ws_deque`.

## Enabled binary ABBA

The rigorous campaign is in `ft-exact-dict-enabled-abba-2026-10-05/`. Each endpoint uses the same workload, affinity, hook-owned activation, and attested enabled state.

| Layout | Baseline AB | Candidate AB | AB result | Baseline BA | Candidate BA | BA result |
|--------|-------------|--------------|-----------|-------------|--------------|-----------|
| General keys | 3.50 ms | 2.77 ms | 1.26x faster | 3.44 ms | 2.77 ms | 1.24x faster |
| Split table | 1.47 ms | 1.14 ms | 1.29x faster | 1.44 ms | 1.15 ms | 1.25x faster |
| Unicode keys | 1.14 ms | 992 us | 1.15x faster | 1.11 ms | 969 us | 1.14x faster |

Every comparison is statistically significant. Combined results are 1.25x faster for general dictionaries, 1.27x faster for split dictionaries, and 1.14x faster for Unicode dictionaries.

## Disabled control

The complete control is in `ft-exact-dict-disabled-control-abba-2026-10-05/`. Unicode dictionaries were unchanged and general dictionaries were 1.02x faster. The combined split result was 1.03x slower, driven by one 1.04x leg; the other leg was 1.02x and not significant.

The split workload was therefore repeated alone in `ft-exact-dict-split-disabled-recheck-2026-10-05/`. Its two legs were 1.02x slower and 1.00x faster, neither significant; the combined result was 1.01x slower and not significant. The repeat falsifies a stable serial-path regression.

## Assembly and hardware counters

The final PGO+LTO AArch64 `thread_pool_do_work` contains a direct traversal-function comparison followed by distinct split, Unicode, and general loops. Each loop invokes `_PyGC_TryMarkAlive` directly through the inlined propagation operation. Per-edge indirect callback calls are absent from those loops; indirect `blr` calls remain only in the generic fallback.

`perf stat -r 3` measured 500 collections at each endpoint in baseline/candidate/candidate/baseline order. Raw endpoint CSV files are in `ft-exact-dict-counters-2026-10-05/`. Combined endpoint means were:

| Layout | Counter | Baseline | Candidate | Change |
|--------|---------|----------|-----------|--------|
| General | Cycles | 23.430 B | 21.268 B | -9.2% |
| General | Instructions | 63.482 B | 59.757 B | -5.9% |
| General | Branches | 16.068 B | 15.239 B | -5.2% |
| Split | Cycles | 11.021 B | 9.769 B | -11.4% |
| Split | Instructions | 27.084 B | 21.556 B | -20.4% |
| Split | Branches | 7.697 B | 6.423 B | -16.5% |
| Unicode | Cycles | 8.439 B | 7.843 B | -7.1% |
| Unicode | Instructions | 19.508 B | 15.938 B | -18.3% |
| Unicode | Branches | 5.528 B | 4.722 B | -14.6% |

Branch misses increased by 3.9, 13.3, and 1.3 percent for general, split, and Unicode layouts respectively. Cache misses fell by 4.7, 2.3, and 1.0 percent. The instruction and branch reductions support removal of callback and generic traversal overhead; branch-miss reduction is not the mechanism.

## Large-heap and adaptive guardrails

All eight established heap families ran at 500,000 requested objects with three samples per endpoint in baseline/candidate/candidate/baseline order. Raw parallel-collection samples and provenance are in `ft-exact-dict-large-heap-abba-2026-10-05.json`. Generated object counts matched at every endpoint; `ai_workload` generated 399,728 objects and every other family generated 500,000.

| Heap | Baseline | Candidate | Candidate time change |
|------|----------|-----------|-----------------------|
| AI workload | 141.337 ms | 140.873 ms | -0.3% |
| Chain | 89.975 ms | 90.913 ms | +1.0% |
| Graph | 125.844 ms | 122.412 ms | -2.7% |
| Independent | 108.483 ms | 111.789 ms | +3.0% |
| Layered | 103.727 ms | 108.068 ms | +4.2% |
| Tree | 101.586 ms | 100.875 ms | -0.7% |
| Web server | 114.320 ms | 115.167 ms | +0.7% |
| Wide tree | 100.274 ms | 100.710 ms | +0.4% |

The geometric-mean collection-time change is +0.69 percent, which is neutral for this short three-sample guardrail. These measurements are not publishable throughput or pause claims.

The candidate also completed one fixed-seed adaptive cycle with five collections in each phase. Active workers changed within every phase and remained in the specified 2-16 range: dense graph used 2-4, shallow-wide used 2-4, and allocation spike used 4-12. The dictionary change does not alter the controller, timing inputs, or selection rules.
