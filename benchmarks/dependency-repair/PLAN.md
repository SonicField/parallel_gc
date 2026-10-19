# Python 3.16 benchmark dependency repair

Status: in progress, authorised 19 October 2026.

Purpose: run the complete pyperformance selection against baseline and current GIL/FT builds without dependency failures. CPython, benchmark programs, workload parameters and GC policy remain unchanged.

Method: [Verifiable Practice](https://github.com/SonicField/verifiable-practice). Preserve the original failure evidence in `../results/investigations/integration-validation-2026-10-16/default-runtime-compatibility/`.

## Steps and verification

1. Reproduce each failure in a new isolated environment. Prefer a compatible published release; where none exists, retain a small dependency-only patch with tests and provenance. Commit each repair separately.
2. Cloudpickle: test global loads, stores, deletion, closures and nested code through a serialization round trip. Removing an unavailable opcode must not lose global-name discovery.
3. Genshi: test expression compilation and both original XML/text template workloads. Verify AST fields and source locations survive cloning. A successful import alone is insufficient.
4. Coverage, Dulwich, MarkupSafe and Greenlet: build compatible native releases for Python 3.16 and test their actual benchmark operations. Check that FT remains GIL-disabled after importing and executing each extension. Do not force GIL-disabled execution of unsupported extensions or substitute a different workload.
5. Prepare fresh baseline/current environments with identical dependency pins and patch hashes. Check package consistency, selected program names, native module paths and worker runtime attestations. Keep historical environments untouched.
6. Run all 100 selected programs in all eight baseline/current × GIL/FT × enabled/disabled contexts as correctness/readiness checks. Do not describe these short runs as performance results.
7. Only after readiness passes, run the complete rigorous ABBA comparisons with the existing optimized binaries and original workload settings. Record commands, package inventories, hashes, failures and numerical results.

## Progress

- 19 October: isolated workspace `/tmp/parallel-gc-dependency-repair-20261019-uMnz4R`; historical benchmark environments unchanged.
- Available releases checked: Genshi 0.7.11, Cloudpickle 3.1.2, Coverage 7.16.2, Dulwich 1.2.17, MarkupSafe 3.0.4, Greenlet 3.5.6. These are candidates, not validated repairs.
- Genshi 0.7.11 still fails constructing `ast.Expression` during template compilation. An upgrade alone does not repair it.
- Cloudpickle 3.1.2 is still the newest release in the configured package index. Its import references removed `DELETE_GLOBAL`.
- Cloudpickle repair verified: five tests pass on all four target binaries and Python 3.12; the original Dask benchmark passes eight short checks with FT GIL-disabled. See [CLOUDPICKLE.md](CLOUDPICKLE.md). Other dependencies and full-suite readiness remain pending.
- Greenlet 3.5.6 source declares FT support through `PyUnstable_Module_SetGIL(..., Py_MOD_GIL_NOT_USED)`. Native build and runtime checks remain required.
- Genshi repair verified while retaining 0.7.7: eight tests pass on all four target binaries and Python 3.12; XML/text benchmarks pass eight short checks (sixteen workload results), with FT GIL-disabled. See [GENSHI.md](GENSHI.md).
- Coverage 7.6.12 retains CTracer and passes four native probes plus eight original benchmark checks. Newest 7.16.2 was rejected because it defaults to SysMonitor. See [COVERAGE.md](COVERAGE.md).
- MarkupSafe 3.0.4 passes four native probes and eight original Sphinx checks; Sphinx remains 7.3.7. See [MARKUPSAFE.md](MARKUPSAFE.md).
- Greenlet 3.5.6 passes four native probes including a context switch. SQLAlchemy's own 1.4 native extensions still enable the GIL; its two FT benchmark programs remain blocked. See [GREENLET.md](GREENLET.md).
- Dulwich 1.2.17 strict native builds pass four probes and eight original commit-walking benchmark checks. Optional pure-Python fallback was rejected. See [DULWICH.md](DULWICH.md).
- Decision required for SQLAlchemy: latest 1.4 native extensions also enable the GIL; 2.x removes APIs used by the original imperative workload. A supported pure-Python 1.4 build would preserve benchmark code but change its implementation. Not executed without agreement. See [SQLALCHEMY.md](SQLALCHEMY.md).
- Final checks: all 48 retained workload records have the requested GC mode and active hook metadata; every FT record reports GIL-disabled execution. All four optimized binary hashes match the original manifests. The existing 75-test parent selection passes on each binary (one FT-only skip in each GIL run), using the dedicated test environments documented in the earlier hook evidence.
- An additional harness invocation in the measurement environments failed because an installed top-level `benchmarks` package masked this repository's namespace. Direct support-script execution passed; the complete selection then passed using the existing dedicated test-environment recipe. No test or source change was made to conceal that invocation error.
- Current status: six dependency repairs verified and separately committed; fresh complete measurement environments, repeated all-program readiness and rigorous comparisons await the SQLAlchemy decision. Historical measurement environments, CPython, benchmark workloads and parameters remain unchanged.
- Subsequent approval: Alex authorised SQLAlchemy's supported pure-Python implementation across both sources and build modes. Zero-extension, version, actual-workload row-count and FT runtime checks pass on all four binaries; both original SQLAlchemy programs pass sixteen short checks. All seven repairs are now verified individually; complete prepared-environment readiness is next.
