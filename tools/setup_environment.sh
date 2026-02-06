#!/bin/bash
# Initial setup script for parallel GC development environment

set -e
set -u

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CPYTHON_DIR="$WORKSPACE/cpython"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[SETUP]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
info() { echo -e "${BLUE}[INFO]${NC} $*"; }

echo ""
log "Parallel GC Development Environment Setup"
echo "==========================================="
echo ""

# Step 1: Clone CPython if not exists
if [ -d "$CPYTHON_DIR/.git" ]; then
    log "✓ CPython already cloned at $CPYTHON_DIR"
    cd "$CPYTHON_DIR"
    info "  Current branch: $(git rev-parse --abbrev-ref HEAD)"
    info "  Latest commit: $(git log -1 --oneline)"
else
    log "Cloning CPython..."
    cd "$WORKSPACE"
    if [ ! -d "$CPYTHON_DIR" ]; then
        mkdir -p "$CPYTHON_DIR"
    fi
    cd "$CPYTHON_DIR"

    if git clone https://github.com/python/cpython.git .; then
        log "✓ CPython cloned successfully"
    else
        error "Failed to clone CPython"
        error "Try manually: cd $CPYTHON_DIR && git clone https://github.com/python/cpython.git ."
        exit 1
    fi
fi

echo ""

# Step 2: Check out main branch
cd "$CPYTHON_DIR"
log "Checking out main branch..."
git checkout main
git pull

echo ""

# Step 3: Create parallel-gc development branch
BRANCH_NAME="parallel-gc-dev"
if git rev-parse --verify "$BRANCH_NAME" >/dev/null 2>&1; then
    log "✓ Branch '$BRANCH_NAME' already exists"
    info "  Switch to it: cd $CPYTHON_DIR && git checkout $BRANCH_NAME"
else
    log "Creating development branch '$BRANCH_NAME'..."
    git checkout -b "$BRANCH_NAME"
    log "✓ Branch created and checked out"
fi

echo ""

# Step 4: Check build dependencies
log "Checking build dependencies..."

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 (missing)"
        return 1
    fi
}

MISSING_DEPS=0

check_command gcc || MISSING_DEPS=$((MISSING_DEPS + 1))
check_command make || MISSING_DEPS=$((MISSING_DEPS + 1))
check_command git || MISSING_DEPS=$((MISSING_DEPS + 1))
check_command python3 || MISSING_DEPS=$((MISSING_DEPS + 1))

if [ $MISSING_DEPS -gt 0 ]; then
    echo ""
    error "Missing $MISSING_DEPS required dependencies"
    echo ""
    info "Install on Debian/Ubuntu:"
    echo "  sudo apt-get install build-essential git python3"
    echo ""
    info "Install on Fedora/RHEL:"
    echo "  sudo dnf install gcc make git python3"
    echo ""
    exit 1
fi

echo ""

# Step 5: Check optional dependencies
log "Checking optional dependencies..."

check_command clang || info "  clang not found - ASan/TSan builds will be skipped"
check_command valgrind || info "  valgrind not found - memory leak detection unavailable"

echo ""

# Step 6: Create initial build (serial GC baseline)
log "Building baseline (serial GC)..."

SERIAL_BUILD="$WORKSPACE/builds/serial"
mkdir -p "$SERIAL_BUILD"
cd "$SERIAL_BUILD"

if [ -f "./python" ]; then
    log "✓ Baseline build already exists"
    info "  Version: $(./python --version 2>&1)"
else
    log "  Configuring..."
    if "$CPYTHON_DIR/configure" --prefix="$SERIAL_BUILD/install" > "$WORKSPACE/logs/setup_serial_build.log" 2>&1; then
        log "  Building (this may take a few minutes)..."
        if make -j$(nproc) >> "$WORKSPACE/logs/setup_serial_build.log" 2>&1; then
            log "✓ Baseline build complete"
            info "  Version: $(./python --version 2>&1)"
        else
            error "Build failed! See: $WORKSPACE/logs/setup_serial_build.log"
            exit 1
        fi
    else
        error "Configure failed! See: $WORKSPACE/logs/setup_serial_build.log"
        exit 1
    fi
fi

echo ""

# Step 7: Run quick test
log "Running quick sanity test..."
cd "$SERIAL_BUILD"
if ./python -c "import gc; gc.collect(); print('GC works!')"; then
    log "✓ Sanity test passed"
else
    error "Sanity test failed!"
    exit 1
fi

echo ""

# Step 8: Summary
log "Setup Complete!"
echo "============================================"
echo ""
echo -e "${GREEN}Environment ready for development!${NC}"
echo ""
echo "Directory structure:"
echo "  Workspace:     $WORKSPACE"
echo "  CPython src:   $CPYTHON_DIR"
echo "  Serial build:  $SERIAL_BUILD/python"
echo ""
echo "Next steps:"
echo "  1. Run baseline tests:"
echo "     cd $SERIAL_BUILD"
echo "     ./python -m test test_gc -v"
echo ""
echo "  2. Build all configurations:"
echo "     $WORKSPACE/tools/build_all_configs.sh"
echo ""
echo "Useful aliases (add to ~/.bashrc):"
echo "  alias pgc-dev='cd $WORKSPACE'"
echo "  alias pgc-src='cd $CPYTHON_DIR'"
echo "  alias pgc-build='cd $SERIAL_BUILD'"
echo ""
log "Happy hacking!"
echo ""
