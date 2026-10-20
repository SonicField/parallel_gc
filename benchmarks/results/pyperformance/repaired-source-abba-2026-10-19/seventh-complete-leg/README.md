# Seventh complete rigorous suite — partial campaign checkpoint

Verification completed at 11:02:58 UTC on 20 October 2026. This is leg 3, the second integrated-source leg of the GIL enabled source-ABBA campaign. Seven of sixteen required suites are complete. The final enabled baseline leg is running; no complete enabled comparison is claimed here.

All 100 original programs produced 127 matching named results. Names, recorded work and package/direct-URL inventories match the [enabled baseline](../fifth-complete-leg/README.md). Every saved run passes compiled/runtime GIL, collector availability, positive-hook-entry and explicit Boolean enabled-state checks. All original-program digests match the execution record. There are 5,004 measured run records and 15,852 values, not independent source replications.

Frozen integrated source is `388fd5bb46fdda6b464db566faf818505c3d6eef`. The GCC 11.5 ARM64 PGO+LTO binary, original workloads and dependency identities are recorded in the retained campaign-start fingerprints and execution record. No dependency installer ran. The after-campaign fingerprint check remains pending until the final baseline leg finishes.

[evidence.tar.gz](evidence.tar.gz) preserves the complete raw suite, all original-program files, execution/dependency record, fingerprints, package inventories, launch revision, verification output and log snapshot. The snapshot includes the next baseline leg's startup, not its completion. Working files remain. These same runs will appear in the completed campaign archive, not as additional replications.

Identities:

- Archive SHA-256: `9c47e56852c01ce0e56bb9353e021d7071978d7c101d4e28e1f9cfab60e18d39`.
- Suite SHA-256: `2fa8556a759f758a590e508d58b5d70db5e4d3893a8b436c98e7c0dce7eb1bbc`.

Gzip integrity passes and the extracted suite digest matches. These are local worker checks, not independent audit or backup claims. [Full protocol](../../../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md); [completed GIL-disabled comparison](../gil-disabled/README.md).
