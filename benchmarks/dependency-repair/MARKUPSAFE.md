# MarkupSafe native FT compatibility

Use **MarkupSafe 3.0.4**, built from source for both GIL and FT Python 3.16. The original 2.0.1 `_speedups` extension enables the GIL in FT. The new extension preserves GIL-disabled execution and passes an escaping correctness check on all four baseline/current binaries.

The **unchanged Sphinx 7.3.7 benchmark** passes all eight enabled/disabled checks, including the FT worker attestations. No Sphinx version, workload or parameter was changed. Raw output and native probes are in [markupsafe-evidence](markupsafe-evidence/); the original failing native probe is retained there too. These short runs are correctness checks, not performance evidence.

Build using each target Python:

```bash
"$target_python" -m pip wheel --no-cache-dir --no-deps \
  --no-binary=markupsafe --wheel-dir "$wheel_directory" markupsafe==3.0.4
```

Install the same mode-specific native wheel on baseline/current. Verify `_speedups` is an extension and FT remains GIL-disabled using [test_native_dependencies.py](test_native_dependencies.py).

Tested wheel SHA-256:

- GIL: `a06a291472172add31ee9e7b24933152802cc8c4fa25d6270ae717b64b9e6dfb`.
- FT: `3c51a6a7de6d7fa1fae41c37cd5d13c1663114c5b2011eb2fee990b2e59a8946`.

New comparison sides must use the same MarkupSafe version. Do not mix these measurements with historical Sphinx runs using 2.0.1.
