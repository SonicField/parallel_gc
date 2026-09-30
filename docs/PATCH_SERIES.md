# Proposed CPython Patch Series

This is the proposed review order for the `cpython/` submodule commit. The
fork currently contains one snapshot implementation commit; it can be split into
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

Add the GIL worker pool, split-vector support, parallel interpreter-root
marking, reference subtraction, reachability marking, serial fallback, and
integration with `gc.c`. Include the 16,384-candidate serial threshold and the
pre-mark deque-draining regression test. Keep this patch dormant behind
`Py_PARALLEL_GC`.

## 3. Mimalloc page enumeration

Add the two internal abandoned-pool page-iteration helpers used by the
free-threaded collector. Keep this separate so allocator maintainers can review
the mimalloc boundary independently.

## 4. Free-threaded collector

Add page bucketing, the persistent pool, parallel root propagation,
`update_refs`, `mark_heap`, and `scan_heap`, work stealing, error recovery,
unique-ID batching, and integration with the serial fallback and cleanup
paths. Keep this patch dormant behind both `Py_GIL_DISABLED` and
`Py_PARALLEL_GC`.

## 5. Configuration and lifecycle

Add `--with-parallel-gc`, the no-argument `gc` control, configuration,
statistics, and asynchronous-collection functions, interpreter shutdown,
sysconfig exposure, Windows build support, generated Clinic output, and
generated global-string files. The worker ceiling is the internal constant 16;
there is no startup worker-count interface. The public API set should be agreed
before this patch is prepared.

## 6. Fidelity and lifecycle tests

Restore the original lifecycle, configuration, graph-correctness, abandoned
page, adaptive-worker, and low-level primitive tests. Fork behavior remains a
validation item; the restored implementation does not add special fork hooks.

## 7. Integration and regression validation

Add API/configuration tests, deque and split-vector tests, GIL/FT graph
properties, lifecycle and reconfiguration tests, allocation/collection races,
external-inspection coverage, and helper-participation proof. Validate fork
behavior without claiming an implementation protocol that is not present.

## 8. Documentation and NEWS

Add the configure and `gc` documentation after the interface is agreed. The
current proposal deliberately adds no environment variable, command-line
option, or `PyConfig` field. Add the NEWS fragment only after a CPython issue
number is assigned; do not invent one for the draft series.

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
