# Exact-list traversal verification

## Verdict

Retain CPython commit `06f1d674a4` (`Specialize FT parallel traversal for exact lists`). The candidate meets the predeclared 20 percent enabled-mode improvement in both ABBA halves, is neutral when parallel GC is disabled, preserves the tested traversal contract, and passes the focused correctness, sanitizer, assembly, counter, adaptive, and large-heap gates.

## Source and binaries

- Common base: CPython `01a89cbeb84b41931a3f30875022cc854d210fc8`
- Candidate source: the exact tree committed as `06f1d674a4`
- Baseline executable SHA-256: `54a5fb0602314f62d5aa4a4dd0d1593ad15fbd681e1eba65d3272074a1f2fbee`
- Candidate executable SHA-256: `fc6229dc412e6a931dce5740700388dbf351735267ecefd0a36727492463f98d`
- Both executables: AArch64 free-threaded builds configured with `--with-parallel-gc --disable-gil --enable-optimizations --with-lto`
- Both builds used CPython's unchanged standard PGO task. Parallel-aware PGO remains a separate later experiment.
- Benchmark affinity: logical CPUs `0-31`

The campaigns were run before the candidate commit was created. Their candidate provenance therefore records base revision `01a89cbeb8` and four dirty paths. No source changed between the build, campaigns, and commit; `06f1d674a4` records that exact tree.

## Correctness and sensitivity

- The clean optimized baseline passed the three black-box list contract tests.
- The candidate passed five dedicated list tests in the free-threaded debug build. They cover empty and populated lists, both endpoints, reverse order, repeated references, deep nesting, self and mutual cycles, reachable and unreachable cycles, growth and shrinkage, and list-subclass fallback.
- Omitting list index zero did not make the initial liveness-only test fail. A later free-threaded reachability phase recovered the missed early propagation edge. This falsified the assumption that final heap outcome alone could verify this fast path.
- A narrow `Py_DEBUG` probe was then added. With index zero omitted, it failed at sizes 1 and 257, observing 0 rather than 1 edge and 256 rather than 257 edges.
- Temporarily routing list subclasses through the direct path made the subtype-path test fail. Both mutations were removed before the final builds.
- Free-threaded debug: all four focused parallel-GC files passed, 134 tests run and two skipped.
- GIL debug: the applicable focused files passed, 83 tests run and 42 skipped because the tests were free-threaded-only.
- AddressSanitizer free-threaded debug: all four focused files passed, 134 tests run and two skipped, with `detect_leaks=0` and `halt_on_error=1`.
- The standard PGO task passed all 43 files: 10,470 tests run and 462 skipped.

The optimized focused run initially exposed two pre-existing lifecycle-test failures: two tests called debug-only `gc._get_thread_pool_stats()` in a release build. The untouched baseline reproduced both failures. They were repaired separately in CPython commit `d29fb102c4` by retaining the public lifecycle assertions in every build and conditioning only the debug-hook assertions. The optimized four-file rerun then passed all 134 tests with 27 expected skips. This repair is not part of the list implementation commit.

## Binary ABBA

The enabled campaign is in `ft-exact-list-enabled-abba-2026-10-05/`. The disabled build-drift control is in `ft-exact-list-disabled-control-abba-2026-10-05/`. SHA-256 values for every raw and combined result were recomputed and match both campaign manifests.

| Mode and half | Baseline | Candidate | Result |
|---------------|----------|-----------|--------|
| Enabled AB | 2.23 ms | 1.38 ms | 1.61x faster |
| Enabled BA | 2.24 ms | 1.37 ms | 1.64x faster |
| Disabled AB | 1.56 ms | 1.55 ms | Not significant |
| Disabled BA | 1.54 ms | 1.54 ms | Not significant |

Pyperformance emitted stability warnings, but the two baseline endpoints and two candidate endpoints agree closely. The result exceeds the fixed 20 percent acceptance threshold in both enabled halves.

## Assembly and hardware counters

In the baseline `thread_pool_do_work`, list objects reach `tp_traverse` through the generic indirect `blr` at `0x45f98c`. In the candidate, the function compares the resolved traversal function with `PyList_Type.tp_traverse`, loads `ob_item` in a reverse-index loop at `0x45f788-0x45f7d4`, and calls `_PyGC_TryMarkAlive` directly. The generic indirect call remains for tuples and other types. The direct list loop does not depend on PGO devirtualization.

`perf stat -r 3` measured 500 benchmark iterations in baseline/candidate/candidate/baseline order. Endpoint means were:

| Counter | Baseline | Candidate | Change |
|---------|----------|-----------|--------|
| Cycles | 12.454 billion | 9.170 billion | -26.4% |
| Instructions | 29.747 billion | 20.126 billion | -32.3% |
| Branches | 9.260 billion | 6.222 billion | -32.8% |
| Branch misses | 31.113 million | 29.280 million | -5.9% |
| Cache misses | 178.350 million | 181.391 million | +1.7% |
| Elapsed | 2.538 seconds | 1.628 seconds | -35.8% |

The large instruction and branch reductions match removal of the per-edge generic traversal callback. Absolute cache misses are effectively flat; they do not explain the speedup.

## Large-heap and adaptive guardrails

All eight established requested 500,000-object heap families ran three samples per endpoint in baseline/candidate/candidate/baseline order. Generated object counts matched for every baseline and candidate sample. Combined parallel-collection means were:

| Heap | Baseline | Candidate | Candidate time change |
|------|----------|-----------|-----------------------|
| AI workload | 145.300 ms | 142.958 ms | -1.6% |
| Chain | 91.138 ms | 90.103 ms | -1.1% |
| Graph | 127.953 ms | 127.134 ms | -0.6% |
| Independent | 113.892 ms | 111.552 ms | -2.1% |
| Layered | 110.596 ms | 104.179 ms | -5.8% |
| Tree | 104.158 ms | 101.172 ms | -2.9% |
| Web server | 116.886 ms | 116.337 ms | -0.5% |
| Wide tree | 103.596 ms | 100.577 ms | -2.9% |

The geometric mean collection-time reduction is 2.2 percent. These short collection-only samples are guardrails, not publishable throughput or pause claims.

The candidate also completed one fixed-seed adaptive cycle with five collections in each of the dense, shallow-wide, and allocation-spike phases. Active workers remained within the specified 2-16 range and changed across workloads. The list change does not alter the controller, its timings, or its selection rules.
