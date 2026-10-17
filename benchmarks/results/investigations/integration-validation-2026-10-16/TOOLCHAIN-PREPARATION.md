# Pyperformance Rust preparation

## Observed failure

GIL enabled binary ABBA's initial default-suite environment creation failed before its first measurement. The dependency chain is `fastapi==0.121.0` → `pydantic==2.14.1` → `pydantic-core==2.50.1`. Pip selected a source distribution for this Python 3.16 AArch64 target. Maturin reported Rust missing and invoked puccinialin's download of `rustup-init` from `static.rust-lang.org`; the HTTP client failed with network unreachable. The full log remains at the campaign root under `results/pyperformance/gil-enabled.log`.

The original controller continues its remaining attempts. A subsequent existing target environment is only partially prepared; its existence is not proof that every default benchmark dependency or hook is ready. Neither a prepared Python executable nor a Rust version string establishes completion of the requested suites.

## Isolated toolchain obtained

Neither `command -v rustc` nor `command -v cargo` found a compiler. Known system and user-Cargo locations also lacked it. Cached configured repository metadata lists Rust and Cargo `1.97.1-3.el9` for AArch64.

Created `/tmp/parallel-gc-rust-toolchain-20261017-TtLNUp` with separate `rpms/`, `prefix/` and wrapper `bin/` directories. A cache-only download attempt failed because those packages were not already downloaded. The subsequent normal download used the same configured repositories and existing metadata:

```bash
dnf -q --setopt=metadata_expire=-1 download --resolve \
  --destdir /tmp/parallel-gc-rust-toolchain-20261017-TtLNUp/rpms \
  rust-1.97.1-3.el9 cargo-1.97.1-3.el9
```

This downloaded three packages, with no system installation or repository-setting change. `rpm -K` reports digests and signatures OK for all three. Their SHA-256 values are:

| Package | SHA-256 |
|---|---|
| cargo-1.97.1-3.el9.aarch64.rpm | `de2940feb2ddc5adec16fae9fb8d2a557035a8b7a53e056a273ca1d704876fc6` |
| rust-1.97.1-3.el9.aarch64.rpm | `5b65f20bd6238119f6bde221299cdb8fd9d614ab84daa366eb2ea2ad72f96af0` |
| rust-std-static-1.97.1-3.el9.aarch64.rpm | `52f314cb4588276ac7f1316a9986c9e44aa4b8efa3607625107b3a379f5d58c1` |

Extracted each package into the owned prefix using `rpm2cpio` and `cpio -idm --no-absolute-filenames`, with pipe failures checked. The relocated compiler initially could not locate `librustc_driver`; its wrapper sets `LD_LIBRARY_PATH` only for the compiler subprocess. Cargo's wrapper sets an owned `CARGO_HOME` cache. Future preparation should put this wrapper directory before the extracted executable directory on PATH. It must not add Rust libraries to the Python measurement process's loader path.

Compiler reports `rustc 1.97.1 (8bab26f4f 2026-07-14) (Red Hat 1.97.1-3.el9)` and relocated sysroot `.../prefix/usr`. Cargo reports `1.97.1 (c980f4866 2026-06-30) (Red Hat 1.97.1-3.el9)`. A tiny standalone Rust program compiled on CPU 32 and ran successfully, printing `isolated Rust toolchain works`. The temporary probe, compiler wrapper, packages, and both download logs are retained. This verifies a relocated compiler and standard library, not that pydantic-core or all benchmark dependencies build.

## Next falsifiable step

After the current controller's attempts finish, use the isolated toolchain to prepare the exact resolved pydantic-core dependency in an owned environment for a real target binary. Success requires the build and native import to finish; a version probe alone is insufficient. Preserve Cargo/network/PyO3 errors and check FT runtime GIL state after native imports. Do not change dependency versions or omit default benchmarks to make the attempt pass.

Then prepare and verify every default workload for all four target binaries before fresh rigorous ABBA campaigns. Preserve the initial failed/partial attempt separately; do not merge its measurements with the corrected preparation. All four enabled/disabled × GIL/FT source ABBAs remain required. No competing compile or benchmark campaign should run during timed comparisons.
