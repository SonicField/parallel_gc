# All-program runtime compatibility check

This is a diagnostic run, not a performance comparison. It executes the original 100-program default selection with the harness's existing `--run-style debug` (`--debug-single-value`). One value cannot establish throughput, latency, performance neutrality or long-run collector correctness. The planned sixteen rigorous suites remain required.

## Results

Eight checks ran sequentially from 07:56:57 to 08:23:48 UTC on 17 October, using the same four verified optimized binaries and prepared environments as the failed full attempt. Each selected all 100 programs; exact ordered attempt lists were compared with the [preserved inventory](../full-pyperformance-preparation/selected-workloads.txt). Every invocation exited 1. Failed programs and successful named result sets match between baseline and current and between enabled and disabled policies within each build mode.

| Builds and policies | Programs attempted per invocation | Failed programs | Successful named result entries per invocation |
|---------------------|-----------------------------------|-----------------|------------------------------------------------|
| Baseline/current GIL, enabled/disabled | 100 | Dask, Genshi | 124 |
| Baseline/current FT, enabled/disabled | 100 | Coverage, Dask, dulwich_log, Genshi, Sphinx, SQLAlchemy declarative, SQLAlchemy imperative | 119 |

Some programs generate several named results, so result-entry counts are not program counts. All 972 saved run records have checked compiled-mode, runtime-GIL and collector-policy metadata. Both modes include the FastAPI result. Failed-program timings are not present in the saved partial suites and are not treated as results. See [machine summary](summary.json) and the complete compressed logs and partial JSONs beside it.

The two shared Python API errors are detailed in [dependency compatibility](../dependency-compatibility/README.md): Cloudpickle 3.1.2 accesses the removed `DELETE_GLOBAL` opcode; Genshi 0.7.7 constructs an AST node without its required `body` field.

The five additional FT failures are runtime-mode rejections, not new API exceptions:

| Program | Native extension that enables the GIL | Installed package |
|---------|---------------------------------------|-------------------|
| Coverage | `coverage.tracer` | Coverage 7.3.2 |
| dulwich_log | `dulwich._objects` | Dulwich 0.20.23 |
| Sphinx | `markupsafe._speedups` | MarkupSafe 2.0.1; Sphinx 7.3.7 |
| SQLAlchemy declarative and imperative | `greenlet._greenlet` | Greenlet 3.2.4; SQLAlchemy 1.4.19 |

Each FT invocation's logs show native-extension warnings followed by five `HookError: Free-threaded benchmark ran with the GIL enabled` errors. The runtime attestation correctly refuses to label these executions free-threaded. The same failures occur on both source revisions and with parallel GC disabled, so neither the integration nor collector activation is required to trigger them. This does not prove absence of collector failures in longer runs.

No workload, dependency pin, collector code, runtime-mode check or unsafe-extension declaration was changed. No `PYTHON_GIL=0` override was added. Retaining the check means these programs still need compatible dependencies before a complete genuine-FT comparison is possible.

## Provenance and preservation

Scratch output is `/tmp/parallel-gc-default-compatibility-20261017-GFJ1lk`; parent checkpoint is `cf7ac426a7d85f05d936224680389d37896c96fa`. Sources and binaries remain baseline `c67363fa59543ef5d572383af927f1cff88514a1` and current `388fd5bb46fdda6b464db566faf818505c3d6eef`. Original build/native preparation records remain linked from the investigation. All four binary hashes and the three frozen harness/hook hashes passed before execution; harness hashes passed between every invocation and after completion. Both source worktrees remain clean. Execution session 26863 completed; its controller is no longer live.

Complete logs and partial suite JSONs are gzip-compressed without content rewriting. `SHA256SUMS` checks the archives; `ORIGINAL-SHA256SUMS` records each decompressed original. Decompressed content was compared byte-for-byte with scratch originals. Scratch files were not deleted. `exits.tsv` preserves all eight nonzero exit statuses.

Post-run package inventories match between baseline and current within each mode. They differ from initial preparation records in two expected ways: the standard 2to3 benchmark installs its local vendored `lib2to3`, and pip's editable Git URL reflects the later parent commit. Every originally listed third-party dependency version is unchanged; frozen hook/source content is checked separately rather than inferred from an editable URL. The first inventory comparison used `pip freeze --all` against an original plain `pip freeze`, additionally listing pip; that diagnostic mismatch is preserved as `baseline-gil-packages-after-all.txt`. Corrected plain freezes are preserved for all four targets. One fingerprint check was mistakenly invoked from the CPython subdirectory and failed to resolve the parent-relative paths; repeating it from the parent passed. Neither comparison error was treated as a passing check.

## Reproduction

Run each target and policy separately from the parent repository. For example:

```bash
builds=/tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW
prepared=/tmp/parallel-gc-pyperformance-prepared-20261017-dBFKZD
diagnostic_output=$(mktemp -d /tmp/parallel-gc-compatibility-repeat-XXXXXX)
numactl --cpunodebind=0 --membind=0 taskset --cpu-list 0-31 \
    "$builds/driver/bin/python" benchmarks/run_pyperformance.py single \
    --python "$builds/baseline-ft/python" \
    --source "$builds/baseline-source" \
    --mode disabled --benchmarks default --run-style debug \
    --affinity 0-31 --timeout 300 --work-root "$prepared/ft" \
    --output "$diagnostic_output/baseline-ft-disabled.partial.json" \
    > "$diagnostic_output/baseline-ft-disabled.log" 2>&1
```

Repeat for baseline/current × GIL/FT × enabled/disabled without concurrent measurements. Original invocation options and subprocess commands are retained in each log. The 300-second timeout is diagnostic only, not a change to the planned rigorous ABBA protocol.

## Next decision

Dependency work requires explicit agreement: investigate compatible releases or narrowly tested compatibility patches, keep every original workload, apply the same environment changes to baseline and current, and retain post-import FT runtime attestation. Do not silently drop programs, force unsafe modules to run without the GIL, or count GIL-fallback timings as FT data. Repeat this full compatibility check after any agreed repair; only then restart the sixteen rigorous suites in a new results directory. Hosted CI results remain separately unverified.
