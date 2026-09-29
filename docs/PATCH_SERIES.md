# Proposed CPython Patch Series

This is the proposed review order for the `cpython/` submodule commit. The
published fork currently contains one snapshot commit; it can be split into
this dependency order before any proposal to `python/cpython`. Generated files
must first be regenerated canonically, and every resulting commit must pass
both GIL and free-threaded builds.
The complete path-by-path scope is listed in
[SOURCE_INVENTORY.md](SOURCE_INVENTORY.md).

## 1. Work-stealing primitives and tests

Add `pycore_ws_deque.h` and `pycore_gc_barrier.h`, together with their
`_testinternalcapi` coverage and build-system registration. The deque is shared
by both collectors; the local-buffer helpers and startup barrier are used by
the GIL collector.

## 2. GIL collector

Add the GIL worker pool, split-vector support, parallel reference subtraction,
parallel reachability marking, serial fallback, and integration with `gc.c`.
Keep this patch dormant behind `Py_PARALLEL_GC`.

## 3. Mimalloc page enumeration

Add the two internal abandoned-pool page-iteration helpers used by the
free-threaded collector. Keep this separate so allocator maintainers can review
the mimalloc boundary independently.

## 4. Free-threaded collector

Add page bucketing, the persistent pool, parallel `mark_heap`, work stealing,
outstanding-work termination, error recovery, and integration with the
existing serial root, update, scan, and cleanup phases. Keep this patch dormant
behind both `Py_GIL_DISABLED` and `Py_PARALLEL_GC`.

## 5. Configuration and lifecycle

Add `--with-parallel-gc`, `PyConfig.parallel_gc_workers`, `-X parallel_gc=N`,
`PYTHON_PARALLEL_GC`, the `gc` control/configuration functions, interpreter
startup and shutdown, sysconfig exposure, Windows build support, generated
Clinic output, and generated global-string files.

## 6. Fork safety

Quiesce every interpreter's pool before `fork()`, restart parent pools before
resuming Python threads, and leave child pools disabled until explicitly
re-enabled.

## 7. Integration and regression tests

Add API/configuration tests, deque and split-vector tests, GIL/FT graph
properties, lifecycle and reconfiguration tests, allocation/collection races,
external-inspection coverage, helper-participation proof, and fork behavior.

## 8. Documentation and NEWS

Add the configure, command-line, `PyConfig`, and `gc` documentation after the
interface is agreed. Add the NEWS fragment only after a CPython issue number is
assigned; do not invent one for the draft series.

## Cross-patch rules

- Split shared files by hunk rather than mixing the collector engines.
- Keep `configure` with `configure.ac` and regenerate it using CPython's
  canonical container.
- Keep Clinic output and generated global-string headers with their source
  changes.
- Preserve CRLF in Visual Studio project files.
- Build and run the focused suite in all four GIL/free-threaded,
  feature-on/feature-off configurations after every applicable patch.
- Do not include removed experiments or public telemetry in the series.
