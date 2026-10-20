# Ninth complete rigorous suite — partial campaign checkpoint

Verification completed at 15:08:55 UTC on 20 October 2026. This is leg 1, baseline source, of the FT disabled source-ABBA campaign. Nine of sixteen required suites are complete. Neither FT campaign has a complete comparison yet.

All 100 original programs produced 127 named results. Names and recorded work match the completed GIL-disabled baseline; that structural check is not a GIL/FT performance comparison. Every saved run passes compiled FT, runtime GIL-disabled, collector availability, positive-hook-entry and explicit Boolean collector-disabled checks. All original-program digests match the execution record. There are 5,004 measured run records and 15,852 values, not independent source replications.

Frozen baseline source is `c67363fa59543ef5d572383af927f1cff88514a1`. GCC 11.5 ARM64 PGO+LTO binary, original workload and prepared FT dependency identities are recorded in the retained campaign-start fingerprints and execution record. Initial and before-campaign fingerprints match; the after-campaign check remains pending until all four FT-disabled legs finish. No dependency installer ran. The first integrated-source FT-disabled leg is running.

[evidence.tar.gz](evidence.tar.gz) preserves the complete raw suite, all original-program files, execution/dependency record, fingerprints, package inventories, launch revision, verification output and log snapshot. The snapshot includes integrated-leg startup, not completion. These same runs will appear in the final campaign archive, not as additional replications. All working files remain.

Identities:

- Archive SHA-256: `173845da9c912baecf9788b41c838b912d6266857ae5bc01d7ae79e5e61f41e2`.
- Suite SHA-256: `33653a0aabfa8db93b77d0c36010d692a97b14a52b76a4b6d0bfe175f62609fd`.

Gzip integrity passes and the extracted suite digest matches. These are local worker checks, not independent audit or backup claims. [Full protocol](../../../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md); completed [GIL disabled](../gil-disabled/README.md) and [GIL enabled](../gil-enabled/README.md) comparisons.
