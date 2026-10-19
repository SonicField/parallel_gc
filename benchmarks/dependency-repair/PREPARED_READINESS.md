# Complete prepared-environment readiness

[check_prepared_suite.py](check_prepared_suite.py) executes the original 100 default programs through upstream `Benchmark.run`, using explicitly prepared environments. It retains each original script, data directory and workload options. [Tests](test_prepared_readiness.py) check the selection against the preserved inventory and check those execution inputs.

The usual upstream suite launcher reinstalls each program's original dependency requirements. That would replace the verified Python 3.16 repairs with incompatible pins. This readiness-only launcher separates dependency installation from execution; it does not modify the pyperformance submodule or benchmark programs.

Before execution it requires `pip check`, the three dependency correctness suites, four native-extension probes and the existing GC-mode preflight. Each saved result must pass the existing worker runtime attestation, including GIL-disabled execution in FT. Failures are named in `summary.json`; other programs continue so a passing subset cannot conceal them.

The launcher uses `--debug-single-value`. Its output proves execution, not speed or statistical equivalence. Do not use its timings as ABBA results. For rigorous comparisons, the official [ABBA runner](../run_pyperformance.py) now accepts prepared environments without reinstalling the old pins; see [PERFORMANCE.md §2.1](../../docs/PERFORMANCE.md#21-pyperformance-abba).

Example, from the parent `parallel_gc` repository, with paths to the driver environment and prepared target environment:

```bash
"$driver_python" benchmarks/dependency-repair/check_prepared_suite.py \
  --python "$prepared_python" \
  --mode enabled \
  --affinity 0-31 \
  --timeout 300 \
  --output-dir "$new_output_directory"
```

The output directory must not already exist. Run baseline/current, GIL/FT and enabled/disabled separately, using identical mode-specific dependency builds on both sources. Preserve all eight summaries and raw results before claiming complete readiness.
