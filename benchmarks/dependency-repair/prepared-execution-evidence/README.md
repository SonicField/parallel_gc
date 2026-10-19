# Prepared ABBA execution verification — 19 October 2026

The existing official runner now separates prepared dependency execution from upstream dependency installation. Collector code, the pyperformance submodule, its 100 default programs, and workload parameters are unchanged. This permits rigorous comparisons with the previously verified Python 3.16 repairs instead of reinstalling incompatible original pins.

The retained [archive](checks-and-smokes.tar.gz) contains the failing tests before implementation, ten passing tests after implementation, the existing parent test logs, and all four original `telco` source-ABBA smoke campaigns (GIL/FT × enabled/disabled). Archive SHA-256: `f390d80ccdc83d7c70be51626842e3b5727771de3d184341cfb501b1c96fa174`.

The new tests check original selection and rigorous options, executable identity, no installer call, both required prepared environments, compiled/runtime GIL metadata, active hooks, and failure retention without a passing partial suite. All ten pass in the pyperformance driver environment. Existing parent tests pass on both frozen integrated binaries: 76 tests each, with one FT-only skip on GIL and none on FT.

All 16 original `telco` smoke invocations pass. These use `--debug-single-value` and establish execution only; their timings are not performance evidence. Each campaign retains its command inputs, target hashes, source records, dependency records and raw results. Parent runner changes were uncommitted during these smokes; campaign provenance records that state honestly.

The frozen PGO+LTO sources are baseline `c67363fa59543ef5d572383af927f1cff88514a1` and integrated `388fd5bb46fdda6b464db566faf818505c3d6eef`. Dependency and complete 100-program readiness evidence is [recorded separately](../full-readiness-evidence/README.md). The latest CI-tested source is not being claimed as the source of these binaries. Hosted CI successes predate this runner integration; the new execution option has been tested locally, not yet on hosted CI.

Reproduce unit checks from the parent repository:

```bash
"$driver_python" benchmarks/test_prepared_pyperformance.py
```

Reproduce workload execution with the prepared source-ABBA command in [PERFORMANCE.md §2.1](../../../docs/PERFORMANCE.md#21-pyperformance-abba), selecting `--benchmarks telco --run-style debug` and a fresh output directory for the smoke. Use `default` and `rigorous` for measurements.
