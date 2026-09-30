# Parallel GC Port Fidelity Ledger

This ledger governs the port from the tested prototype to current CPython.

The GIL integration mapping is documented separately in
`docs/GIL_PORT_CALLSITE_MAPPING.md`.

## Immutable references

- Design and behavioural baseline:
  `beb2907f8d723d7a202d068cb7de69448c53ff7e`
- Baseline's upstream comparison point:
  `2e64e36a2b1f8ebb2a6f24ad5c8f75388047d039`
- Current port under audit:
  `323d3cc90adcc5dcc799f79812edd339b347a46c`
- Port's upstream parent:
  `333071231d3a46cccc32d7f44b99328c3299d0b1`

## Fidelity rule

The port must preserve every algorithmic phase, synchronization choice,
atomic invariant, adaptive mechanism, API behaviour, diagnostic, and test in
the baseline. Code cleanup may change presentation only, never behaviour.

An upstream incompatibility is a hard blocker. It must be documented and
discussed with Alex before any adaptation is designed or implemented. Passing
new tests or CPython CI is not evidence of parity with the baseline.

## Status meanings

- **MATCH**: equivalence has been demonstrated from source and tests.
- **MISSING**: baseline functionality or coverage is absent from the port.
- **CHANGED**: both exist, but behaviour or implementation semantics differ.
- **BLOCKED**: current upstream prevents a direct port; no resolution is
  authorized until discussed.
- **UNAUDITED**: comparison is not complete.

## Restoration status

| Area | Baseline | Current port | Status |
|---|---|---|---|
| Worker selection | Shared adaptive worker controller for GIL and FT | Restored | MATCH |
| GIL root marking | Parallel root/queue marking paths | Restored | MATCH |
| FT root propagation | Parallel pool phase | Restored | MATCH |
| FT `update_refs` | Parallel pool phase | Restored | MATCH |
| FT `scan_heap` | Parallel pool phase | Restored | MATCH |
| Async collection | `gc.collect_async()` | Restored | MATCH |
| Statistics | `gc.get_parallel_stats()` with phase timing | Restored | MATCH |
| Configuration reporting | Includes adaptive count and FT cleanup capability | Restored | MATCH |
| Reconfiguration | Baseline GIL and FT contracts | Restored | MATCH |
| Environment option | `PYTHONPARALLELGC` | Restored | MATCH |
| `PyConfig` field | `parallel_gc` | Restored | MATCH |
| Startup worker range | 0 through 256 | Restored | MATCH |
| Resizable barrier | `_PyGCBarrier_Resize` supports adaptive FT dispatch | Restored | MATCH |
| Deque backing store | Preallocated external-buffer initialization/finalization | Restored | MATCH |
| GIL shared work queue | Block queue and semaphore support parallel root marking | Restored | MATCH |
| Worker thread state | Baseline helper thread-state and accounting fields | Restored | MATCH |
| Deque allocation failure | Baseline fatal behavior | Restored | MATCH |
| Synchronization failures | Baseline native-operation handling | Restored | MATCH |
| Fork lifecycle | No baseline-specific hooks | Reduced-port hooks removed | MATCH |
| GIL mark-alive tests | 34-test dedicated module | Restored exactly | MATCH |
| FT tests | 36 tests in `test_gc_ft_parallel.py` | Restored exactly | MATCH |
| General parallel tests | 35 tests in `test_gc_parallel.py` | Restored exactly | MATCH |
| Property tests | 16 tests | Restored exactly | MATCH |
| Deque tests | 31 tests | Restored exactly | MATCH |

These are discrepancy findings, not decisions about how to resolve them.

## Collector phase map

| Build | Baseline parallel phases | Restored parallel phases | Status |
|---|---|---|---|
| GIL | root/queue mark-alive; `subtract_refs`; `move_unreachable` reachability marking | Same phases | MATCH |
| FT | root propagation; `update_refs`; `mark_heap`; `scan_heap` | Same phases | MATCH |

Serial fallbacks, error paths, and shutdown-specific paths are part of each
baseline phase contract and must be mapped separately.

## Core baseline blobs

These blob identifiers make the intended source exact rather than descriptive:

| Path | Baseline blob | Current-port blob | Status |
|---|---|---|---|
| `Include/internal/pycore_gc_barrier.h` | `f77578d8db82d184788d2c19023a357a007591a1` | `f77578d8db82d184788d2c19023a357a007591a1` | MATCH |
| `Include/internal/pycore_gc_ft_parallel.h` | `816d74deecfcddf6164479de43bc5d8d9d4dcd5e` | `816d74deecfcddf6164479de43bc5d8d9d4dcd5e` | MATCH |
| `Include/internal/pycore_gc_parallel.h` | `b6c9da7225077ba8adb94a515fc6f384cdc739c0` | `b6c9da7225077ba8adb94a515fc6f384cdc739c0` | MATCH |
| `Include/internal/pycore_gc_random_walk.h` | `36fcd08d813de99d07391b781555685aa77c4362` | `36fcd08d813de99d07391b781555685aa77c4362` | MATCH |
| `Include/internal/pycore_ws_deque.h` | `fd268cd416eba16d1e5dea513e191e7a1e899c97` | `fd268cd416eba16d1e5dea513e191e7a1e899c97` | MATCH |
| `Python/gc_free_threading_parallel.c` | `753b9bfb9144b8530ca03c6fe40f7af065c431ab` | `753b9bfb9144b8530ca03c6fe40f7af065c431ab` | MATCH |
| `Python/gc_parallel.c` | `21dd4468d05cc644882a74805eeb047ae9931426` | `5dc28f6833a279493d795f558a42c3efecf17051` | MATCH WITH APPROVED LIST-BIT MAPPING |

The current versions are not accepted as equivalent merely because portions of
their control flow or APIs have the same names.

The baseline patch adds 157 Python test methods across the parallel-GC test
modules and `Lib/test/test_free_threading/test_gc.py`. The current port adds 58
across the corresponding files. The baseline also adds 29 C test/helper entry
points in `Modules/_testinternalcapi/test_ws_deque.c`. New port-side tests do not
count as replacements until their assertions have been mapped individually.

## Candidate upstream blockers requiring reproduction

These were reported while constructing the reduced port, but the failing
intermediate source states were not committed. They are therefore hypotheses,
not authorization for a behavioural change:

| Baseline facility | Reported current-upstream conflict | Required evidence |
|---|---|---|
| GIL interpreter-root pre-mark | Stale/freed pointers appeared in a broad run | Exact baseline path ported unchanged, deterministic reproducer, and failing assertion or sanitizer trace |
| FT parallel root propagation | `validate_gc_objects` assertion | Exact baseline path ported unchanged and minimized failing test |
| FT parallel `update_refs` | `validate_gc_objects` assertion; upstream now lazily initializes referents outside the page walk | Exact baseline path ported unchanged and minimized failing test |
| FT parallel `scan_heap` | Resurrection assertions in `test_crossinterp` and `test_pdb` | Exact baseline path ported unchanged and minimized failing test |
| Helper-owned Python thread states | Reported incompatibility with external thread inspection | Exact test, trace, and upstream invariant that conflict with the baseline design |

Until reproduced, none of these claims permits deletion, serialization, or
replacement of the baseline facility.

## Baseline-modified paths absent from the port delta

- `.gitignore`
- `Include/internal/pycore_gc_random_walk.h`
- `Include/internal/pycore_uniqueid.h`
- `Lib/test/test_gc_parallel_mark_alive.py`
- `Objects/object.c`
- `PCbuild/_freeze_module.vcxproj`
- `PCbuild/_freeze_module.vcxproj.filters`
- `Python/brc.c`
- `Python/uniqueid.c`

Some entries may ultimately prove generated or behaviour-neutral. They remain
in scope until that is demonstrated and explicitly accepted.

## Literal patch applicability

The complete baseline delta was applied without modification in a disposable,
detached worktree at the port's upstream parent. The active branch was not
modified.

- 36 paths apply unchanged.
- 12 paths have textual conflicts and are hard blockers pending inspection.

The conflicted paths are:

- `Include/internal/pycore_global_objects_fini_generated.h`
- `Include/internal/pycore_interp_structs.h`
- `Include/internal/pycore_unicodeobject_generated.h`
- `Modules/Setup.stdlib.in`
- `Modules/_testinternalcapi.c`
- `Modules/_testinternalcapi/parts.h`
- `Modules/clinic/gcmodule.c.h`
- `Python/brc.c`
- `Python/gc.c`
- `Python/gc_free_threading.c`
- `Python/initconfig.c`
- `Python/pylifecycle.c`

A clean textual application is not yet classified as a semantic match. Each of
the 48 paths remains subject to source and test review.

### Conflict classification

No required 3.15-to-current spelling change has been identified. In particular,
the port's `PyConfig.parallel_gc_workers` and `PYTHON_PARALLEL_GC` names were
not forced by upstream; the baseline names apply cleanly.

Nine conflicts are integration-placement conflicts and do not presently imply
an algorithm change:

- three generated files:
  `pycore_global_objects_fini_generated.h`,
  `pycore_unicodeobject_generated.h`, and `Modules/clinic/gcmodule.c.h`;
- three build/test registration files:
  `Modules/Setup.stdlib.in`, `Modules/_testinternalcapi.c`, and
  `Modules/_testinternalcapi/parts.h`;
- `Python/initconfig.c`, where upstream reformatted help text;
- `Python/pylifecycle.c`, where upstream added adjacent includes and lifecycle
  code; and
- `Include/internal/pycore_interp_structs.h`, where upstream changed the GC
  state layout around the baseline fields.

Three conflicts touch runtime algorithms and are hard blockers:

1. `Python/gc.c`: upstream commit `1575a81bf2` replaced the incremental
   collector used by the baseline with the forward-ported generational
   collector. The baseline parallel phase bodies apply unchanged, but their
   invocation and collection-wide timing/adaptation boundaries do not have
   textually identical insertion points.
2. `Python/gc_free_threading.c`: the baseline inherited CPython's RSS-based
   collection-deferral mechanism. Current upstream deliberately removed that
   complete mechanism in `13188dbf85` (GH-148937). Alex approved preserving
   current upstream and not resurrecting this unrelated RSS policy. The
   original parallel timing boundaries and adaptive update remain unchanged.
3. `Python/brc.c`: the baseline only relocates `merge_queued_objects()` without
   changing it. Current upstream replaced that function with separate
   refcount-merge and decref passes plus detached-thread handling in
   `030e913a74`. Alex confirmed that the baseline relocation was accidental and
   is not required. Preserve current upstream; no parallel-GC code depends on
   the old placement or implementation.

## GIL restoration checkpoint (2026-09-30)

The GIL call-site mapping has been implemented locally. One representation
change was discussed and approved: the baseline parallel sweep's
`2 | old_space_bit` list tag is mapped to current upstream's bit-0
`NEXT_MASK_UNREACHABLE` representation. The removed old-space bit belonged to
the retired incremental serial collector and carried no parallel-GC state.

The original GIL worker implementation, adaptive controller, barrier/deque
primitives, mark-alive tests, and standalone test modules have been restored.
The current debug ARM64 GIL build succeeds. The 34 original GIL mark-alive and
adaptive tests, 31 original deque/barrier tests, and 61 applicable upstream
`test_gc` tests pass.

## Free-threaded restoration checkpoint (2026-09-30)

The original FT worker implementation and header are restored byte-for-byte.
The baseline abandoned-page enumeration and unique-ID batching APIs are also
restored byte-for-byte; their absence caused three reproducible compiler
errors before restoration.

The original parallel root propagation, `update_refs`, `mark_heap`, and
`scan_heap` call sites are restored in `Python/gc_free_threading.c`, along with
the original private phase timestamps and adaptive random-walk update. Current
upstream's public `gc.get_stats()` timing remains unchanged.

The current ARM64 free-threaded debug build succeeds. Results so far:

- 35/36 `test_gc_ft_parallel` tests pass; the remaining test cannot import the
  optional `_ctypes` module, which this local build could not build.
- all 35 `test_gc_parallel` tests pass (one expected state-dependent skip);
- all 16 property tests pass;
- all 31 deque/barrier tests pass; and
- all five baseline additions to `test_free_threading.test_gc` pass, alongside
  its seven upstream tests.

The reduced port's single replacement abandoned-pool test has been removed;
all five original baseline tests are present again. The five standalone test
modules match the baseline blobs exactly, accounting for 152 tests, and the
existing FT module contains the baseline's remaining five additions.

This checkpoint is not a final MATCH declaration. The remaining source/build
audit must be resolved first.

## Platform integration decision (2026-09-30)

The current port's Windows build switch, MSBuild definition, `_sysconfig`
reporting, test-project registration, and 64-bit platform checks are retained.
They extend build integration around the unchanged collector rather than
replacing baseline behavior. Alex confirmed that Windows support is required
and that the working implementation must not be reversed merely because those
files were absent from the older baseline patch.

## Audit sequence

1. Account for all 47 baseline-modified paths and all subsequent feature
   commits through `beb2907f8d`.
2. Map every public and internal interface and its exact semantics.
3. Map GIL and FT collector phases, work distribution, termination, atomics,
   barriers, and lifecycle behavior.
4. Restore and map every original Python and C test. Preserve each test's body,
   parameters, and assertions; a required mechanical edit is a blocker first.
5. Separate exact matches from discrepancies and upstream hard blockers.
6. Review the completed ledger with Alex before changing CPython source.
7. Restore approved baseline code and tests in reviewable commits without
   semantic cleanup.
8. Verify both GIL and FT builds with the complete original test intent,
   broader CPython tests, sanitizers, and long-form ABBA performance runs.
