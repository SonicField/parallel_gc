# Fifth complete rigorous suite — partial campaign checkpoint

Verification completed at 07:13:29 UTC on 20 October 2026. This is leg 1, baseline source, of the GIL enabled source-ABBA campaign. Five of sixteen required suites are complete. Only the earlier GIL-disabled campaign has a complete four-leg comparison.

All 100 original programs produced the expected 127 named results. Result names and recorded work match the completed GIL-disabled baseline. Every saved run passes compiled/runtime GIL, collector availability and positive-hook-entry checks; explicit Boolean enabled-state metadata also passes. All 100 original-program file digests match the execution record. There are 5,004 measured run records and 15,852 values, not independent source replications. No enabled-versus-disabled performance effect is inferred from this checkpoint.

The frozen baseline source is `c67363fa59543ef5d572383af927f1cff88514a1`. GCC 11.5 ARM64 PGO+LTO binary, original workload and dependency identities are retained in the campaign-start fingerprints and execution record. Initial and before-campaign fingerprints match; the after-campaign check cannot occur until all four legs finish. No dependency installer ran. The first integrated-source leg is running.

[evidence.tar.gz](evidence.tar.gz) retains the combined raw suite, all 100 original-program files, execution/dependency record, fingerprints, package inventories, launch revision, verification output and log snapshot. The snapshot also includes integrated-leg startup; it is not evidence of its completion. Working files remain and nothing was removed. These are the same actual runs that will appear in the final campaign archive, not additional replications.

Identities:

- Archive SHA-256: `76164bc427df03f3e097b6db913c35db78f820c42c9b273f6f8d20c86f6649ce`.
- Suite SHA-256: `701cbea84235c45a0958ae10d7542b126e9dc1b66125bb2f6f36891dc0910c91`.

Gzip integrity passes and the extracted suite digest matches the working suite. These are local worker preservation checks, not independent audit or backup claims. [Completed GIL-disabled comparison](../gil-disabled/README.md); [full protocol](../../../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md).
