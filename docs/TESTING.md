# Testing Strategy

This document describes **what to test, why, and how to interpret results** for the parallel GC. For the underlying build/test commands, see [BUILD_AND_TEST.md](BUILD_AND_TEST.md). For benchmarks specifically, see [BENCHMARKING.md](BENCHMARKING.md).

The terminal goal is upstream CPython PR submission. A CPython core reviewer must be able to verify the project end-to-end without asking questions. The single-command entry point is the [`Makefile`](../Makefile) at the project root.

## Single-command verification

For a reviewer or a developer wanting to know "is this change OK":

```bash
make gate-all   # Build both GIL and FTP, run full test suite for each
```

This is the gate. If it passes, the change is correct enough to consider for merge. If it fails, the failure is the reviewer's signal.

For faster iteration during development, use the narrower gates:

```bash
make gate-gil   # GIL build only
make gate-ftp   # FTP build only
```

## Test categories

Five categories, ordered by what they prove.

### 1. Core GC tests (`make test-gc` → `test_gc`)

The upstream CPython GC test suite, run unmodified. Proves that **adding parallel GC has not regressed the serial GC path**. Must pass in every build mode.

**What passing means**: serial GC behaves identically to vanilla CPython.
**What failing means**: parallel-GC code (or build configuration) has broken a guarantee of the serial GC. Treat as a P0 regression.

### 2. Parallel-GC algorithm tests

Test files that exercise the parallel-GC implementation itself.

| Test file | Build | What it proves |
|-----------|-------|----------------|
| `test_gc_ws_deque` | both | Chase-Lev work-stealing deque correctness — the algorithmic foundation. 11 tests including concurrent push/steal. |
| `test_gc_parallel_mark_alive` | GIL only | mark_alive pre-marking optimisation correctness — root collection, finaliser interaction, type cycles. 22 tests. |
| `test_gc_parallel` | FTP only | Parallel GC public API, enable/disable, phase timing, mixed scenarios. 35 tests. |
| `test_gc_ft_parallel` | FTP only | FTP-specific internals — page counting, parallel marking, cross-thread refs. 30 tests. |
| `test_gc_parallel_properties` | FTP only | Property-based: cycles collected, reachables survive, worker stats consistent. 16 tests, each iterates 100×. |

Run as a group: `make test-parallel`.

**Naming caveat (Phase 4 followup):** the names are inconsistent. `test_gc_parallel` is FTP-only despite no `_ft` prefix; `test_gc_ft_parallel` is named as FTP-only but runs build-agnostic tests too; `test_gc_parallel_mark_alive` is GIL-only despite no `_gil` prefix. The build/skip behaviour is enforced by `setUpModule()` in each file. A future renaming pass should make this explicit, e.g. `test_gc_parallel_gil_mark_alive`, `test_gc_parallel_ftp_pages`, `test_gc_parallel_common_ws_deque`.

**What passing means**: the parallel GC implements its declared contract correctly.
**What failing means**: depends — see the categories below.

### 3. Full CPython suite (`make test-all` → `python -m test`)

Runs every test CPython ships with. ~48,000 tests; ~1–2 minutes on a 192-core host, ~30 minutes typical desktop.

**What passing means**: parallel GC has not regressed any CPython functionality and has not introduced incompatibilities visible from Python-level tests.

**What failing means**: depends — the failure is the signal. Common modes:
- **Help-text or env-var snapshot tests** (e.g. `test_cmd_line`) failing: parallel GC added a new env var or `-X` option in the wrong alphabetical position. Fix the source ordering in `Python/initconfig.c`.
- **Test runner crashes** (e.g. `test_capi`): a parallel-GC test helper triggers an assertion outside its intended subprocess context. The helper must be renamed to avoid `test_capi`'s auto-discovery (prefix with `unsafe_`).
- **Threading/concurrency tests** failing: most likely a real bug in the parallel GC. Re-run under TSan (`make build-tsan && make test-parallel`).

### 4. Sanitiser gate (`make build-asan` or `make build-tsan` + tests)

Address Sanitizer and Thread Sanitizer builds. TSan is the most important — parallel GC is inherently concurrent and Python's reference counting layered with worker threads + work-stealing deque is exactly what TSan was designed to catch.

```bash
make build-tsan
make test-parallel
```

**What passing means**: no data races detectable under TSan; no use-after-free, double-free, or buffer errors detectable under ASan (when run with `make build-asan`).

**What failing means**: a real concurrency or memory bug. Stop. Do not paper over it with locks or "fix" by suppressing the report. Read the TSan/ASan output and find the root cause.

**Build cost**: sanitiser builds require `make distclean` and full rebuild (~10 min on typical hardware, ~1 min on 192-core). Switching back to a non-sanitiser build also requires `make distclean`. This is by design — sanitisers change the ABI.

### 5. Benchmark gate (`make bench-quick` for sanity; full procedure in BENCHMARKING.md)

Confirms the parallel GC actually delivers a speedup and that recent changes have not regressed performance. See [BENCHMARKING.md](BENCHMARKING.md) for the full procedure.

**Required for**: any change touching `gc_parallel.c`, `gc_free_threading_parallel.c`, the dispatch path, or the work-stealing deque. Recommended for: any other parallel-GC-touching change.

**What passing means**: speedup within tolerance of published numbers (1.23×–2.33× on supported workloads, −54% to −67% STW pause reduction).
**What failing means**: performance regression. May or may not block merge depending on whether the change is a correctness fix worth the cost — but the regression must be measured and discussed, not hidden.

## Decision matrix: what must pass before merge

| Change scope | Required gates |
|--------------|----------------|
| Documentation only | (none — text changes only) |
| Test code only | `make test-parallel` on the affected build |
| Build-system change | `make gate-all` |
| Algorithm change to parallel GC | `make gate-all` **and** `make build-tsan && make test-parallel` **and** benchmark check (see BENCHMARKING.md) |
| Public API change (`gc.enable_parallel`, etc.) | `make gate-all` **and** updated tests in `test_gc_parallel*.py` **and** doc update |
| Upstream PR submission | `make gate-all` **and** sanitiser builds clean **and** benchmark numbers re-published |

## Reproducibility

Property-based tests use a seed. Reproduce a failure by setting `GC_TEST_SEED`:

```bash
GC_TEST_SEED=12345 cd cpython && ./python -m test test_gc_parallel_properties -v
```

The seed is printed on every test run. Capture it from a CI log if you need to reproduce a failure that happened elsewhere.

## What the strategy does NOT cover yet

Honest list of gaps a reviewer would identify:

- **No CI configuration.** The strategy assumes a developer runs `make gate-all` manually. An upstream PR would benefit from a GitHub Actions workflow that runs at least `gate-gil` and `gate-ftp` on each push, and `build-tsan + test-parallel` on a slower nightly cadence.
- **Test naming is inconsistent** (see Category 2 above). A reviewer will trip over `test_gc_parallel` being FTP-only.
- **No coverage measurement.** We can run all the tests but cannot say what percentage of parallel-GC code paths are exercised. A coverage gate would be valuable but requires extra build configuration.
- **Sanitiser tests are not automated end-to-end.** `make build-tsan` builds; the developer must remember to also run `make test-parallel` after.
- **Benchmark gates are not enforced numerically.** BENCHMARKING.md describes how to run them; no CI tooling compares results to a published baseline yet.

These are all addressable. They are documented here so a reviewer knows the boundary of what has been claimed.
