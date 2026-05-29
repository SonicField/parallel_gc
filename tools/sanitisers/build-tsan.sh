#!/bin/bash
# Build parallel_gc/cpython/ with ThreadSanitizer.
#
# TSan is the most useful gate for parallel GC correctness — concurrent worker
# threads + work-stealing deque + barriers/condvars are exactly what TSan catches.
# Run TSan before any parallel-GC-touching merge.
#
# Requires clang.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPYTHON_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)/cpython"

if [ ! -f "$CPYTHON_DIR/configure" ]; then
    echo "ERROR: cpython/ not found at $CPYTHON_DIR" >&2
    exit 1
fi

if ! command -v clang >/dev/null 2>&1; then
    echo "ERROR: clang not available. TSan builds require clang." >&2
    exit 1
fi

cd "$CPYTHON_DIR"

echo "=== TSAN Build ==="
echo "Date:     $(date)"
echo "Branch:   $(git rev-parse --abbrev-ref HEAD)"
echo "Commit:   $(git log -1 --oneline)"
echo "Target:   $CPYTHON_DIR"
echo ""

echo "=== Step 1: distclean ==="
make distclean 2>&1 | tail -1

echo "=== Step 2: configure with clang + TSan ==="
CC=clang CXX=clang++ ./configure --with-parallel-gc --with-pydebug --with-thread-sanitizer

echo "=== Step 3: build ==="
make -j"$(nproc)"

echo "=== Step 4: verify ==="
./python -c "import gc; print('config:', gc.get_parallel_config())"

echo ""
echo "=== TSAN build complete ==="
echo "Run tests: cd $CPYTHON_DIR && ./python -m test test_gc test_gc_parallel_mark_alive test_gc_ws_deque"
