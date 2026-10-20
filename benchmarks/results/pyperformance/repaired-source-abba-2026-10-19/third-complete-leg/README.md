# Third complete rigorous suite — partial campaign checkpoint

Verification completed at 03:22:40 UTC on 20 October 2026. This is leg 3, the second integrated-source leg of the GIL disabled source-ABBA campaign. Three of sixteen required suites are complete; this checkpoint is not a complete comparison.

All 100 original programs produced the expected 127 named results. Their names and recorded work match the baseline. Every saved run passes compiled/runtime GIL, collector availability and positive-hook-entry checks; explicit Boolean disabled-state metadata also passes. This leg contains 5,004 measured run records and 15,852 values, not independent source replications.

The integrated source is `388fd5bb46fdda6b464db566faf818505c3d6eef`. Frozen GCC 11.5 ARM64 PGO+LTO binary and dependency/workload inputs are identified in the retained fingerprints and execution record. No dependency installer ran. The final baseline leg of this GIL disabled ABBA has started; no four-leg result or performance effect is claimed yet.

[evidence.tar.gz](evidence.tar.gz) retains the combined raw suite, all 100 original-program results, execution/dependency record, fingerprints, package inventories, launch revision and verification output. Its log snapshot also includes final-baseline startup; that is not evidence of baseline completion. Working files remain; nothing was removed.

Identities:

- Archive SHA-256: `2fb3363fe3222b2ca68a1805e02effd1c4ebef9a54262cc0ddb0db728d27970c`.
- Suite SHA-256: `f29c094d1fa3c8046b7f49c060339187eb6de4ac14250d4195ac6643de71dadd`.

The extracted suite digest matches the working suite and gzip integrity verification passes. These are local worker preservation checks, not independent audit or backup claims. [Earlier checkpoint](../second-complete-leg/README.md); [full protocol](../../../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md).
