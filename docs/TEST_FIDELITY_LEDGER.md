# Parallel GC Test Fidelity Ledger

The authoritative test baseline is the parallel-GC delta between
`2e64e36a2b1f8ebb2a6f24ad5c8f75388047d039` and
`beb2907f8d723d7a202d068cb7de69448c53ff7e`.

No current-port test is considered a replacement for a baseline test merely
because it has a similar name or exercises the same broad component. Every
baseline test intent and assertion must remain represented. Mechanical
adaptations for current APIs or cross-platform execution are recorded rather
than being mistaken for byte-for-byte identity.

## Python test inventory

| Path | Baseline-added methods retained | Current additional methods | Baseline blob |
|---|---:|---:|---|
| `Lib/test/test_free_threading/test_gc.py` | 5 | 0 | `b06fa492f00caa43b19cf72ea731126d3e3aee10` |
| `Lib/test/test_gc_ft_parallel.py` | 36 | 0 | `e45ffb9ab5c2ec89301c26360033884ec54b1776` |
| `Lib/test/test_gc_parallel.py` | 35 | 0 | `a9f8f457de9f30e5badd3f8b5f600ba9c497b915` |
| `Lib/test/test_gc_parallel_mark_alive.py` | 34 | 4 | `04b81fa25cdb21e2c324c86e0e6792edf4543fb6` |
| `Lib/test/test_gc_parallel_fork.py` | 0 | 3 | one upstream-blocked skip |
| `Lib/test/test_gc_parallel_properties.py` | 16 | 0 | `fbea7ccd8be48e0d576291316984f64bc066ce59` |
| `Lib/test/test_gc_ws_deque.py` | 31 | 3 | `52c65263acd8a365d5f33d7023a4c17b1b515d93` |
| **Total** | **157** | **10** | |

The current files are not byte-for-byte copies. They contain the no-startup-
configuration API adaptation, cross-platform subprocess/test-harness fixes,
and additional coverage for the GIL threshold, exact adaptive normalization,
complete pre-mark deque draining, and the GIL/FT fork lifecycle. Those edits
were reviewed as test adaptations; they do not authorize weakening the
baseline assertions.

The baseline also modifies existing assertions or support code in:

- `Lib/test/support/__init__.py`
- `Lib/test/test_capi/test_config.py`
- `Lib/test/test_embed.py`

Those deltas must be mapped hunk by hunk because the surrounding upstream
files changed after the baseline.

## C test inventory

The baseline adds 29 test/helper entry points in
`Modules/_testinternalcapi/test_ws_deque.c`, baseline blob
`e8a9026ccd7dae79c7c54a46b6fbb0328743b71b`.

All baseline C test/helper entry points are retained. The current file also has
cross-platform robustness and added regression coverage, so it is not
byte-for-byte identical. The reduced port's separate
`Modules/_testinternalcapi/test_parallel_gc.c` and its registrations have been
removed; it was not part of the baseline.

## Verification checkpoint (2026-09-30)

- GIL debug: all 34 mark-alive/adaptive tests and all 31 deque/barrier tests
  pass; the upstream `test_gc` run completed with 59 passes and two expected
  skips.
- FT debug: all 35 general parallel-GC tests, all 16 property tests, all 31
  deque/barrier tests, and all five restored abandoned-pool additions pass.
- FT component tests: 35 of 36 pass. The remaining test requires the optional
  `_ctypes` module, which was unavailable in this local build; it did not reach
  collector code.

## Restoration gate

The continuing fidelity rule is:

1. every baseline test remains represented and any adaptation is documented;
2. every baseline hunk in pre-existing support/test files is retained or its
   disposition is recorded;
3. the complete baseline test selection runs in both applicable GIL and FT
   builds; and
4. failures are investigated without removing, weakening, skipping, or
   replacing tests.
