# Module-rooting benchmark integration

16 October 2026. Imported the workload dimension from parent candidate `306644b59682223980fd08cf2262d3b8e40a3eb5`. The creation-pool ownership repair was committed separately in `5b786a3`; these additions preserve its stronger scheduling tests.

## Agreed contract

Sustained heaps are held in module state between operations, not a persistent worker-frame heap local. Shuffle and churn may temporarily reference the heap or a new batch. A mutating workload cannot honestly promise absence of every stack reference. Controlled single collections instead release the collecting-frame keep-set reference before collection. Separate creation-pool tests verify that idle allocation helpers release their results, including the caller's exact survivor selection.

The new results have separate JSON keys: `collection_results_module`, `synthetic_by_heap_module` and `mixed_workload_module_cache`. Existing result keys/types remain compatible with the historical fixture from `724b74b`. Default frame-rooted generators, seeds, durations and workload selection are unchanged. The new full synthetic-inclusive suite also runs all original workloads and took about 95 minutes per invocation in the recorded candidate campaigns. This integration has not rerun those performance campaigns.

## Test-first checks and discovered failures

Before implementation, the imported additions produced eleven errors in the 21-test harness: missing rooting arguments, module holders and result fields. After importing the implementation, a newly added activation-failure test exposed a module cache retained after activation raises. Constructing the optional cache only after activation succeeds fixes this new-path failure; collector activation/error semantics are unchanged.

The candidate's sustained test incorrectly treated temporary newly published clusters as forbidden stack roots. The agreed contract instead tests whole-heap holder aliases at churn allocation boundaries. This is not a blanket assertion that every heap reference is absent from every stack at every moment.

The initial test probe also read `f_locals` in other executing threads. Repeated FT release checks segfaulted (exit 139); FT debug aborted with a GC refcount assertion (exit 134, raw log retained). An additional FT feature-off debug run of the original synthetic probe aborted during iteration 18 of a requested 20 repeats, with a freelist assertion. One earlier single feature-off suite passed. This shows why a single pass did not validate the test's safety; it does not identify an active parallel-collector defect.

CPython explicitly documents that accessing another executing thread's `f_locals` is unsafe and may crash: `cpython/Doc/howto/free-threading-python.rst`, "Frame objects". The revised probe inspects only its calling stack. Each sustained worker checks its own stack; the controlled collection checks its collecting stack, supported independently by creation-pool ownership tests. A regression test rejects use of `sys._current_frames`. This correction is in test instrumentation, not benchmark workloads or collector source. No claim is made to have traced every initial crash instruction to that unsafe access.

## Positive controls and final results

The original frame-rooted variants are positive controls. Two planted in-memory mutations were also detected on the host interpreter and fresh FT debug binary: a persistent `module_worker.local_heap` alias and an uncleared collection `keep_refs`. Both tests failed for the intended alias. `rooting_mutations.py` reproduces these checks and restores the original functions; it does not edit project source files.

After correcting the probe, the final 23-test harness passed on the host interpreter. Each fresh GIL/FT release/debug binary then passed ten full suites with runtime policy off and ten armed: 460 tests per binary, 1,840 total, zero failures/errors. These checks exercise actual ownership and runtime compatibility; their short workload durations are test scaffolding, not performance measurements. The controlled heap variants report identical seeded object counts; worker exceptions propagate; holders are removed on normal completion and tested failure paths; old JSON keys/types and new result destinations pass their checks.

Binary/configuration provenance is in the separate [cleanup report](../dead-code-cleanup-2026-10-16/README.md): source content matches CPython `442a97213f`, fresh non-PGO ARM64 builds, detached dirty source stamp, optional dependency limits recorded. `rooting_checks.py` and four completion logs accompany this report. To reproduce from the parent root, use `PYTHONPATH="$PWD" <build>/python benchmarks/results/investigations/module-rooting-integration-2026-10-16/rooting_checks.py`; the build must provide the feature-on runtime API. Run `python3 -m unittest -v benchmarks.test_gc_perf_benchmark` for a build-agnostic single suite.

These tests do not establish performance neutrality, all possible rooting patterns, or Windows/macOS portability. Fresh hosted tests and matched-harness performance campaigns remain pending. No rejected coordination/splitting experiment was imported.

## Follow-up: release the collection probe's own references

The observation helper was excluding its own frame while checking the benchmark's boundary, but retained its `ids` list during the subsequent real `gc.collect()`. The benchmark implementation released its references correctly; the test instrument was turning that collection into a frame-rooted one. A new check inspects the probe's frame before the real collection and failed with the retained `ids` alias. Releasing `ids` after the observation fixes the test instrument. No workload, duration, result schema or collector code changed.

The resulting 24-test harness passes on the host interpreter. On each fresh GIL/FT release/debug binary, ten policy-off and ten armed suites pass: 480 tests per binary, 1,920 total, zero failures/errors. The four `*-probe-followup.log` files retain these results separately from the earlier 23-test evidence. Source content for these binaries matches CPython `0fc7b3ccb938e367e23c140995a8f2e4b6757b49`; these are the clean non-PGO builds recorded in the [production-verifier report](../production-verifier-integration-2026-10-16/README.md), with its source-stamp and optional-module limits. Both planted persistent-reference mutations remain detected on the host and FT debug interpreter. The older 1,840-test result above remains evidence for the earlier harness, not a count for this revision.
