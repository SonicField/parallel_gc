# Parallel-GC header dependency repair

16 October 2026. CPython `388fd5bb46fdda6b464db566faf818505c3d6eef` adds five existing internal headers to `PYTHON_HEADERS` in `Makefile.pre.in`. It follows the existing dependency mechanism and changes no collector code.

## Reproduction and repair

Extending a debug diagnostic structure during verifier integration left stale objects in an incremental build: a participant count was 64 instead of 4 and a lifecycle test crashed. Clean builds passed. Before this repair, `make -n -W <header> <GC-object>` scheduled no compilation for any of the five new headers in either GIL or FT debug builds. The existing `pycore_gc.h` dependency scheduled compilation in both. All twelve checks behaved that way, as recorded in `header-dependencies-before.log`.

The omitted headers were `pycore_gc_barrier.h`, `pycore_gc_ft_parallel.h`, `pycore_gc_parallel.h`, `pycore_gc_random_walk.h` and `pycore_ws_deque.h`. Adding their paths to the existing sorted list makes all five trigger recompilation, alongside the existing control: twelve checks pass in `header-dependencies-after.log`. These checks do not modify a header or rely on timestamp sleeps.

The verification script initially requested `config.status Makefile`, which CPython rejects: its configured intermediate is `Makefile.pre`. The corrected script uses the existing `make Makefile` regeneration rule. No configure or build-rule change was needed beyond the five prerequisites.

## Actual rebuild and tests

Each of four feature-on builds regenerated its Makefile, compiled its active parallel-GC object using `make -W .../pycore_gc_random_walk.h` with unused-function/variable error flags, relinked, and passed the focused suite. Both feature-off debug controls performed the same dependency-driven rebuild for `Python/gc.o` and passed. The `*-compile.log` files show actual compiler commands, not just dry runs.

| Configuration | Runner summary: run / skipped | Result |
|---------------|-------------------------------|--------|
| GIL release | 349 / 88 | SUCCESS |
| FT release | 377 / 77 | SUCCESS |
| GIL debug | 349 / 85 | SUCCESS |
| FT debug | 377 / 40 | SUCCESS |
| GIL feature-off debug | 314 / 125 | SUCCESS |
| FT feature-off debug | 377 / 160 | SUCCESS |

ARM64 Linux, GCC 11.5.0, non-PGO/non-LTO builds. These reuse the complete clean builds from the [verifier report](../production-verifier-integration-2026-10-16/README.md), then rebuild for this five-line dependency change. The tracked scratch source content matches `388fd5bb46`; its version stamp still identifies its detached dirty baseline. Selections include GC, lifecycle/fork, deque, marking/properties, PGO-workload, configuration and embedding tests; FT includes its upstream GC tests. Optional-module and ctypes limits remain those recorded in the verifier report. The debug FT startup assertion still emits its pre-existing signedness warning; the focused gate rejects unused functions/variables, not every warning. This warning occurs in the pre-integration baseline too and was not changed here.

`header_dependencies.py`, `header_repair.sh` and `header_controls.sh` retain exact commands; use fresh isolated source/build directories and replace their explicit scratch root when reproducing. Configuration, compilation, build and test logs are retained for all six configurations. The sanitizer runs remain evidence for `0fc7b3ccb9`, not reruns for this dependency-only commit. No performance or hosted-CI claim is made.

Raw build output retains its original trailing whitespace. Whitespace checks apply separately to new documentation and scripts; the logs are not rewritten to satisfy a formatting check.

The GIL feature-off object also emits the pre-existing unused `move_unreachable` label warning. `Python/gc.c` is unchanged by integration; this remains an A10 follow-up rather than an unreported all-warning pass.
