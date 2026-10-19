# First complete rigorous suite — partial campaign checkpoint

Captured on 19 October 2026; verification completed at 23:33:07 UTC. This is only leg 1 of the GIL disabled source-ABBA campaign, not a completed comparison. All sixteen required suites remain part of the overall protocol; this checkpoint does not reduce that scope.

The baseline suite completed all 100 original programs and contains exactly 127 named results. Revalidation of the saved suite requires the requested collector state, compiled/runtime GIL state and positive hook entries in every run. It passes. The suite contains 5,004 measured run records and 15,852 measurement values. Those are repeated within-leg measurements, not 5,004 independent source comparisons or necessarily distinct operating-system processes.

Baseline source is `c67363fa59543ef5d572383af927f1cff88514a1`; the frozen GCC 11.5 ARM64 PGO+LTO binary and prepared dependencies are identified in the retained input fingerprints and execution record. No dependency installer ran. The campaign has started its first integrated-source GIL disabled leg; no source effect is calculated from this baseline alone.

[evidence.tar.gz](evidence.tar.gz) preserves the combined raw suite, all 100 per-program files, execution/dependency record, original input fingerprints, package inventories, parent launch revision and verification output. It also preserves a log snapshot captured while the next leg had started; that snapshot includes candidate preparation/startup and is not proof of a complete candidate leg. Files remain at their working locators as well; none were removed.

Identities:

- Archive SHA-256: `562c78089277cb4ac1d8bc6590be79201f6b003f055f2f3cb0044390dc2db792`.
- Combined baseline suite SHA-256: `d26bf288a046328e8a184789f162b0573a681c682f579921d6df1cc16e29972a`.

The extracted combined-suite digest was compared with the working file, and the archive passes gzip integrity verification. These are local worker preservation checks, not independent audit or backup claims. [Full protocol](../../../../../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md).
