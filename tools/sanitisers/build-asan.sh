#!/bin/bash
# Build parallel_gc/cpython/ with AddressSanitizer.
#
# Per goal.md: build in place. This script operates on ../../cpython/ relative
# to its own location. Switching to or from sanitiser builds requires a full
# rebuild (make distclean), so this is intentionally slow but reproducible.
#
# Requires clang.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CPYTHON_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)/cpython"

if [ ! -f "$CPYTHON_DIR/configure" ]; then
    echo "ERROR: cpython/ not found at $CPYTHON_DIR" >&2
    echo "  Run 'git submodule update --init' from the project root." >&2
    exit 1
fi

if ! command -v clang >/dev/null 2>&1; then
    echo "ERROR: clang not available. ASan builds require clang." >&2
    exit 1
fi

cd "$CPYTHON_DIR"

echo "=== ASAN Build ==="
echo "Date:     $(date)"
echo "Branch:   $(git rev-parse --abbrev-ref HEAD)"
echo "Commit:   $(git log -1 --oneline)"
echo "Target:   $CPYTHON_DIR"
echo ""

echo "=== Step 1: distclean (sanitiser builds incompatible with prior configs) ==="
make distclean 2>&1 | tail -1

echo "=== Step 2: configure with clang + ASan ==="
CC=clang CXX=clang++ ./configure --with-parallel-gc --with-pydebug --with-address-sanitizer

echo "=== Step 3: build ==="
make -j"$(nproc)"

echo "=== Step 4: verify parallel GC is compiled in ==="
./python -c "import gc; print('config:', gc.get_parallel_config())"

echo ""
echo "=== ASAN build complete ==="
echo "Run tests: cd $CPYTHON_DIR && ./python -m test test_gc test_gc_parallel_mark_alive test_gc_ws_deque"
