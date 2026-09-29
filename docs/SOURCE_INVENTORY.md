# Current CPython Port Source Inventory

This inventory describes every modified or untracked path in
`cpython/` relative to its recorded `python/cpython` main base,
`333071231d3a46cccc32d7f44b99328c3299d0b1`. It excludes archived project
material outside the submodule.

The published fork commit is
`9da963f754f747d64a6db4112efa2a2ef8bde111`. Status notation used when the
snapshot was prepared:

- **Modified**: file from the `python/cpython` base changed by the port.
- **New**: file added by the port.
- **Generated**: output that must remain synchronized with its authoritative
  source through CPython's canonical regeneration workflow.

## Collector engines and shared primitives

- **Modified** `Include/internal/mimalloc/mimalloc/internal.h` — declares the
  abandoned-pool page visitor and page-count helpers needed to include pages
  owned by exited threads in free-threaded collection.
- **Modified** `Include/internal/pycore_gc.h` — defines the shared worker-count
  limits and 8192-object work grain used by both implementations.
- **New** `Include/internal/pycore_gc_barrier.h` — provides checked POSIX/Windows
  mutex and condition-variable wrappers and the reusable GIL-pool startup
  barrier.
- **New** `Include/internal/pycore_gc_ft_parallel.h` — defines free-threaded
  worker-pool, page-bucket, work-descriptor, marking, and lifecycle interfaces.
- **New** `Include/internal/pycore_gc_parallel.h` — defines GIL collector state,
  workers, phases, split vectors, and lifecycle/collection interfaces.
- **New** `Include/internal/pycore_ws_deque.h` — implements the shared Chase-Lev
  deque and the GIL collector's local work buffer.
- **Modified** `Objects/mimalloc/segment.c` — implements enumeration and counting
  of non-empty abandoned mimalloc pages by heap tag.
- **New** `Python/gc_free_threading_parallel.c` — implements page bucketing, the
  free-threaded persistent pool, parallel `mark_heap`, work stealing, error
  propagation, and fork hooks.
- **New** `Python/gc_parallel.c` — implements the GIL persistent worker pool,
  split-vector dispatch, parallel reference subtraction and reachability
  marking, serial fallback support, and fork hooks.

## Core collector integration and lifecycle

- **Modified** `Include/internal/pycore_interp_structs.h` — adds per-interpreter
  parallel-GC state for the GIL and free-threaded implementations.
- **Modified** `Modules/posixmodule.c` — quiesces every interpreter's pool before
  `fork()`, restarts parent pools, and disables inherited child pools.
- **Modified** `Python/gc.c` — integrates split recording, parallel reference
  subtraction, parallel reachability marking, and serial fallback into the GIL
  cyclic collector.
- **Modified** `Python/gc_free_threading.c` — integrates page assignment and
  optional parallel `mark_heap` while retaining upstream serial root, reference,
  stack, scan, and cleanup processing.
- **Modified** `Python/pylifecycle.c` — starts configured pools during main
  interpreter initialization and finalizes pools before interpreter thread-state
  teardown.
- **Modified** `Python/pystate.c` — makes interpreter clearing defensively
  finalize any remaining per-interpreter parallel-GC pool.

## Public API and runtime configuration

- **Modified** `Include/cpython/initconfig.h` — adds the public
  `PyConfig.parallel_gc_workers` field.
- **Modified** `Lib/sysconfig/__init__.py` — includes `Py_PARALLEL_GC` in the
  non-POSIX configuration-variable export path.
- **Modified** `Modules/_sysconfig.c` — exposes the compiled `Py_PARALLEL_GC`
  value through `sysconfig`.
- **Modified** `Modules/gcmodule.c` — implements `gc.enable_parallel()`,
  `gc.disable_parallel()`, and `gc.get_parallel_config()` for feature-on and
  feature-off builds.
- **Modified** `Python/initconfig.c` — parses and validates
  `PYTHON_PARALLEL_GC`, `-X parallel_gc=N`, and
  `PyConfig.parallel_gc_workers`, including unsupported-build rejection.

## Build-system inputs and generated outputs

- **Modified** `Makefile.pre.in` — adds both collector implementation objects to
  POSIX builds.
- **Modified** `Modules/Setup.stdlib.in` — adds the two parallel-GC internal test
  sources to `_testinternalcapi`.
- **Modified** `configure.ac` — defines `--with-parallel-gc`, emits
  `Py_PARALLEL_GC`, and rejects 32-bit targets. This is the authoritative
  Autoconf input.
- **Modified, generated** `configure` — Autoconf output containing the feature
  option and macro definition; canonical regeneration is still required to pick
  up all current `configure.ac` changes.
- **Modified, generated** `pyconfig.h.in` — `autoheader` output containing the
  `Py_PARALLEL_GC` template definition.
- **Modified, generated** `Modules/clinic/gcmodule.c.h` — Argument Clinic output
  for the three public `gc` functions and the `num_workers` argument parser.
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
- **Modified** `Lib/test/test_capi/test_config.py` — verifies that
  `parallel_gc_workers` is present in the public configuration schema.
- **Modified** `Lib/test/test_embed.py` — drives embedded-runtime tests for valid
  and invalid `PyConfig.parallel_gc_workers` startup values.
- **Modified** `Lib/test/test_free_threading/test_gc.py` — adds regression
  coverage for collecting cycles allocated by threads whose mimalloc pages have
  become abandoned.
- **New** `Lib/test/test_gc_ft_parallel.py` — covers free-threaded graph
  correctness, concurrent collection/allocation, abandoned pages, and pool
  lifecycle/reconfiguration.
- **New** `Lib/test/test_gc_parallel.py` — covers the public API, feature-off
  behavior, startup controls, worker validation, fork restart, and subinterpreter
  lifecycle.
- **New** `Lib/test/test_gc_parallel_properties.py` — exercises shared graph
  invariants, split boundaries, helper participation, worker counts, and
  repeated reconfiguration.
- **New** `Lib/test/test_gc_ws_deque.py` — exercises deque, local-buffer,
  barrier, split-vector, concurrency, and allocation-failure behavior through
  `_testinternalcapi`.
- **Modified** `Modules/_testinternalcapi.c` — registers the new parallel-GC and
  deque/primitives test parts.
- **Modified** `Modules/_testinternalcapi/parts.h` — declares initialization
  entry points for those two test parts.
- **New** `Modules/_testinternalcapi/test_parallel_gc.c` — provides low-level
  barrier, local-buffer, split-vector, stack-reference, and helper-traversal test
  hooks.
- **New** `Modules/_testinternalcapi/test_ws_deque.c` — provides low-level deque
  ordering, growth, OOM, reset, and concurrent owner/thief test hooks.
- **Modified** `Programs/_testembed.c` — implements embedded-startup probes for
  accepted, invalid, and unsupported parallel-GC configuration.

## Windows platform integration

- **Modified** `PCbuild/build.bat` — adds `--parallel-gc`, propagates the MSBuild
  property, and rejects 32-bit Windows targets.
- **Modified** `PCbuild/pyproject.props` — converts the `ParallelGC` MSBuild
  property into the `Py_PARALLEL_GC` preprocessor definition.
- **Modified** `PCbuild/pythoncore.vcxproj` — adds both collector sources and all
  new internal headers to the Windows core project.
- **Modified** `PCbuild/pythoncore.vcxproj.filters` — places those collector
  sources and headers in the corresponding Visual Studio filters.
- **Modified** `PCbuild/_testinternalcapi.vcxproj` — adds both new C test parts to
  the Windows `_testinternalcapi` project.
- **Modified** `PCbuild/_testinternalcapi.vcxproj.filters` — places those C test
  parts in the Visual Studio source filter.

## CPython documentation

- **Modified** `Doc/c-api/init_config.rst` — documents
  `PyConfig.parallel_gc_workers`, its limits, activation semantics, and
  unsupported-build behavior.
- **Modified** `Doc/library/gc.rst` — documents the three experimental `gc`
  functions and their availability and worker-count contracts.
- **Modified** `Doc/using/cmdline.rst` — documents `-X parallel_gc=N` and
  `PYTHON_PARALLEL_GC` startup behavior.
- **Modified** `Doc/using/configure.rst` — documents the
  `--with-parallel-gc` build option and runtime opt-in controls.

## Path-set verification

At the time of this inventory, `git status --porcelain=v1` reports 53 paths:
41 modified tracked files and 12 untracked additions. The 53 paths above occur
exactly once and are the complete status set relative to `upstream/main`.

The only classification ambiguity is
`Include/internal/pycore_global_strings.h`: the file contains hand-maintained
scaffolding around a generated identifier section, while this port changes only
that generated section. It is therefore labeled **generated section**, rather
than treating the whole file as generated.
