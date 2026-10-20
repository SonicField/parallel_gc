# Eleventh complete rigorous suite — partial campaign checkpoint

Verification completed at 19:21:34 UTC on 20 October 2026. This is leg 3, the second integrated-source leg of the FT disabled source-ABBA campaign. Eleven of sixteen required suites are complete. The final FT-disabled baseline leg is running; no complete FT comparison is claimed here.

All 100 original programs produced 127 named results. Names, recorded work and package/direct-URL inventories match the [FT-disabled baseline](../ninth-complete-leg/README.md). Every saved run passes compiled FT, runtime GIL-disabled, collector availability, positive-hook-entry and explicit Boolean collector-disabled checks. All original-program digests match the execution record. There are 5,004 measured run records and 15,852 values, not independent source replications.

Frozen integrated source is `388fd5bb46fdda6b464db566faf818505c3d6eef`. GCC 11.5 ARM64 PGO+LTO binary, original workload and prepared FT dependency identities are recorded in the retained campaign-start fingerprints and execution record. No dependency installer ran. The after-campaign fingerprint check remains pending until the final baseline leg finishes.

[evidence.tar.gz](evidence.tar.gz) preserves the complete raw suite, all original-program files, execution/dependency record, fingerprints, package inventories, launch revision, verification output and log snapshot. The snapshot includes final-baseline startup, not completion. These same runs will appear in the final campaign archive, not as additional replications. All working files remain.

Identities:

- Archive SHA-256: `5dc04275b43612167ad2b77c1d4ffbba4f5e6521b2cc600617abc7e37d243326`.
- Suite SHA-256: `969d09fac5d1c739a0eada497c7fdf6b7bf1b64254fc9f5a851715d26d3131e9`.

Gzip integrity passes and the extracted suite digest matches. These are local worker checks, not independent audit or backup claims. [Full protocol](../../../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md). No complete FT performance result or VP-conformance verdict is claimed here.
