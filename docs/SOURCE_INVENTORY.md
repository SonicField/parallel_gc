# Current CPython Port Source Inventory

This inventory describes every modified or untracked path in
`cpython/` relative to its recorded `python/cpython` main base,
`333071231d3a46cccc32d7f44b99328c3299d0b1`. It excludes archived project
material outside the submodule.

The current fork commit is
`84be8d65bef72ff98c68a0e6523503ff039b21c8`. Status notation used when the
snapshot was prepared:

- **Modified**: file from the `python/cpython` base changed by the port.
- **New**: file added by the port.
- **Generated**: output that must remain synchronized with its authoritative
  source through CPython's canonical regeneration workflow.

## Collector engines and shared primitives

- **Modified** `Include/internal/mimalloc/mimalloc/internal.h` — declares the
  abandoned-pool page visitor and page-count helpers needed to include pages
  owned by exited threads in free-threaded collection.
- **Modified** `Include/internal/pycore_gc.h` — carries the baseline source
  layout change; worker limits and work-partitioning constants live in the
  implementation-specific parallel-GC headers.
- **New** `Include/internal/pycore_gc_barrier.h` — provides checked POSIX/Windows
  mutex and condition-variable wrappers and the reusable GIL-pool startup
  barrier.
- **New** `Include/internal/pycore_gc_ft_parallel.h` — defines free-threaded
  worker-pool, page-bucket, work-descriptor, marking, lifecycle, and child-fork
  recovery interfaces.
- **New** `Include/internal/pycore_gc_parallel.h` — defines GIL collector state,
  workers, phases, split vectors, and lifecycle, collection, and child-fork
  recovery interfaces.
- **New** `Include/internal/pycore_gc_random_walk.h` — defines the shared
  stochastic random-walk worker-count controller and reset operation.
- **New** `Include/internal/pycore_ws_deque.h` — implements the shared Chase-Lev
  deque and the GIL collector's local work buffer.
- **Modified** `Objects/mimalloc/segment.c` — implements enumeration and counting
  of non-empty abandoned mimalloc pages by heap tag.
- **New** `Python/gc_free_threading_parallel.c` — implements page bucketing, the
  free-threaded persistent pool, parallel root propagation, `update_refs`,
  `mark_heap`, and `scan_heap`, work stealing, and error propagation.
- **New** `Python/gc_parallel.c` — implements the GIL persistent worker pool,
  split-vector dispatch, parallel interpreter-root marking, reference
  subtraction and reachability marking, serial fallback support, and adaptive
  worker selection.

## Core collector integration and lifecycle

- **Modified** `Include/internal/pycore_interp_structs.h` — adds per-interpreter
  parallel-GC state for the GIL and free-threaded implementations.
- **Modified** `Python/gc.c` — integrates split recording, candidate counting,
  interpreter-root pre-marking, reference subtraction, reachability marking,
  the small-collection serial threshold,
  private adaptive timing, and serial fallback into the GIL cyclic collector.
- **Modified** `Python/gc_free_threading.c` — integrates parallel root
  propagation, page assignment, `update_refs`, `mark_heap`, `scan_heap`, and
  private adaptive timing while retaining serial fallbacks and serial stack,
  finalization, and cleanup processing.
- **Modified** `Python/pylifecycle.c` — starts configured pools during main
  interpreter initialization and finalizes pools before interpreter thread-state
  teardown.
- **Modified** `Python/pystate.c` — makes interpreter clearing defensively
  finalize any remaining per-interpreter parallel-GC pool.
- **Modified** `Modules/posixmodule.c` — replaces inherited parallel-GC pools
  in the child before user after-fork callbacks run.
- **Modified** `Include/internal/pycore_uniqueid.h` and `Python/uniqueid.c` —
  provide the stop-the-world batch unique-ID release used by parallel
  free-threaded `scan_heap`.
- **Modified** `Objects/object.c` — restores the baseline explanatory comment
  around cross-thread queued-reference handling; it does not alter behavior.

## Public API and runtime configuration

- **Modified** `Lib/sysconfig/__init__.py` — includes `Py_PARALLEL_GC` in the
  non-POSIX configuration-variable export path.
- **Modified** `Modules/_sysconfig.c` — exposes the compiled `Py_PARALLEL_GC`
  value through `sysconfig`.
- **Modified** `Modules/gcmodule.c` — implements `gc.enable_parallel()`,
  `gc.disable_parallel()`, `gc.get_parallel_config()`,
  `gc.get_parallel_stats()`, and `gc.collect_async()`. `enable_parallel()`
  takes no worker-count argument; the internal maximum is 16 and the adaptive
  controller selects the active count.

There is no environment-variable, `-X`, or `PyConfig` startup interface for
parallel GC.

## Build-system inputs and generated outputs

- **Modified** `Makefile.pre.in` — adds both collector implementation objects to
  POSIX builds.
- **Modified** `Modules/Setup.stdlib.in` — adds the deque/primitives test source
  to `_testinternalcapi`.
- **Modified** `configure.ac` — defines `--with-parallel-gc`, emits
  `Py_PARALLEL_GC`, and rejects 32-bit targets. This is the authoritative
  Autoconf input.
- **Modified, generated** `configure` — canonically regenerated Autoconf output
  containing the feature option and macro definition.
- **Modified, generated** `pyconfig.h.in` — `autoheader` output containing the
  `Py_PARALLEL_GC` template definition.
- **Modified, generated** `Modules/clinic/gcmodule.c.h` — Argument Clinic output
  for the five no-argument public `gc` functions.
- **Modified, generated** `Include/internal/pycore_global_objects_fini_generated.h`
  — generated static
  identifier finalization/check entry for `num_workers`.
- **Modified, generated section** `Include/internal/pycore_global_strings.h` —
  adds `num_workers` to the identifier table generated by
  `Tools/build/generate_global_objects.py`.
- **Modified, generated** `Include/internal/pycore_runtime_init_generated.h` —
  generated runtime
  initializer entry for the `num_workers` identifier.
- **Modified, generated** `Include/internal/pycore_unicodeobject_generated.h` —
  generated static-Unicode
  initialization entry for the `num_workers` identifier.

## Tests and test support

- **Modified** `Lib/test/support/__init__.py` — exposes a `Py_PARALLEL_GC` build
  capability flag to Python tests.
- **Modified** `Lib/test/test_capi/test_config.py` — checks the exported build
  configuration value.
- **Modified** `Lib/test/test_embed.py` — checks that parallel-GC support is
  absent from the startup configuration surface.
- **Modified** `Lib/test/test_free_threading/test_gc.py` — adds regression
  coverage for collecting cycles allocated by threads whose mimalloc pages have
  become abandoned.
- **New** `Lib/test/test_gc_ft_parallel.py` — covers free-threaded graph
  correctness, concurrent collection/allocation, abandoned pages, and pool
  lifecycle/reconfiguration.
- **New** `Lib/test/test_gc_parallel.py` — covers the public API, feature-off
  behavior, worker validation, timing statistics, abandoned pages, concurrent
  allocation, and serial/parallel equivalence.
- **New** `Lib/test/test_gc_parallel_mark_alive.py` — covers GIL interpreter-root
  marking and graph reachability cases.
- **New** `Lib/test/test_gc_parallel_fork.py` — covers ordinary and finalizer
  forks, parent-state preservation, child controller reset, and child
  collection in both collector builds.
- **New** `Lib/test/test_gc_parallel_properties.py` — exercises shared graph
  invariants, split boundaries, helper participation, worker counts, and
  repeated reconfiguration.
- **New** `Lib/test/test_gc_ws_deque.py` — exercises deque, local-buffer,
  barrier, split-vector, concurrency, and allocation-failure behavior through
  `_testinternalcapi`.
- **Modified** `Modules/_testinternalcapi.c` — registers the deque/primitives
  test part.
- **Modified** `Modules/_testinternalcapi/parts.h` — declares its initialization
  entry point.
- **New** `Modules/_testinternalcapi/test_ws_deque.c` — provides low-level deque
  ordering, growth, OOM, reset, and concurrent owner/thief test hooks.

## Windows platform integration

- **Modified** `PCbuild/build.bat` — adds `--parallel-gc`, propagates the MSBuild
  property, and rejects 32-bit Windows targets.
- **Modified** `PCbuild/pyproject.props` — converts the `ParallelGC` MSBuild
  property into the `Py_PARALLEL_GC` preprocessor definition.
- **Modified** `PCbuild/pythoncore.vcxproj` — adds both collector sources and all
  new internal headers to the Windows core project.
- **Modified** `PCbuild/pythoncore.vcxproj.filters` — places those collector
  sources and headers in the corresponding Visual Studio filters.
- **Modified** `PCbuild/_freeze_module.vcxproj` and
  `PCbuild/_freeze_module.vcxproj.filters` — compile and classify both collector
  sources in the bootstrap executable.
- **Modified** `PCbuild/_testinternalcapi.vcxproj` — adds the deque/primitives C
  test part to the Windows `_testinternalcapi` project.
- **Modified** `PCbuild/_testinternalcapi.vcxproj.filters` — places that C test
  part in the Visual Studio source filter.

## CPython documentation

- **Modified** `Doc/library/gc.rst` — documents the five experimental `gc`
  functions and their availability and worker-count contracts.
- **Modified** `Doc/using/configure.rst` — documents the
  `--with-parallel-gc` build option and runtime API opt-in.

## Path-set verification

At commit `84be8d65be`, the source differs from the recorded upstream base at
53 paths: 39 modified files and 14 additions. The CPython worktree was clean
when that revision was recorded in the parent repository.

The only classification ambiguity is
`Include/internal/pycore_global_strings.h`: the file contains hand-maintained
scaffolding around a generated identifier section, while this port changes only
that generated section. It is therefore labeled **generated section**, rather
than treating the whole file as generated.
