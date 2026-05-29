# Parallel GC for CPython — entry-point Makefile.
#
# Targets here orchestrate cpython/ build + test operations so a reviewer
# (or a developer) can verify the project end-to-end with a single command.
# All actual building happens in-place in cpython/ — see docs/BUILD_AND_TEST.md
# for the underlying configure/make commands.
#
# See docs/TESTING.md for the testing strategy this Makefile implements.

NPROC := $(shell nproc 2>/dev/null || echo 4)
CPYTHON := cpython
PY := $(CPYTHON)/python

# Test groupings — see docs/TESTING.md for what each category proves.
TESTS_CORE := test_gc
TESTS_BUILD_AGNOSTIC := test_gc_ws_deque
TESTS_GIL_ONLY := test_gc_parallel_mark_alive
TESTS_FTP_ONLY := test_gc_parallel test_gc_ft_parallel test_gc_parallel_properties

# Default: tell the reader what to do.
.PHONY: help
help:
	@echo "Parallel GC for CPython — make targets:"
	@echo ""
	@echo "  Build (in-place in cpython/):"
	@echo "    make build-gil        configure --with-parallel-gc --with-pydebug, make"
	@echo "    make build-ftp        as above plus --disable-gil"
	@echo "    make build-release    --with-parallel-gc --enable-optimizations --with-lto (FTP)"
	@echo "    make build-asan       sanitiser build via tools/sanitisers/build-asan.sh"
	@echo "    make build-tsan       sanitiser build via tools/sanitisers/build-tsan.sh"
	@echo ""
	@echo "  Test (assumes you have built the matching config):"
	@echo "    make test-gc          core GC tests (must pass in any build)"
	@echo "    make test-parallel    parallel-GC-specific tests for current build"
	@echo "    make test-all         full CPython test suite (~2 min on 192-core, longer elsewhere)"
	@echo ""
	@echo "  Top-level gates (build + test):"
	@echo "    make gate-gil         build GIL, run parallel-GC tests + full suite"
	@echo "    make gate-ftp         build FTP, run parallel-GC tests + full suite"
	@echo "    make gate-all         both of the above sequentially (slow)"
	@echo ""
	@echo "  Benchmarks:"
	@echo "    make bench-quick      sanity benchmark (~1 min, requires release build)"
	@echo ""
	@echo "  Cleanup:"
	@echo "    make clean            make distclean in cpython/"
	@echo ""
	@echo "  Info:"
	@echo "    make verify           print version + parallel-GC config of current build"
	@echo ""
	@echo "See docs/TESTING.md for the strategy and docs/BUILD_AND_TEST.md for details."

# --- Build targets ---

.PHONY: build-gil
build-gil:
	cd $(CPYTHON) && $(MAKE) distclean 2>/dev/null || true
	cd $(CPYTHON) && ./configure --with-parallel-gc --with-pydebug
	cd $(CPYTHON) && $(MAKE) -j$(NPROC)
	@$(MAKE) -s verify

.PHONY: build-ftp
build-ftp:
	cd $(CPYTHON) && $(MAKE) distclean 2>/dev/null || true
	cd $(CPYTHON) && ./configure --with-parallel-gc --disable-gil --with-pydebug
	cd $(CPYTHON) && $(MAKE) -j$(NPROC)
	@$(MAKE) -s verify

.PHONY: build-release
build-release:
	cd $(CPYTHON) && $(MAKE) distclean 2>/dev/null || true
	cd $(CPYTHON) && ./configure --with-parallel-gc --disable-gil --enable-optimizations --with-lto
	cd $(CPYTHON) && $(MAKE) -j$(NPROC) PROFILE_TASK="-m test --pgo -x test_sqlite3"
	@$(MAKE) -s verify

.PHONY: build-asan
build-asan:
	./tools/sanitisers/build-asan.sh

.PHONY: build-tsan
build-tsan:
	./tools/sanitisers/build-tsan.sh

# --- Test targets ---

.PHONY: test-gc
test-gc:
	cd $(CPYTHON) && ./python -m test $(TESTS_CORE)

.PHONY: test-parallel
test-parallel:
	# Runs all parallel-GC tests; build-agnostic + whichever of GIL/FTP applies.
	# Skips for the inactive mode are expected and harmless.
	cd $(CPYTHON) && ./python -m test -j$(NPROC) \
	    $(TESTS_BUILD_AGNOSTIC) $(TESTS_GIL_ONLY) $(TESTS_FTP_ONLY)

.PHONY: test-all
test-all:
	cd $(CPYTHON) && ./python -m test -j$(NPROC)

# --- Gate targets (build + test combined) ---

.PHONY: gate-gil
gate-gil: build-gil
	$(MAKE) test-gc
	$(MAKE) test-parallel
	$(MAKE) test-all

.PHONY: gate-ftp
gate-ftp: build-ftp
	$(MAKE) test-gc
	$(MAKE) test-parallel
	$(MAKE) test-all

.PHONY: gate-all
gate-all: gate-gil gate-ftp

# --- Benchmarks ---

.PHONY: bench-quick
bench-quick:
	cd $(CPYTHON) && ./python ../benchmarks/gc_perf_benchmark.py --quick 2>/dev/null \
	    || echo "Note: requires release build (make build-release)"

# --- Cleanup + info ---

.PHONY: clean
clean:
	cd $(CPYTHON) && $(MAKE) distclean 2>/dev/null || true

.PHONY: verify
verify:
	@echo "--- Build info ---"
	@cd $(CPYTHON) && ./python --version 2>&1 || echo "  (no built python yet)"
	@cd $(CPYTHON) && ./python -c "import sys; print('  GIL enabled:', sys._is_gil_enabled() if hasattr(sys,'_is_gil_enabled') else True)" 2>/dev/null || true
	@cd $(CPYTHON) && ./python -c "import gc; print('  parallel GC:', gc.get_parallel_config())" 2>/dev/null || true
