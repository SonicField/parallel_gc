# Dulwich native FT compatibility

Use **Dulwich 1.2.17**, built with native extensions for both GIL and FT Python 3.16. The original 0.20.23 `_objects` extension enables the GIL in FT. The replacement passes all four native probes with FT GIL-disabled. The **unchanged original commit-walking benchmark and its repository data** pass all eight enabled/disabled checks.

Raw benchmark results, probes, build logs and the original failure are in [dulwich-evidence](dulwich-evidence/). These short checks are correctness evidence, not performance measurements.

## Require the native build

The first wheel build succeeded but contained **no native extensions**: Dulwich permits optional extension-build failures. That wheel was rejected. Require extensions with `CIBUILDWHEEL=1`, and independently check the installed `_objects` module with [test_native_dependencies.py](test_native_dependencies.py).

The old owned Rust prefix had no compiler executable, and the old Cargo cache contained directories with missing manifests. The strict builds first failed for those two reasons. Fresh isolated RPM extraction and a fresh Cargo cache resolved them; the historical tooling directories were not repaired or modified by extraction.

With an isolated Rust toolchain on `PATH` and its libraries available:

```bash
CIBUILDWHEEL=1 \
  "$target_python" -m pip wheel --no-cache-dir --no-deps \
  --no-binary=dulwich --wheel-dir "$wheel_directory" dulwich==1.2.17
```

Do not set `PURE` or accept a wheel without its extensions. Use the same mode-specific wheel on baseline/current. No CPython, benchmark source, repository input or GC policy change is required.

## Provenance

- Rust compiler: 1.97.1, Red Hat package `1.97.1-3.el9`, extracted from retained owned RPMs into the new dependency workspace.
- GIL wheel SHA-256: `ea3615d0ff34f8a67aa6b55aebc3acbe8d19216efb7d4b0e7aea6270b77a101f`.
- FT wheel SHA-256: `5dac2bf3ce3946071967907fe440883fd588eb25bd7df5c50f12db6d87080361`.
- Fresh native build logs are `dulwich-strict-ft-fresh-cache.log.gz` and `dulwich-strict-gil-build.log.gz`. Earlier strict failures are retained separately.

The dependency implementation changed from the historical release. New comparisons must use the same Dulwich version and build on both sides; do not combine them with historical 0.20.23 benchmark timings.
