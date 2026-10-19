# Cloudpickle Python 3.16 compatibility

Repair: retain Cloudpickle 3.1.2 and construct its global-opcode set from the opcodes present in the interpreter. Python 3.16 represents global deletion with `STORE_GLOBAL`; older interpreters still include `DELETE_GLOBAL`. The existing name-discovery loop is unchanged. No benchmark or CPython source is modified.

The unpatched package fails on import with `KeyError: 'DELETE_GLOBAL'`. `test_cloudpickle_316.py` was written and run before the repair; the saved failure is [unpatched-gil.log](cloudpickle-evidence/unpatched-gil.log).

After the repair all five tests pass with baseline/current GIL/FT optimized Python 3.16 binaries, and with Python 3.12 as a control where `DELETE_GLOBAL` exists. They exercise shared global loads/stores/deletion, isolation of the original globals, nested global discovery, closures and comprehensions. FT remains GIL-disabled.

The **unchanged original Dask benchmark** passes short correctness checks in all eight baseline/current × GIL/FT × enabled/disabled contexts. Raw output and worker metadata are in [cloudpickle-evidence](cloudpickle-evidence/). All four FT records report `parallel_gc_runtime_gil_enabled: false`. These single-value checks establish execution, not performance. Dask remains at 2024.10.0.

## Reproduce the wheel repair

Use an isolated packaging environment with `wheel==0.46.3`. Here `$repair_root` is a fresh scratch directory and `$packaging_python` is that environment's Python:

```bash
"$packaging_python" -m pip download --no-deps \
  --dest "$repair_root/packages" cloudpickle==3.1.2
"$packaging_python" -m wheel unpack \
  "$repair_root/packages/cloudpickle-3.1.2-py3-none-any.whl" \
  --dest "$repair_root/unpacked"
patch --batch --fuzz=0 -p1 \
  -d "$repair_root/unpacked/cloudpickle-3.1.2" \
  -i /data/users/alexturner/parallel_gc/benchmarks/dependency-repair/cloudpickle-3.1.2-python316.patch
mkdir -p "$repair_root/patched-wheels"
"$packaging_python" -m wheel pack \
  "$repair_root/unpacked/cloudpickle-3.1.2" \
  --dest-dir "$repair_root/patched-wheels"
```

`wheel pack` regenerates wheel integrity records. Install this wheel only in fresh benchmark environments, identically for baseline/current; do not upload it as an upstream release. Run the tests using each target interpreter:

```bash
"$target_python" -m pip install --no-deps --force-reinstall \
  "$repair_root/patched-wheels/cloudpickle-3.1.2-py3-none-any.whl"
"$target_python" benchmarks/dependency-repair/test_cloudpickle_316.py
```

## Provenance and limitations

- Original wheel SHA-256: `9acb47f6afd73f60dc1df93bb801b472f05ff42fa6c84167d25cb206be1fbf4a`.
- Patch SHA-256: `6a4d5110943ed92fc3391823461fc0981ebac7808000a16cbeeb35712b22feae`.
- Locally tested repaired wheel SHA-256: `9e9fc73113f388f173d302f5573f9f68f751ca5efb47b614904baa560812296e`. Repacking timestamps can change the archive hash; retain the source and patch hashes in every campaign.
- Optimized baseline CPython: `c67363fa59543ef5d572383af927f1cff88514a1`; current: `388fd5bb46fdda6b464db566faf818505c3d6eef`.
- Diagnostic commands used `PYTHONPATH` to select the isolated patched dependency before the historical environment, and the parent-owned hook source explicitly. The first direct Dask command omitted the editable hook's source path and failed before execution; correcting that diagnostic invocation produced the eight retained passes. Historical environments were not modified.
- Dask logs warn that external IP detection is unavailable and use a local scheduler. No Dask workload setting was changed.
- This is not a claim that every Cloudpickle feature supports Python 3.16. Full-default readiness and rigorous benchmark comparisons remain pending.
