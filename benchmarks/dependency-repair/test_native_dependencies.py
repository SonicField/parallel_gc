"""Verify the dependency's native implementation and FT runtime contract."""

import argparse
import importlib
import importlib.machinery
import json
import sys
import sysconfig


MODULES = {
    "coverage": "coverage.tracer",
    "markupsafe": "markupsafe._speedups",
    "greenlet": "greenlet._greenlet",
    "dulwich": "dulwich._objects",
}


def verify(dependency):
    ft_build = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
    gil_before = sys._is_gil_enabled()
    if ft_build and gil_before:
        raise RuntimeError("FT dependency check started with the GIL enabled")
    module = importlib.import_module(MODULES[dependency])
    filename = module.__file__
    if not any(filename.endswith(suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES):
        raise RuntimeError(f"Expected a native {dependency} extension, got {filename}")

    trace_engine = None
    if dependency == "coverage":
        import coverage
        collector = coverage.Coverage()
        collector.start()
        try:
            trace_engine = collector._collector.tracer_name()
        finally:
            collector.stop()
        if trace_engine != "CTracer":
            raise RuntimeError(f"Expected the benchmark's CTracer engine, got {trace_engine}")
    elif dependency == "markupsafe":
        from markupsafe import escape
        if escape("<tag>") != "&lt;tag&gt;":
            raise RuntimeError("MarkupSafe produced incorrect escaped text")
    elif dependency == "greenlet":
        from greenlet import greenlet
        if greenlet(lambda: 42).switch() != 42:
            raise RuntimeError("Greenlet did not return the switched function's value")
    gil_after = sys._is_gil_enabled()
    if ft_build and gil_after:
        raise RuntimeError(f"{dependency} enabled the GIL in the FT process")
    return {
        "dependency": dependency,
        "native_module": filename,
        "compiled_gil_disabled": ft_build,
        "runtime_gil_before": gil_before,
        "runtime_gil_after": gil_after,
        "trace_engine": trace_engine,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dependency", choices=MODULES)
    args = parser.parse_args()
    print(json.dumps(verify(args.dependency), sort_keys=True))
