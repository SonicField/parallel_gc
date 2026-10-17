# Failed attempt and native-dependency repair

The first pyperformance GIL enabled preparation failed before any suite. Its complete log is `gil-enabled.txt`, byte-identical to the original 24,769-byte scratch log, SHA-256 `1032172f986d5008c4cfd627daeb0ea7f598acc2aefc0354102b8d0ede272670`.

The following GIL disabled invocation reused the partial target environment, retried the 100 selected default programs' dependencies, marked FastAPI “benchmark will be skipped,” then started timing other programs. Inspection of the pinned pyperformance `run.py` and `commands.py` confirms such a skipped dependency is a recorded error and ultimately gives a failing CLI exit, not a complete suite. Continuing these timings could not satisfy the promised default workload coverage.

At 05:43:54 UTC on 17 October, stopped only the dedicated owned campaign process group 3947716 after checking every member: launcher, campaign driver, pyperformance manager and its benchmark children. Subsequent process listings confirm that group is gone. The initial GIL enabled failure is terminal; the GIL disabled attempt is interrupted and incomplete, not a completed ABBA. FT pyperformance attempts did not start. No files were removed, no source/benchmark parameters changed, and all eight project legs remain valid and separately preserved.

The complete interrupted log is `gil-disabled.txt`. The original is 360,288 bytes, SHA-256 `21a98e558d311ffad8cdc3d696469f6a34261467baa4521fc799c38a4a136f57`; the Git copy adds only its terminal newline, giving 360,289 bytes and SHA-256 `03228729b5c60d8c86f8f7baa9a6dec534146a0de3b5e767600168c9f093c7fb`. Its original-length prefix matches byte-for-byte. It records the FastAPI dependency failure, one completed 2to3 result and interrupted argparse timing. Those partial timings are not included in a performance comparison. Both original pip logs contain whitespace-only lines; they are intentionally preserved rather than reformatted, so whitespace checks report those raw lines. Source and prose checks exclude the two raw log files.

## Native repair checks

Using the [isolated Rust toolchain](../TOOLCHAIN-PREPARATION.md), built the exact resolved `pydantic-core==2.50.1`, without changing that dependency version or forcing a Python/PyO3 compatibility setting:

- GIL wheel: `pydantic_core-2.50.1-cp316-cp316-linux_aarch64.whl`, SHA-256 `abd6c15924ff9184fa484fdf6497f70554b336a402905415dc9250363127e53d`.
- FT wheel: `pydantic_core-2.50.1-cp316-cp316t-linux_aarch64.whl`, SHA-256 `225c878b7bbe4b4ffb6a7cabaf8165f9ad1d90ee532cc9e0efa5304d56196886`.

Build logs are preserved here; native wheels remain in the owned toolchain directory and pip's normal wheel cache. Separate test environments for each of the four real baseline/candidate × GIL/FT binaries install the matching wheel and unchanged FastAPI/httpx/uvicorn versions. The retained `native_probe.py` imports native dependencies and exercises an actual FastAPI test-client request and pydantic schema validation. All four requests return the expected value 42, the core module is native, and both FT interpreters still report GIL disabled. The four JSON probe results retain executable, module and package versions. No benchmark timing is collected by this probe.

This establishes repair of the observed native dependency failure on all four binaries. It does not establish that every default dependency installs, every benchmark works, or the full requested campaigns finish. Fresh complete preparation and all sixteen rigorous suites remain required. Failed/partial attempts must not be merged into them.
