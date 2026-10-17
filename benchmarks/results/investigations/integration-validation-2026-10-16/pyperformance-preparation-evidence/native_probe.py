"""Verify native benchmark dependencies; do not collect performance data."""

import json
import sys
import sysconfig

import decimal
import sqlite3
import ssl
import fastapi
import httpx
import uvicorn
import pydantic_core
from pydantic_core import _pydantic_core, SchemaValidator
from fastapi.testclient import TestClient

app = fastapi.FastAPI()


@app.get("/check")
def check():
    return {"value": SchemaValidator({"type": "int"}).validate_python("42")}


with TestClient(app) as client:
    response = client.get("/check")
if response.status_code != 200 or response.json() != {"value": 42}:
    raise RuntimeError("FastAPI dependency probe returned the wrong response")

native = _pydantic_core.__file__.endswith(sysconfig.get_config_var("EXT_SUFFIX"))
gil = sys._is_gil_enabled()
free_threaded = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
if not native or gil == free_threaded:
    raise RuntimeError(f"Invalid native/runtime mode: native={native}, gil={gil}")
print(json.dumps({
    "executable": sys.executable,
    "fastapi": fastapi.__version__,
    "httpx": httpx.__version__,
    "uvicorn": uvicorn.__version__,
    "pydantic_core": pydantic_core.__version__,
    "native_module": _pydantic_core.__file__,
    "native": native,
    "gil_enabled": gil,
    "response": response.json(),
}, sort_keys=True))
