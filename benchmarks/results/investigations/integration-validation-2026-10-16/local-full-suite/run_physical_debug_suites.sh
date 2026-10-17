#!/usr/bin/env bash
# Full local checks only; never replace the optimized measurement binaries.
set -euo pipefail
root=${1:?empty owned build directory required}
source=${2:?physical CPython source directory required}
deps=${3:?existing owned native dependency prefix required}
test -d "$root"
test -z "$(ls -A "$root")"
test "$source" = "$(readlink -f "$source")"
test "$(git -C "$source" rev-parse HEAD)" = \
    388fd5bb46fdda6b464db566faf818505c3d6eef
git -C "$source" diff --quiet
git -C "$source" diff --cached --quiet
test -f "$deps/usr/include/mpdecimal.h"
test -f "$deps/usr/lib64/libmpdec.so"
git -C "$source" rev-parse HEAD > "$root/cpython-revision.txt"
overall=0
for mode in gil ft; do
    flags=(--with-pydebug --with-parallel-gc)
    if [ "$mode" = ft ]; then
        flags+=(--disable-gil)
    fi
    mkdir "$root/$mode"
    date -u '+%Y-%m-%dT%H:%M:%SZ'
    echo "PHYSICAL_DEBUG_BUILD=$mode"
    (
        cd "$root/$mode"
        CPPFLAGS="-I$deps/usr/include" \
        LDFLAGS="-L$deps/usr/lib64 -Wl,-rpath,$deps/usr/lib64" \
        PKG_CONFIG_PATH="$deps/usr/lib64/pkgconfig" \
        PKG_CONFIG_SYSROOT_DIR="$deps" \
            "$source/configure" "${flags[@]}" > configure.log 2>&1
        make -j16 > build.log 2>&1
        sha256sum python > binary.sha256
        ./python - "$mode" "$source" > preflight.json <<'PY'
import _ctypes
import _decimal
import _sqlite3
import _ssl
import decimal
import gc
import json
import os
import pydoc
import sys
import sysconfig
import test.support
import unittest

mode, source = sys.argv[1:]
assert sysconfig.get_config_var("Py_DEBUG")
assert bool(sysconfig.get_config_var("Py_GIL_DISABLED")) == (mode == "ft")
assert sys._is_gil_enabled() == (mode == "gil")
assert decimal.Decimal is _decimal.Decimal
assert gc.get_parallel_config()["available"]
assert not gc.get_parallel_config()["enabled"]
assert sysconfig.get_config_var("abs_srcdir") == source
assert sysconfig.get_config_var("srcdir") == source
paths = {name: module.__file__ for name, module in (
    ("json", json), ("pydoc", pydoc),
    ("test_support", test.support), ("unittest", unittest),
)}
assert all(path.startswith(source + "/Lib/") for path in paths.values())
assert all(os.path.realpath(path) == path for path in paths.values())
print(json.dumps({
    "mode": mode, "version": sys.version, "python_git": sys._git,
    "config_args": sysconfig.get_config_var("CONFIG_ARGS"),
    "runtime_gil_enabled": sys._is_gil_enabled(), "paths": paths,
    "srcdir": source, "native_decimal": _decimal.__file__,
    "parallel_gc": gc.get_parallel_config(),
}, indent=2, sort_keys=True))
PY
        ./python -m unittest \
            test.test_pydoc.test_pydoc.PydocDocTest.test_mixed_case_module_names_are_lower_cased \
            test.test_pydoc.test_pydoc.PydocDocTest.test_online_docs_link \
            test.test_pydoc.test_pydoc.TestInternalUtilities.test__get_version \
            test.test_unittest.test_program.TestCommandLineArgs.testSelectedTestNamesFunctionalTest \
            > path-tests.log 2>&1
        ./python -m test --list-tests > default-selection.txt
    )
    date -u '+%Y-%m-%dT%H:%M:%SZ'
    echo "PHYSICAL_DEBUG_FULL_START=$mode"
    result=0
    (
        cd "$root/$mode"
        ./python -m test -q -j2 --timeout=600 --fail-env-changed \
            --rerun --verbose3 --randseed=20260929 > full-test.log 2>&1
    ) || result=$?
    printf '%s\t%s\n' "$mode" "$result" >> "$root/exits.tsv"
    echo "PHYSICAL_DEBUG_FULL_EXIT=$mode $result"
    tail -n 28 "$root/$mode/full-test.log"
    (cd "$root/$mode" && sha256sum --check binary.sha256)
    git -C "$source" diff --quiet
    git -C "$source" diff --cached --quiet
    if [ "$result" -ne 0 ]; then
        overall=1
    fi
done
date -u '+%Y-%m-%dT%H:%M:%SZ'
echo "PHYSICAL_DEBUG_FINISHED=$overall"
exit "$overall"
