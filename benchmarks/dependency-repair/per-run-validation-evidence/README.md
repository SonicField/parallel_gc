# Rigorous per-run metadata validation

The first rigorous workload exposed a validation error, not a hook failure. `2to3` completed 41 original runs. Calibration recorded four hook entries and every measured run recorded three. pyperf's benchmark-level metadata keeps only common fields, so the varying count was absent there. The original new validator incorrectly rejected that absence.

Validation now reads every run's metadata and requires a positive integer hook count and correct compiled/runtime GIL and collector availability. Counts need not be equal. Workloads, hooks, dependencies and rigorous parameters are unchanged. Twelve tests pass; the new positive control failed before the correction, and a single missing/zero-count run still invalidates a suite. The original rigorous `2to3` result passes the corrected validator.

[Retained evidence](attempts-and-tests.tar.gz) includes all three stopped launch directories, raw `2to3` results and logs, before/after unit tests, and original-result revalidation. No full ABBA campaign completed in those attempts. The isolated timing is not used as a comparative performance result. Fresh measurements run under the [recorded full protocol](../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md).
