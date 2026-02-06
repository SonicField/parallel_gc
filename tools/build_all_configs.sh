#!/bin/bash
# Build all CPython configurations for parallel GC development

set -e  # Exit on error
set -u  # Exit on undefined variable

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPYTHON_SRC="$WORKSPACE/cpython"
BUILDS_DIR="$WORKSPACE/builds"
LOGS_DIR="$WORKSPACE/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $*"
}

error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

# Check CPython source exists
if [ ! -d "$CPYTHON_SRC" ] || [ ! -f "$CPYTHON_SRC/configure" ]; then
    error "CPython source not found at $CPYTHON_SRC"
    error "Run: cd $CPYTHON_SRC && git clone https://github.com/python/cpython.git ."
    exit 1
fi

# Create directories
mkdir -p "$BUILDS_DIR" "$LOGS_DIR"

# Number of parallel jobs
JOBS=$(nproc)

build_config() {
    local config_name="$1"
    shift
    local configure_args=("$@")

    log "Building $config_name configuration..."

    local build_dir="$BUILDS_DIR/$config_name"
    local log_file="$LOGS_DIR/build_${config_name}_$(date +%Y%m%d_%H%M%S).log"

    mkdir -p "$build_dir"
    cd "$build_dir"

    # Configure
    log "  Configuring... (log: $log_file)"
    if ! "$CPYTHON_SRC/configure" \
        --prefix="$build_dir/install" \
        "${configure_args[@]}" \
        > "$log_file" 2>&1; then
        error "  Configure failed! See: $log_file"
        return 1
    fi

    # Build
    log "  Building with $JOBS parallel jobs..."
    if ! make -j"$JOBS" >> "$log_file" 2>&1; then
        error "  Build failed! See: $log_file"
        return 1
    fi

    # Test (quick smoke test)
    log "  Running smoke test..."
    if ! ./python -c "import sys; print(f'Python {sys.version}')" >> "$log_file" 2>&1; then
        error "  Smoke test failed! See: $log_file"
        return 1
    fi

    log "  ${GREEN}✓${NC} $config_name build complete"
    echo "     Binary: $build_dir/python"
    echo "     Log: $log_file"

    return 0
}

# Build configurations
log "Starting parallel GC build matrix..."
log "CPython source: $CPYTHON_SRC"
log "Build directory: $BUILDS_DIR"
log "Using $JOBS parallel jobs"
echo ""

# Track build results
declare -a BUILDS_SUCCESS=()
declare -a BUILDS_FAILED=()

# 1. Serial GC (baseline)
if build_config "serial"; then
    BUILDS_SUCCESS+=("serial")
else
    BUILDS_FAILED+=("serial")
fi
echo ""

# 2. Parallel GC (release)
if build_config "release"; then
    BUILDS_SUCCESS+=("release")
else
    BUILDS_FAILED+=("release")
    warn "Parallel GC not available yet - this is expected early in development"
fi
echo ""

# 3. Parallel GC (debug)
if build_config "debug" --with-pydebug --with-assertions; then
    BUILDS_SUCCESS+=("debug")
else
    BUILDS_FAILED+=("debug")
    warn "Parallel GC not available yet - this is expected early in development"
fi
echo ""

# 4. AddressSanitizer (if clang available)
if command -v clang >/dev/null 2>&1; then
    export CC="clang -fsanitize=address"
    export LDFLAGS="-fsanitize=address"
    if build_config "asan" --with-pydebug; then
        BUILDS_SUCCESS+=("asan")
    else
        BUILDS_FAILED+=("asan")
    fi
    unset CC LDFLAGS
    echo ""
else
    warn "Clang not found - skipping ASan build"
fi

# 5. ThreadSanitizer (if clang available)
if command -v clang >/dev/null 2>&1; then
    export CC="clang -fsanitize=thread"
    export LDFLAGS="-fsanitize=thread"
    if build_config "tsan" --with-pydebug; then
        BUILDS_SUCCESS+=("tsan")
    else
        BUILDS_FAILED+=("tsan")
    fi
    unset CC LDFLAGS
    echo ""
else
    warn "Clang not found - skipping TSan build"
fi

# Summary
echo ""
log "Build Summary:"
if [ ${#BUILDS_SUCCESS[@]} -gt 0 ]; then
    echo -e "${GREEN}  Successful builds (${#BUILDS_SUCCESS[@]}):${NC}"
    for build in "${BUILDS_SUCCESS[@]}"; do
        echo "    ✓ $build ($BUILDS_DIR/$build/python)"
    done
fi

if [ ${#BUILDS_FAILED[@]} -gt 0 ]; then
    echo -e "${RED}  Failed builds (${#BUILDS_FAILED[@]}):${NC}"
    for build in "${BUILDS_FAILED[@]}"; do
        echo "    ✗ $build (see logs in $LOGS_DIR)"
    done
    echo ""
    warn "Some builds failed - this is normal if parallel GC not yet implemented"
fi

echo ""
log "Done! Next steps:"
echo "  1. Run tests:   cd $BUILDS_DIR/serial && ./python -m test test_gc -v"
echo "  2. Development: cd $BUILDS_DIR/debug && make -j$JOBS"
echo "  3. Benchmarks:  cd $WORKSPACE/benchmarks && ./scripts/run_benchmarks.sh"
