# Corrected full-project campaign legs

These are complete individual invocations of the unchanged full project suite, not yet a complete source ABBA. Only combine legs from the corrected four-build campaign. Do not substitute data from the earlier builds without native decimal.

## GIL leg 1: baseline

[Complete measurement data](gil-1-baseline.json).

- CPython source: `c67363fa59543ef5d572383af927f1cff88514a1`, recorded clean.
- Recorded parent checkpoint: `5440ac284672a631ffcdb5ef6a32544967fd2c45`.
- Launcher timestamps: 16 October 2026, 17:51:41 to 19:13:04 UTC.
- Eight sustained comparisons and sixteen controlled comparisons, with five samples per serial/parallel arm. Standard parameters and recorded CPU affinity passed inspection; controlled object counts match within each serial/parallel pair.
- Original scratch-file SHA-256: `81a75027d92b1c8840ab7d5f40c58c1148c04db9fb44ae994baefdfdaad92f4a`.
- Git-copy SHA-256: `4db50e09e32292610d64e7a889d8b8e9fee63666b22ffe6120ecc3b60b382a19`.

The original JSON has 65,758 bytes and no terminal newline. The Git copy has 65,759 bytes; only the final newline is added. Its original-length prefix was byte-compared against the original. This difference changes the file hash, not the recorded measurements.

Candidate leg 2 is running; legs 3 and 4 are required before the GIL source comparison can be analysed. All four FT legs and the separate pyperformance campaigns also remain required. No acceptance or performance-neutrality verdict follows from this individual leg.
