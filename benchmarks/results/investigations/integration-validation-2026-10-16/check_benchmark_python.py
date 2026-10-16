"""Require native benchmark modules and the intended optimized build mode."""
import argparse
import json
import platform
import sys
import sysconfig

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('mode', choices=('gil', 'ft'))
args = parser.parse_args()

# Import native modules explicitly: importing decimal alone accepts its slow
# pure-Python fallback when libmpdec was missing during configuration.
import _ctypes
import _decimal
import _sqlite3
import _ssl
import bz2
import decimal
import gc
import hashlib
import lzma
import sqlite3
import ssl
import uuid
import zlib

if decimal.Decimal is not _decimal.Decimal:
    raise RuntimeError('decimal is not using the native _decimal implementation')
if sysconfig.get_config_var('Py_DEBUG'):
    raise RuntimeError('debug builds are not benchmark builds')
if bool(sysconfig.get_config_var('Py_GIL_DISABLED')) != (args.mode == 'ft'):
    raise RuntimeError('compiled GIL/FT mode does not match the requested mode')
if sys._is_gil_enabled() != (args.mode == 'gil'):
    raise RuntimeError('runtime GIL state changed during dependency imports')
config = gc.get_parallel_config()
if not config['available'] or config['enabled']:
    raise RuntimeError(f'expected available, initially disabled parallel GC: {config}')
flags = sysconfig.get_config_var('CONFIG_ARGS')
if '--enable-optimizations' not in flags or '--with-lto' not in flags:
    raise RuntimeError(f'PGO+LTO configure flags missing: {flags}')
print(json.dumps({
    'version': sys.version,
    'machine': platform.machine(),
    'config_args': flags,
    'gil_enabled': sys._is_gil_enabled(),
    'parallel_gc': config,
    'native_decimal': _decimal.__file__,
    'libmpdec_version': _decimal.__libmpdec_version__,
}, indent=2))
