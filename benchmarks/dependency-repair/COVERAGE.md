# Coverage native FT compatibility

Use **Coverage 7.6.12**, built from source for both GIL and FT Python 3.16. It retains the original benchmark's default **CTracer** engine. The original 7.3.2 extension enables the GIL on import in FT; 7.6.12 does not.

The newest release, 7.16.2, was explored but rejected for this comparison because its default engine is `SysMonitor`. Passing execution with a different tracing implementation is not sufficient. Its exploratory output is retained in [coverage-newest-rejected-evidence](coverage-newest-rejected-evidence/).

The [native dependency probe](test_native_dependencies.py) checks that the imported file is an extension, that the active engine is CTracer, and that FT remains GIL-disabled. All four baseline/current GIL/FT probes pass. The unchanged recursive-Fibonacci Coverage benchmark passes all eight enabled/disabled checks. Raw logs, results and probes are in [coverage-evidence](coverage-evidence/). These short checks are not performance measurements.

Build separately with each target Python, in isolated packaging environments:

```bash
"$target_python" -m pip wheel --no-cache-dir --no-deps \
  --no-binary=coverage --wheel-dir "$wheel_directory" coverage==7.6.12
```

Verify that the wheel contains `coverage/tracer` as a native extension; install the same mode-specific wheel into baseline/current benchmark environments. No benchmark source, GC setting or tracing environment override is required.

Tested native wheel SHA-256:

- GIL: `92b82a5e3c481d3c2655bf4f4a6740fb5e328370864087a6d7d612d86c699f8d`.
- FT: `15b99e91de663093850a8911d04a21e675fcfd2110ebad01f8dd3b043b2fa003`.

This changes a dependency version, so new benchmark measurements must not be mixed numerically with historical Coverage results using 7.3.2. Both sides of the new source comparison must use 7.6.12.
