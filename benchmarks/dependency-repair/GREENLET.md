# Greenlet native FT compatibility

Use **Greenlet 3.5.6**, built for both GIL and FT Python 3.16. The original 3.2.4 extension enables the GIL in FT. All four baseline/current native probes now pass, including switching a greenlet and checking its returned value; FT remains GIL-disabled. Source declares FT support with `PyUnstable_Module_SetGIL(..., Py_MOD_GIL_NOT_USED)`.

The raw probes and original failure are in [greenlet-evidence](greenlet-evidence/).

Build using each target Python:

```bash
"$target_python" -m pip wheel --no-cache-dir --no-deps \
  --no-binary=greenlet --wheel-dir "$wheel_directory" greenlet==3.5.6
```

Install the same mode-specific wheel on baseline/current; run [test_native_dependencies.py](test_native_dependencies.py) with `greenlet`.

Tested native wheel SHA-256:

- GIL: `e5b97e057781b33239d4d4ace8fcc48d60da3b714a5fd3a3cd179ace1c3f5b0d`.
- FT: `70139e04bd0ab91aa3c6d0c4aa8d264088075655ac5a390ff6339614a0fb24fe`.

**This does not repair the SQLAlchemy benchmarks by itself.** Once Greenlet's failure is removed, SQLAlchemy 1.4.19's `cprocessors` also enables the GIL. SQLAlchemy 1.4.54 likewise has unsupported native extensions. A separate decision is required for SQLAlchemy; do not force GIL-disabled execution or report those benchmark programs passing.
