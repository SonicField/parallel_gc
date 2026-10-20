# Second complete rigorous suite — partial campaign checkpoint

Verification completed at 01:31:42 UTC on 20 October 2026. This is leg 2, the first integrated-source leg of the GIL disabled source-ABBA campaign. It is not a complete comparison and does not replace the remaining fourteen suites in the overall protocol.

All 100 original programs completed, producing 127 named results. Every saved run passes the requested collector-state, compiled/runtime GIL-state and positive-hook-entry checks. The result names and recorded work match the preserved baseline suite exactly. This leg contains 5,004 measured run records and 15,852 measurement values; those counts do not establish independent source replications.

The integrated source is `388fd5bb46fdda6b464db566faf818505c3d6eef`. The frozen GCC 11.5 ARM64 PGO+LTO binary, original workload inputs and prepared dependencies are identified in the preserved fingerprints and execution record. No dependency installer ran. The second integrated-source leg has started; neither a complete ABBA comparison nor a speed improvement is claimed here.

[evidence.tar.gz](evidence.tar.gz) preserves the raw combined suite, all 100 original-program result files, execution/dependency record, input fingerprints, package inventories, launch revision and verification output. Its log is a snapshot captured after leg 3 started; it includes that startup but does not prove leg 3 completion. Working copies remain; nothing was removed.

Identities:

- Archive SHA-256: `58529dda6972a7573f2f559c6b5ef539867c719448faa9aa9be701e935bf0055`.
- Integrated suite SHA-256: `e2a4872f229e06ab8d07b8dcc3bf307307b10d5c8e07a9b8e6e4caff352f46fb`.

The extracted suite digest matches the working suite, and the archive passes gzip integrity verification. These are local worker preservation checks, not an independent audit or backup claim. [Baseline checkpoint](../first-complete-leg/README.md); [full protocol](../../../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md).
