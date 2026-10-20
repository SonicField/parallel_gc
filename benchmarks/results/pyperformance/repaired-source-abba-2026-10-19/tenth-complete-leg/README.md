# Tenth complete rigorous suite — partial campaign checkpoint

Verification completed at 17:15:10 UTC on 20 October 2026. This is leg 2, the first integrated-source leg of the FT disabled source-ABBA campaign. Ten of sixteen required suites are complete. The complete FT-disabled comparison still requires its second integrated and final baseline legs.

All 100 original programs produced 127 named results. Names, recorded work and package/direct-URL inventories match the [FT-disabled baseline](../ninth-complete-leg/README.md). Every saved run passes compiled FT, runtime GIL-disabled, collector availability, positive-hook-entry and explicit Boolean collector-disabled checks. All original-program digests match the execution record. There are 5,004 measured run records and 15,852 values, not independent source replications.

Frozen integrated source is `388fd5bb46fdda6b464db566faf818505c3d6eef`. GCC 11.5 ARM64 PGO+LTO binary, original workload and prepared FT dependency identities are recorded in the retained campaign-start fingerprints and execution record. No dependency installer ran. The second integrated FT-disabled leg is running; the after-campaign fingerprint check remains pending until all four legs finish.

[evidence.tar.gz](evidence.tar.gz) preserves the complete raw suite, all original-program files, execution/dependency record, fingerprints, package inventories, launch revision, verification output and log snapshot. The snapshot includes the next integrated leg's startup, not completion. These same runs will appear in the final campaign archive, not as additional replications. All working files remain.

Identities:

- Archive SHA-256: `6c7f8a935d022173a890e275c85c9f179880ab68b15d6b675ef0067cfa142825`.
- Suite SHA-256: `927f1c388d0b722274480fd18ad9c5abc131916b4c4ad5747004c2165f8f63ba`.

Gzip integrity passes and the extracted suite digest matches. These are local worker checks, not independent audit or backup claims. [Full protocol](../../../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md). No complete FT performance result or VP-conformance verdict is claimed here.
