# Explicit collector-state metadata in results analysis

The inherited result check converts enabled-state metadata to Boolean. For a disabled run, that could accept an absent field or integer zero as though the producer had explicitly recorded `False`. The analysis now requires an explicit Boolean in every saved run, including calibration. This strengthens verification of the already required runtime mode; it changes neither the experiment nor its calculations.

Planted missing-field and integer-zero fixtures both passed the old analysis when they should have been rejected. Both negative controls fail before the correction and pass afterward. All ten analysis tests now pass. A first test-fixture reuse error is retained separately from the corrected negative controls; it is not evidence about real benchmark execution.

The two completed real suites, `01-baseline.json` and `02-candidate.json` in the GIL disabled campaign, pass the new explicit-state check. No raw data was edited. The measurement runner, hook, original benchmark programs, prepared environments and frozen binaries are unchanged. Their input fingerprints remain those of the existing campaign.

[checks.tar.gz](checks.tar.gz) retains the initial fixture failure, corrected pre-change failures, passing ten-test output and real-suite revalidation. These are local working verification records, not independent audit closure or comparative performance results.

Reproduce tests in the driver environment:

```bash
"$driver_python" benchmarks/test_analyse_pyperformance_abba.py
```

[Full experiment and analysis protocol](../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md).
