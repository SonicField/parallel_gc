# Proposed CPython Patch Series

This is a proposed dependency order for a later submission series, not the
current Git history. The fork at `c67363fa59` contains the initial snapshot
plus separate repair, test and performance commits. Preparing a buildable
review series remains future work and is not required for the informal review.
Generated files must be verified through their canonical generators, and every
applicable resulting commit must build in GIL and FT configurations.
The complete path-by-path scope is listed in
[SOURCE_INVENTORY.md](SOURCE_INVENTORY.md).

## 1. Work-stealing primitives and tests

Add `pycore_ws_deque.h` and `pycore_gc_barrier.h`, together with their
`_testinternalcapi` coverage and build-system registration. The deque is shared
by both collectors; the local-buffer helpers and synchronization wrappers are
used by the GIL collector. Its lifecycle uses those wrappers for a cancellable
startup handshake rather than a fixed participant barrier.

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

Add page bucketing, the lazy persistent pool, parallel root propagation,
`update_refs`, `mark_heap`, and `scan_heap`, work stealing, error recovery,
unique-ID batching, and integration with the serial fallback and cleanup
paths. Keep this patch dormant behind both `Py_GIL_DISABLED` and
`Py_PARALLEL_GC`.

## 5. Configuration and lifecycle

Add `--with-parallel-gc`, the no-argument `gc` control, configuration,
statistics, and asynchronous-collection functions, interpreter shutdown,
lazy startup, warning/fallback/retry, sysconfig exposure, Windows build support,
generated Clinic output, and
generated global-string files. The worker ceiling is the internal constant 16;
there is no startup worker-count interface. The public API set should be agreed
before this patch is prepared.

## 6. Fidelity and lifecycle tests

Restore the original lifecycle, configuration, graph-correctness, abandoned
page, adaptive-worker, and low-level primitive tests. Add the shared GIL/FT
fork regressions for ordinary and finalizer forks, parent-state preservation,
child controller reset, and post-fork collection.

## 7. Integration and regression validation

Add API/configuration tests, deque and split-vector tests, GIL/FT graph
properties, lifecycle and reconfiguration tests, allocation/collection races,
external-inspection coverage, and helper-participation proof. Validate the
fork protocol through CPython's supported hooks: armed child recovery for GIL,
and FT, with lifecycle ordering before stop-the-world and an inherited
collection forced serial in the child.

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
- Keep unrelated experiments outside the series. Decide the diagnostic API
  scope explicitly; the discussion PEP currently includes provisional stats
  and excludes `gc.collect_async()`.
