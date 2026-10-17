"""Falsify collector attribution of the observed dependency API failures.

This is an untimed correctness probe, not a replacement benchmark workload.
"""

import ast
import gc
import importlib
import json
import sys
import sysconfig


gc.disable_parallel()
before = gc.get_parallel_config()
if before["enabled"] or before["pool_active"]:
    raise RuntimeError("Probe requires disabled parallel GC and no helper pool")


def capture(operation):
    try:
        operation()
    except Exception as error:
        return {"type": type(error).__name__, "message": str(error)}
    return {"type": None, "message": "unexpected success"}


def template():
    from genshi.template import NewTextTemplate
    NewTextTemplate("${value}")


gil_before = sys._is_gil_enabled()
observations = {
    "cloudpickle_import": capture(lambda: importlib.import_module("cloudpickle")),
    "empty_ast_expression": capture(ast.Expression),
    "genshi_template": capture(template),
}
record = {
    "executable": sys.executable,
    "python_git": sys._git,
    "compiled_gil_disabled": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
    "runtime_gil_before": gil_before,
    "runtime_gil_after": sys._is_gil_enabled(),
    "parallel_gc_before": before,
    "parallel_gc_after": gc.get_parallel_config(),
    "observations": observations,
}
print(json.dumps(record, sort_keys=True))
expected = (
    observations["cloudpickle_import"]["type"] == "KeyError"
    and observations["cloudpickle_import"]["message"] == "'DELETE_GLOBAL'"
    and observations["empty_ast_expression"]["type"] == "TypeError"
    and "body" in observations["empty_ast_expression"]["message"]
    and observations["genshi_template"]["type"] == "TypeError"
    and "body" in observations["genshi_template"]["message"]
    and not record["parallel_gc_after"]["enabled"]
    and not record["parallel_gc_after"]["pool_active"]
)
if not expected:
    raise SystemExit("Observed incompatibility hypothesis did not reproduce")
