# Feature-off runtime probe repair

Goal: run the benchmark harness tests on both feature-enabled and feature-off GIL/FT builds without weakening runtime attestation or changing collector behaviour.

CI run `39248590193` fails one GIL feature-off test and two FT feature-off tests. The test probe used `hasattr(gc, "disable_parallel")` to choose runtime-disabled mode. Feature-off builds expose the API but report `available=False` and reject disable calls. This is a test-probe error, not a collector failure.

The existing real-runtime tests reproduce the failures locally on both feature-off binaries. Feature-on controls pass. The repair selects the probe mode from `gc.get_parallel_config()["available"]`, retaining the missing-API fallback. The production hook and mode functions are unchanged. A regression test requires feature-off mode to accept an unavailable API without calling enable/disable; the real-runtime probe additionally checks its recorded collector mode and availability.

Afterwards the complete CI harness selection passes on all four configurations: 76 tests per run, with one FT-only skip in each GIL run and no skips in FT. The FT test that deliberately forces the GIL still verifies rejection; it is a negative control, not a benchmark execution override. No test is skipped because parallel GC was compiled out.

## Reproduction

From the parent repository, use a test environment containing pyperf 2.10.0 and one target binary per configuration:

```bash
"$test_python" -m unittest -v \
  benchmarks.test_container_traversal_benchmark \
  benchmarks.test_gc_adaptive_benchmark \
  benchmarks.test_gc_perf_benchmark \
  benchmarks.test_pyperformance_support
```

Workspace: `/tmp/parallel-gc-ci-repair-20261019-IuvW1e`. Environments use the existing `build-ci-check-gil-off`, `build-ci-check-gil-on`, `build-control-ft` and `build-fidelity-ft` binaries. The environments were created without pip; the existing pure-Python pyperf package and metadata were copied into them. Initial direct imports showed these binaries had no pyperf installation; no test outcome was claimed from that dependency check.

Retained `*-before.log.gz` files show the existing focused runtime tests before the fix. `gil-off-regression-before.log.gz` shows the focused tests still fail after adding checks but before changing mode selection. `*-after.log.gz` contains all 76 tests per configuration. `binaries.sha256` records the tested executable bytes.

This repair changes only parent-repository tests. Hosted confirmation requires publishing this commit and rerunning CI. It does not resolve the separate Clang unused-wrapper error in CPython or establish performance neutrality.
