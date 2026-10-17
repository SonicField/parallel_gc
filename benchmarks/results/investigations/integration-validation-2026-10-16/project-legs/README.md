# Corrected full-project campaign legs

These are complete individual invocations of the unchanged full project suite. The four GIL legs form a complete source ABBA; FT currently has only its first leg. Only combine legs from the corrected four-build campaign. Do not substitute data from the earlier builds without native decimal.

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

## GIL leg 3: candidate

[Complete measurement data](gil-3-candidate.json).

- CPython source: `388fd5bb46fdda6b464db566faf818505c3d6eef`, recorded clean.
- Recorded parent checkpoint: `bf5e87076deb8c415ddc5425587aa7a5456c64cf`.
- Launcher timestamps: 16 October 2026, 20:34:28 to 21:55:51 UTC.
- All eight sustained and sixteen controlled comparisons have five valid samples per arm. Configuration, placement and actual controlled object-count sequences match baseline leg 1.
- Original scratch-file SHA-256: `a3005d0b47fd48637f70fb61d964195a56523855e6773e4fdbc00ed64ebd54ae`.
- Git-copy SHA-256: `448c84a99f67365f5bea91beaccb9ff611735c17f261c8c696031ecb1ae48445`.

The original has 65,677 bytes; the Git copy adds only its terminal newline, giving 65,678 bytes. Its original-length prefix was byte-compared against the original. The measurement/preflight fingerprints passed again between legs.

## GIL leg 4: baseline

[Complete measurement data](gil-4-baseline.json).

- CPython source: `c67363fa59543ef5d572383af927f1cff88514a1`, recorded clean.
- Recorded parent checkpoint: `da42aa1891d765fe8eef413095bc6f9caa9d805e`.
- Launcher timestamps: 16 October 2026, 21:55:51 to 23:17:25 UTC.
- Complete four-leg validation passes: source order, standard configuration, build mode, placement, all workloads, five samples per arm and matching generated-member counts.
- Original scratch-file SHA-256: `874e92e008a4d369e77c83810b24aee8769db00aa1731f196b34a66fcd70337b`.
- Git-copy SHA-256: `1534bffedd0009bff2f81ec27eb880e6722e7c78eb7aaab3d69089c85673f4a5`.

The original has 65,727 bytes; the Git copy adds only its terminal newline, giving 65,728 bytes. Its original-length prefix was byte-compared against the original. The measurement/preflight fingerprints passed again before FT began.

The full GIL source ABBA is now complete. See [results and interpretation](../GIL-PROJECT-RESULTS.md) and [all analysis rows](../gil-source-analysis.json). Completing the measurement does not establish performance neutrality or release acceptance. Four FT legs, separate pyperformance campaigns and current hosted CI verification remain required.

## FT leg 1: baseline

[Complete measurement data](ft-1-baseline.json).

- CPython source: `c67363fa59543ef5d572383af927f1cff88514a1`, recorded clean.
- Recorded parent checkpoint: `3f7de2f28ba541dbe55aae39e4fa4da2604c4c1e`, recorded dirty while the closing GIL data/writeup was being prepared. This metadata is preserved; it is not relabeled as a clean parent checkpoint. The project benchmark, launch driver and preflight fingerprints remained unchanged.
- Launcher timestamps: 16 October 2026, 23:17:25 to 17 October, 00:51:50 UTC (94 minutes 25 seconds).
- All eight sustained and sixteen controlled comparisons contain five finite, nonnegative samples per arm. Standard configuration, clean baseline CPython content, compiled FT flags, affinity 0–31 and the established NUMA policy pass inspection. Each controlled serial/parallel pair has identical positive generated-member counts.
- Original scratch-file SHA-256: `9f5d9415fc1c7326db5c9c2d630e1caa659790d8153247b873cb2ec4f5aeca67`.
- Git-copy SHA-256: `66f1d4a98ffe2fdad4854a92073c9f8ccb00327ccfcf2a93e3819309b9480681`.

The original has 65,646 bytes; the Git copy adds only its terminal newline, giving 65,647 bytes. Its original-length prefix was byte-compared against the original. The controller checked all three initial measurement/preflight fingerprints and the subsequently frozen pyperformance hook, then started candidate FT leg 2. The project suite does not use that hook.

This is one FT leg, not a source comparison. The analysis command refuses the incomplete campaign because candidate leg 2's result is absent. Three more FT legs remain required. Inspection also exposed a spelling mismatch in the separate analysis tool's artificial FT fixture: the real harness records `free-threaded`, not the launcher's `ft` label. That analysis-only correction must be tested separately; do not change measured metadata or benchmark code to satisfy the analyser.

## FT leg 2: candidate

[Complete measurement data](ft-2-candidate.json).

- CPython source: `388fd5bb46fdda6b464db566faf818505c3d6eef`, recorded clean.
- Recorded parent checkpoint: `68e32f522427bf34ab19990c8482e3038d3a5018`, recorded dirty during the preceding leg's evidence work. Preserve the dirty metadata; the project benchmark and all four controller fingerprints remained unchanged.
- Launcher timestamps: 17 October 2026, 00:51:50 to 02:27:00 UTC (95 minutes 10 seconds).
- All eight sustained and sixteen controlled comparisons contain five valid samples per arm. Standard configuration and affinity/NUMA placement match FT baseline leg 1; all controlled generated-member count sequences match baseline in both serial and parallel arms.
- Original scratch-file SHA-256: `fcb25415eff9be92519b6117b6c69b9467ee1ab7ebd3bf6fc16f6081c9496757`.
- Git-copy SHA-256: `8de3ad44de718ef803f365744c7366b4211fb28eb10ba241ac99ad60efdc9d33`.

The original has 65,695 bytes; the Git copy adds only its terminal newline, giving 65,696 bytes. Its original-length prefix was byte-compared against the original. The controller checked all four fingerprints and started the second candidate FT invocation, leg 3. The analysis command still refuses the incomplete campaign because that result is absent. The initial FT source pair supplies only the first ABBA half; two closing legs remain required before a source-effect report.

## FT leg 3: candidate

[Complete measurement data](ft-3-candidate.json).

- CPython source: `388fd5bb46fdda6b464db566faf818505c3d6eef`, recorded clean.
- Recorded parent checkpoint: `67658cbe7993ad168e98bc6532bf17cb8625a13f`, recorded dirty during preceding evidence work. The dirty metadata is retained; the project implementation and four controller fingerprints remained unchanged.
- Launcher timestamps: 17 October 2026, 02:27:00 to 04:03:07 UTC (96 minutes 7 seconds).
- All eight sustained and sixteen controlled comparisons contain five valid samples per arm. Configuration, placement and generated-member count sequences match FT baseline leg 1.
- Original scratch-file SHA-256: `ef4a0e6d31b9204f6cd438dff441257538756cd54442157467289e0778827e4e`.
- Git-copy SHA-256: `eefa804e31d4bd9964b05d4faf39818658dcb606ea8f26778f19fcb58d3b562e`.

The original has 65,667 bytes; the Git copy adds only its terminal newline, giving 65,668 bytes. Its original-length prefix was byte-compared against the original. The controller checked all four fingerprints and started closing baseline FT leg 4. Three legs are not a complete source ABBA; the analysis command still refuses the missing closing result.
