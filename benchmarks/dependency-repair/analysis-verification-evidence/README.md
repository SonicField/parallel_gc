# Full source-ABBA calculation checks

[analyse_pyperformance_abba.py](../../analyse_pyperformance_abba.py) implements the already declared descriptive method; it does not assign performance acceptance. Each source mean weights its two suite legs equally. Half comparisons are C2/B1 and C3/B4. Positive execution-time changes are slowdowns. Per-leg worker samples are not treated as independent source experiments.

Eight tests pass using real serialized pyperf fixtures. They check exact means/ratios, retain opposing half-directions and reject incomplete/changed evidence. The default analysis scope is all 100 original programs and 127 named results. Unit fixtures explicitly use a one-program scope for arithmetic only; the CLI does not expose that relaxation.

Retained logs show the pre-implementation missing-tool failures, a fixture-construction error corrected before acceptance, eight passing tests and a direct CLI attempt to analyse the incomplete live campaign. The latter exits 2 and produces neither JSON nor Markdown, confirming that partial collection is not reported as complete.

The logs are in [checks.tar.gz](checks.tar.gz). Their timings and generated fixture values are not benchmark results. Reproduce tests in the driver environment:

```bash
"$driver_python" benchmarks/test_analyse_pyperformance_abba.py
```

The method and eventual real-data command are in the [campaign protocol](../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md).
