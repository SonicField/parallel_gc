#!/bin/bash
# Quick test runner for parallel GC development

set -e
set -u

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILDS_DIR="$WORKSPACE/builds"
LOGS_DIR="$WORKSPACE/logs"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# Parse arguments
BUILD_CONFIG="${1:-debug}"
TEST_FILTER="${2:-test_gc}"

BUILD_DIR="$BUILDS_DIR/$BUILD_CONFIG"
PYTHON="$BUILD_DIR/python"
LOG_FILE="$LOGS_DIR/test_${BUILD_CONFIG}_$(date +%Y%m%d_%H%M%S).log"

# Check build exists
if [ ! -f "$PYTHON" ]; then
    error "Python not found at $PYTHON"
    error "Run: $WORKSPACE/tools/build_all_configs.sh"
    exit 1
fi

mkdir -p "$LOGS_DIR"

log "Running tests with $BUILD_CONFIG build..."
echo "  Build: $BUILD_DIR"
echo "  Tests: $TEST_FILTER"
echo "  Log: $LOG_FILE"
echo ""

# Run tests
cd "$BUILD_DIR"
if ./python -m test "$TEST_FILTER" -v 2>&1 | tee "$LOG_FILE"; then
    log "${GREEN}✓${NC} Tests passed!"
else
    error "Tests failed! See: $LOG_FILE"
    exit 1
fi
