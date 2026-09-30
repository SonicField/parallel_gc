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
  `624d4bc8f3a37b701a55d14c9923b1f999f14a83`
- Port's upstream parent:
  `333071231d3a46cccc32d7f44b99328c3299d0b1`

## Fidelity rule

The port must preserve every algorithmic phase, synchronization choice,
atomic invariant, adaptive mechanism, API behaviour, diagnostic, and test in
the baseline unless a specific difference is discussed and recorded here.
Code cleanup may change presentation only, never behaviour.

An upstream incompatibility is a hard blocker. It must be documented and
discussed with Alex before any adaptation is designed or implemented. Passing
new tests or CPython CI is not evidence of parity with the baseline.

## Status meanings

- **MATCH**: equivalence has been demonstrated from source and tests.
- **MISSING**: baseline functionality or coverage is absent from the port.
- **CHANGED**: both exist, but behaviour or implementation semantics differ.
- **BLOCKED**: current upstream prevents a direct port; no resolution is
  authorized until discussed.
- **APPROVED DIFFERENCE**: a specific divergence was discussed and accepted;
  the reason must be recorded here.
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
| Environment option | Baseline startup environment control | Not present | APPROVED DIFFERENCE: runtime API only |
| `PyConfig` field | `parallel_gc` | Not present | APPROVED DIFFERENCE: runtime API only |
| Startup worker range | 0 through 256 | Fixed internal ceiling of 16 | APPROVED DIFFERENCE: adaptive runtime selection |
| Resizable barrier | `_PyGCBarrier_Resize` supports adaptive FT dispatch | Restored | MATCH |
| Deque backing store | Preallocated external-buffer initialization/finalization | Restored | MATCH |
| GIL shared work queue | Block queue and semaphore support parallel root marking | Restored | MATCH |
| Worker thread state | Baseline helper thread-state and accounting fields | Restored | MATCH |
| Deque allocation failure | Baseline behavior | Explicit propagation; no silent work loss | CHANGED; final failure-path audit required |
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
| `Include/internal/pycore_gc_ft_parallel.h` | `816d74deecfcddf6164479de43bc5d8d9d4dcd5e` | `96c242bb4a2c52392a092cc5b8b13af363f40201` | APPROVED DIFFERENCE: rollback state |
| `Include/internal/pycore_gc_parallel.h` | `b6c9da7225077ba8adb94a515fc6f384cdc739c0` | `2977d32000434b8ca719d9de231017d7275455b7` | APPROVED DIFFERENCES: fixed ceiling, threshold, rollback state, visitor declaration |
| `Include/internal/pycore_gc_random_walk.h` | `36fcd08d813de99d07391b781555685aa77c4362` | `b64ccbbf84ed6653af3573f29668d3eae6202de2` | APPROVED DIFFERENCE: reject regressions and walk back |
| `Include/internal/pycore_ws_deque.h` | `fd268cd416eba16d1e5dea513e191e7a1e899c97` | `fd268cd416eba16d1e5dea513e191e7a1e899c97` | MATCH |
| `Python/gc_free_threading_parallel.c` | `753b9bfb9144b8530ca03c6fe40f7af065c431ab` | `b8c4a4e24ff1c6acb68d88199e157a16fbb54134` | APPROVED DIFFERENCE: initialize rollback state |
| `Python/gc_parallel.c` | `21dd4468d05cc644882a74805eeb047ae9931426` | `40120b54c92fb673682fec52e4b4cdcc244b7398` | APPROVED DIFFERENCES: current list bit, complete pre-mark draining, rollback state |

The current versions are not accepted as equivalent merely because portions of
their control flow or APIs have the same names.

The baseline patch adds 157 Python test methods across the parallel-GC test
modules and `Lib/test/test_free_threading/test_gc.py`; all 157 are present in
the current port. The baseline also adds 29 C test/helper entry points in
`Modules/_testinternalcapi/test_ws_deque.c`; the current file retains those and
adds coverage for the approved port behavior.

## Reported blockers and outcomes

The earlier reduced port reported several conflicts without preserving a
reproducer. Restoration showed that none justified deleting a baseline phase:

| Facility | Outcome |
|---|---|
| GIL interpreter-root pre-mark | Restored. A stale-pointer crash was reproduced and traced to completion with a non-empty worker-private deque. Workers now drain the complete private closure before returning. |
| FT root propagation | Restored and exercised by the original tests. |
| FT parallel `update_refs` | Restored with its two-pass barrier and exercised by the original tests. |
| FT parallel `scan_heap` | Restored, including abandoned pages and unique-ID batching, and exercised by the original tests. |
| Helper-owned Python thread states | Restored; the broad `test_external_inspection` run passed on the earlier port revision. Current-revision broad validation remains required. |

## Baseline paths deliberately absent from the port delta

The following baseline paths implement either the removed startup interface or
an unrelated upstream policy and are intentionally absent after discussion:

- `Include/cpython/initconfig.h`, `Python/initconfig.c`,
  `Programs/_testembed.c`, `Doc/c-api/init_config.rst`, and
  `Doc/using/cmdline.rst`: environment, `-X`, and `PyConfig` worker selection;
- `Python/brc.c`: an accidental relocation made during an earlier BRC
  experiment; current upstream's BRC implementation is retained; and
- `.gitignore`: repository housekeeping, not collector behavior.

The RSS-based free-threaded collection-deferral logic is also not restored,
because it was an upstream policy inherited by the baseline rather than part
of parallel GC.

## Literal patch applicability

The complete baseline delta was applied without modification in a disposable,
detached worktree at the port's upstream parent. This historical exercise
identified 36 clean applications and 12 textual conflicts; those conflicts
were subsequently inspected and resolved rather than treated as permission to
change the collector design.

- 36 paths apply unchanged.
- 12 paths had textual conflicts.

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

A clean textual application alone was not classified as a semantic match.

### Conflict classification

No required 3.15-to-current spelling change was identified. In particular,
startup worker selection was removed by an explicit interface decision, not
because an upstream rename forced it.

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

The original GIL phases, barrier/deque primitives, mark-alive tests, and
standalone test modules have been restored. Approved changes are the current
list-bit mapping, full draining of the pre-mark private deque, the 16,384-object
serial threshold, the fixed 16-worker ceiling, and a random-walk controller
that rejects a worse trial and returns to the previous count.
The current debug ARM64 GIL build succeeds. The 34 original GIL mark-alive and
adaptive tests, 31 original deque/barrier tests, and 61 applicable upstream
`test_gc` tests pass.

## Free-threaded restoration checkpoint (2026-09-30)

The original FT worker algorithm is restored. Its source differs from the
baseline by initialization of the approved random-walk rollback state. The
baseline abandoned-page enumeration and unique-ID batching APIs are restored;
their absence caused three reproducible compiler errors before restoration.

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
all five original baseline additions are present again. The standalone modules
retain all 152 baseline methods and add six regression methods for approved
port behavior. They include documented API and portability adaptations and are
therefore not byte-for-byte baseline blobs.

This checkpoint records design restoration, not submission readiness. Clean
current-revision broad, sanitizer, feature-on platform, and repeat benchmark
evidence remain separate gates.

## Platform integration decision (2026-09-30)

The current port's Windows build switch, MSBuild definition, `_sysconfig`
reporting, test-project registration, and 64-bit platform checks are retained.
They extend build integration around the unchanged collector rather than
replacing baseline behavior. Alex confirmed that Windows support is required
and that the working implementation must not be reversed merely because those
files were absent from the older baseline patch.

## Completed audit sequence and remaining gates

The path, interface, phase, test, and upstream-conflict audits are complete for
the restoration commit. Remaining submission gates are clean current-revision
broad and sanitizer runs, feature-on platform coverage, clean repeated ABBA
benchmarks with feature-off controls, and core review of the proposed public
surface.
