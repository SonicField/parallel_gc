# Python 3.16 dependency failures in the default pyperformance suite

## Observation and scope

The corrected GIL-enabled baseline suite started at 05:55:44 UTC on 17 October. It attempted the unchanged 100-program default selection and exited nonzero before the controller started GIL-disabled baseline at 07:49:26 UTC. The log identifies two failed programs: Dask and Genshi. The saved JSON contains 124 successful result entries because some programs produce several named results. It includes `fastapi_http`; the earlier native Rust preparation failure did not recur here. This is a failed suite with partial results, not a completed ABBA comparison.

The exact baseline/candidate sources, four PGO+LTO builds, package inventories and setup records are documented in [full preparation](../full-pyperformance-preparation/README.md). Sources remain `c67363fa59543ef5d572383af927f1cff88514a1` and `388fd5bb46fdda6b464db566faf818505c3d6eef`. No collector, benchmark implementation, workload selection, parameter or dependency version was changed for this investigation.

| Program | Installed dependency | Exception and location |
|---------|----------------------|------------------------|
| Dask (`dask[distributed]==2024.10.0`) | Cloudpickle 3.1.2 | Import accesses `opcode.opmap["DELETE_GLOBAL"]`, raising `KeyError: 'DELETE_GLOBAL'` in `cloudpickle/cloudpickle.py:389` |
| Genshi (`genshi==0.7.7`) | Genshi 0.7.7 | AST cloning calls `node.__class__()` without required fields, raising `TypeError: ast.Expression.__init__ missing 1 required positional argument: 'body'` in `genshi/template/astutil.py:802` |

Dask fails before constructing its `pyperf.Runner`, so its worker GC hook has not activated. Genshi fails while constructing the template before its explicit timed rendering interval. The log's phrase “Benchmark died” is pyperformance's error classification; these traces show uncaught Python exceptions, not a demonstrated native crash.

## Falsification experiment

**Claim tested:** These two observed exceptions require parallel GC activation.

**Counterexample sought:** The same exceptions on a fresh process with parallel GC disabled and no helper pool.

Ran the [untimed probe](../compatibility_probe.py) on all four actual measurement virtual environments, pinned to CPU 32. Each process explicitly calls `gc.disable_parallel()` and records configuration before and after importing Cloudpickle and constructing a minimal Genshi template. A direct `ast.Expression()` call separately checks the missing-required-field error. These probes do not replace the original benchmark programs.

All four processes exited zero after reproducing the expected `KeyError` and both expected `TypeError` messages. All four recorded `enabled=false` and `pool_active=false` before and after. Both FT processes recorded a disabled runtime GIL before and after imports; both GIL processes retained an enabled GIL. All four stderr captures are empty. Raw records: [baseline GIL](baseline-gil.json), [candidate GIL](candidate-gil.json), [baseline FT](baseline-ft.json), [candidate FT](candidate-ft.json).

Repeated all four probes after stopping the campaign; the same exceptions and runtime configurations reproduced. Separately checked all 5,006 run records in the partial suite, including calibration runs: their merged metadata identifies GIL compilation, an enabled runtime GIL and the enabled collector policy. This attests only the saved partial results, not the two failed programs or a completed source comparison.

**Verdict: Falsified.** Parallel GC activation is not required for these exceptions. This does not establish general collector correctness or prove that these libraries have no further Python 3.16 compatibility failures.

Reproduction, using the retained preparation root:

```bash
prepared=/tmp/parallel-gc-pyperformance-prepared-20261017-dBFKZD
probe=benchmarks/results/investigations/integration-validation-2026-10-16/compatibility_probe.py
for label in baseline-gil candidate-gil baseline-ft candidate-ft; do
    target_python=$(sed -n 's/^VERIFIED_PYTHON=//p' "$prepared/$label-hook-setup.log")
    taskset --cpu-list 32 "$target_python" "$probe" || exit
done
```

Run from the parent `parallel_gc` repository. The saved records retain the original runtime version stamps, including the already documented out-of-tree `-dirty` label; independent source checks remain the cleanliness evidence.

## Preserved campaign evidence

After revalidating that process group 1711344 contained only this campaign's launcher, driver and benchmark children, sent it SIGTERM and verified no group members remained by 07:54:56 UTC. GIL-disabled baseline was interrupted, not completed. No FT pyperformance suite had started. No files were deleted. All original scratch output remains under the preparation root above.

The gzip archives below decompress byte-for-byte to their original files. Compression integrity and decompressed SHA-256 were checked; there is no JSON rewriting or terminal-newline alteration.

| Archive | SHA-256 of original, decompressed content |
|---------|-------------------------------------------|
| `gil-enabled-01-baseline.partial.json.gz` | `1ffdf8f3785fe72b0242919dc9b742fb7f987bb031566c8fb9e1ad087f931850` |
| `gil-enabled.failed.log.gz` | `fd7d14844116bbae0e3259a800239fa8b9278ae07aa378a3859a037e17fc7746` |
| `gil-disabled.interrupted.log.gz` | `07e0256c01f02dc4e453456100adb502cea16219d347d5d0191068b26f81f05e` |
| `campaign-summary.interrupted.log.gz` | `1b2091426e87b539de312c75af6784a25ab8692d35de39eb48b68e4b41ff24d4` |

## Decision still required

Successful installation, `pip check`, native imports and FastAPI requests did not establish runtime compatibility for every default workload. Before restarting a multi-day campaign, exercise every selected program on all four environments with untimed or short compatibility checks. Such checks establish readiness only; they are not performance measurements.

That diagnostic check has now run for all four targets and both collector policies: [all-program runtime results](../default-runtime-compatibility/README.md). It reproduces Dask/Genshi everywhere and identifies five additional FT programs whose dependencies enable the GIL. These are correctly rejected by the runtime-mode hook. All failures occur on both source revisions and with the collector disabled; all eight invocations remain failing. Dependency work must address these additional FT requirements too, without bypassing runtime attestation.

Do not omit Dask or Genshi to obtain a passing reduced suite. Any dependency-version change or compatibility patch must be explicitly agreed, isolated from GC changes, applied identically to baseline and candidate within each mode, and checked against the original workloads. No such change has been made. The full sixteen-suite pyperformance comparison and hosted CI evidence remain outstanding.
