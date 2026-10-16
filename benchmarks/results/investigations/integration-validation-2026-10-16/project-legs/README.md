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

## GIL leg 2: candidate

[Complete measurement data](gil-2-candidate.json).

- CPython source: `388fd5bb46fdda6b464db566faf818505c3d6eef`, recorded clean.
- Recorded parent checkpoint: `cc2a489e937458f2271064fc88e81f8adf1ee517`.
- Launcher timestamps: 16 October 2026, 19:13:04 to 20:34:28 UTC.
- All eight sustained and sixteen controlled comparisons have five samples per arm. Configuration and placement match leg 1; actual controlled object-count sequences match both serial and parallel baseline sequences.
- Original scratch-file SHA-256: `8fcfb72ff61db94e451334b26433daf61e60a108cd56ff7693c9fabbd4906d24`.
- Git-copy SHA-256: `1fae162956f2ab00f8ba43b085ed2af1eef3bc751d829e450bc7e71a586cf877`.

The original has 65,736 bytes; the Git copy adds only its terminal newline, giving 65,737 bytes. Its original-length prefix was byte-compared against the original. The parent checkpoint changed only through documentation/analysis additions; the launcher's three measured-code/preflight fingerprints passed again between legs.

Candidate leg 3 is running; it and baseline leg 4 are required before the GIL source comparison can be analysed. All four FT legs and the separate pyperformance campaigns also remain required. No acceptance or performance-neutrality verdict follows from these first two legs.
