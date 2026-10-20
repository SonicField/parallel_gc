# Sixth complete rigorous suite — partial campaign checkpoint

Verification completed at 09:08:33 UTC on 20 October 2026. This is leg 2, the first integrated-source leg of the GIL enabled source-ABBA campaign. Six of sixteen required suites are complete; no complete enabled comparison is claimed.

All 100 original programs produced 127 matching named results. Names, recorded work and package/direct-URL inventories match the [enabled baseline](../fifth-complete-leg/README.md). Every saved run passes compiled/runtime GIL, collector availability, positive-hook-entry and explicit Boolean enabled-state checks. All original-program digests match the execution record. There are 5,004 measured run records and 15,852 values, not independent source replications.

Frozen integrated source is `388fd5bb46fdda6b464db566faf818505c3d6eef`, not the later CI-tested source. The ARM64 GCC 11.5 PGO+LTO binary, original workloads and dependency identities are recorded in the retained campaign-start fingerprints and execution record. No dependency installer ran. The second integrated-source leg is running; the after-campaign fingerprint check remains pending until all four legs finish.

[evidence.tar.gz](evidence.tar.gz) preserves the complete raw suite, all 100 original-program files, execution/dependency record, fingerprints, package inventories, launch revision, verification output and log snapshot. The snapshot includes the next leg's startup, not its completion. Working files remain. These same runs will be included in the completed campaign archive; they are not extra replications.

Identities:

- Archive SHA-256: `edb4ecfe6e6543cf68c33b37786886c650908e98cfa67a9840a73946afe9ee30`.
- Suite SHA-256: `ffa88a6808ccccdf29c17a4ccba30b06aa7537a6a500bf8a1425d3a50e87e96e`.

Gzip integrity passes and the extracted suite digest matches. These are local worker checks, not independent audit or backup claims. [Full protocol](../../../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md); [completed GIL-disabled comparison](../gil-disabled/README.md).
