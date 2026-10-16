# Runtime GIL-state attestation

The pyperformance hook previously recorded collector activation but not the runtime GIL state after workload imports. Bare-interpreter preflight cannot establish that a later extension import did not enable the GIL in a free-threaded worker.

The hook now checks this state in `teardown`, records `parallel_gc_build_gil_disabled` and `parallel_gc_runtime_gil_enabled`, and rejects an FT worker with its GIL enabled. It also rejects inconsistent GIL-build state and an FT build without a runtime probe. For older GIL-only interpreters without that probe, GIL-enabled state follows from their build mode. It does not set `PYTHON_GIL`, change collector selection, or force an extension to run without the GIL.

Inspection of pyperf 2.10.0's `_worker.py` confirms teardown runs after the `_compute_values` loop and the timing function's return. The check is outside measured values. It checks the measured worker's main interpreter; it does not attest arbitrary workload-spawned children or subinterpreters. The existing passive `_process_time.py` hook remains passive.

## Verification

Six new decision tests failed before implementation: three missing metadata errors and three missing rejection failures. With implementation, all 35 support tests pass on each of the four isolated test environments. The GIL runs skip the FT-only real-process rejection test. The two real-process tests import `decimal`, use the actual build/runtime probes and actual collector API, and verify recorded metadata or rejection. Each FT environment also explicitly starts a child with `PYTHON_GIL=1` and requires rejection without successful metadata. This environment override is confined to that test child, not the measurement campaign.

The complete parent harness selection now runs 75 tests on each binary, up from 67 before these eight tests. GIL skips one FT-only test; FT skips none. The four result logs are preserved here. All checks ran on CPU 32, outside the active project measurement's affinity 0–31. These short checks are not performance measurements.

Reproduce from the parent repository, substituting each of `baseline-gil`, `candidate-gil`, `baseline-ft`, `candidate-ft` for `VARIANT`:

```bash
taskset -c 32 \
  /tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW/test-env-VARIANT/bin/python \
  -m unittest \
  benchmarks.test_container_traversal_benchmark \
  benchmarks.test_gc_adaptive_benchmark \
  benchmarks.test_gc_perf_benchmark \
  benchmarks.test_pyperformance_support
```

The initial broader invocation misspelled the first two module names and failed their imports. Its log remains at the scratch root as `baseline-gil-harness-attestation-tests.log`. The corrected invocation used the exact four modules from the Linux workflow; its four `*-harness-attestation-tests-v2.log` files are the preserved passing evidence. The failed invocation was not a collector failure.

## Measurement boundary and fingerprints

At 23:37 UTC on 16 October, the four project GIL legs were complete, FT baseline leg 1 was live, and the pyperformance output directory was empty. No pyperformance campaign had started. The project benchmark does not import this hook; neither timed benchmark implementation nor any CPython source changed.

Before any pyperformance run, froze the new hook SHA-256:

```text
e7a98175a0928a495bd27f93bef0d475a5eee8d65fb94045cff3fb0079783ea4  benchmarks/pyperformance_support/parallel_gc_pyperformance/hook.py
```

The live controller's scratch `results/harness.sha256` now additionally checks that hook after every subsequent project leg and pyperformance campaign. Preserved the initial three-file manifest as `results/harness-before-hook.sha256` (SHA-256 `41108925177a13ff8cf16654593546d3e4cb6b6f11d874137d805bf7cc529856`). The four-file manifest's SHA-256 is `6bef99eb388d7893dabdee39bb881991062ff5c1102116cca0a303412899a4bc`; an independent `results/pyperformance-hook.sha256` holds the same hook fingerprint. All four current checks pass. The running launcher script was not edited or restarted.

Hosted CI at the previously published parent checkpoint does not cover these newly added parent tests. Its CPython source validation remains a separate requirement; this parent change needs publication and a subsequent harness matrix run. Neither current hosted CI nor completed pyperformance results are claimed here.
