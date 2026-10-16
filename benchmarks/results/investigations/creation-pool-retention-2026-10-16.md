# Creation-pool ownership repair

Date: 16 October 2026. Parent baseline: `bedc060`; CPython checkout/gitlink: `c67363fa59`, unchanged. This is a benchmark correctness repair, not a collector optimisation or a performance measurement.

## Goal and falsifier

The collection benchmark must keep only the caller-selected surviving clusters alive while its creation helpers stay running. Helpers must release their results before reporting task completion. Falsified if discarded clusters remain reachable from idle helpers, or selected survivors disappear.

The repair applies the assignment from candidate `6c8bf14`: after placing a result on the result queue, set the worker's `clusters` local to `None`, before `task_done()`. `create_objects()` waits for all tasks before collecting the results, so the caller cannot discard a batch before its creator has released the local reference. No heap generator, seed, run duration, collector policy or JSON format changed.

## Test-first observations

The new regression tests use real queues, threads, graph generation, weak references and `gc.collect()`. Scheduling controls only delay entry to the existing worker or synchronize task claims; they do not replace pool behaviour.

| Schedule / ownership | Before repair | After repair |
|----------------------|---------------|--------------|
| One worker processes all four tasks; caller retains nothing | 10 of 40 cluster heads alive; assertion fails | 0 of 40 alive |
| Four workers each claim a task before any finishes; caller retains nothing | 40 of 40 alive; assertion fails | 0 of 40 alive |
| Natural scheduling; caller retains nothing | 10 of 40 alive in this run; assertion fails | 0 of 40 alive |
| Four-worker schedule; caller retains 32 of 40 clusters | 40 alive, expected 32; assertion fails | Exactly the selected 32 alive; discarded eight absent |

Every successful ownership check also verifies that all four creation helpers remain alive. Existing deterministic-seed/order, generator-error and worker-error tests remain.

These results establish the original bug and its scheduling dependence. A worker keeps its last batch, not all batches it ever generated. Consequently, the actual retained fraction in old benchmark campaigns cannot be inferred from one test schedule. This repair removes those unintended roots; it does not establish historical campaign garbage fractions retrospectively.

The first three failures were run directly against the unfixed working tree. The 32-survivor check was subsequently run against `git show bedc060:benchmarks/gc_perf_benchmark.py`, loaded in a separate process; it failed by the intended `40 != 32` assertion, not an import or infrastructure error.

## Verification

Host Python `3.12.15+meta`, AArch64: all ten harness tests pass. The full harness also passed 40 repeated suites on each GIL/FT release/debug binary: 20 with parallel policy disabled and 20 armed, 400 tests per binary and 1,600 in total, zero failures/errors. These are reused, non-PGO October 15 binaries; their version strings identify `c67363fa59` and include `dirty`. They are mode-specific harness evidence, not proof of an exact clean-source build. New CPython builds and sanitizer campaigns were not performed for this parent-only assignment.

Binary root: `/home/alexturner/local/parallel_gc_claude-builds/B1-baseline-c67363fa59/`.

| Binary | SHA-256 |
|--------|---------|
| `gil-rel/python` | `d3db5863e2fa311241af3348feb07378ced1e4fae035bebd5df9b9828531ccb3` |
| `ft-rel/python` | `270822bf0b1a487e346c372d9e9b9c0898f8905bf80dba1dcd5c568fed4bfff6` |
| `gil-dbg/python` | `db0828972d10171827ea89cc88858a09ecd07a8675ff4a3d88e32de72dcb8a03` |
| `ft-dbg/python` | `a697342da851d879827d3c9b18a0991b0205fc8e2c0fd1fac45854a03075478f` |

From the parent repository, run the focused tests with:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
    benchmarks.test_gc_perf_benchmark.CreationPoolTests
```

The repetition command, run with each binary under `timeout 120`, is:

```python
import gc
import unittest
from benchmarks import test_gc_perf_benchmark as tests

for enabled in (False, True):
    gc.enable_parallel() if enabled else gc.disable_parallel()
    for run in range(20):
        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromModule(tests).run(result)
        if not result.wasSuccessful():
            raise RuntimeError((enabled, run, result.failures, result.errors))
    gc.disable_parallel()
```

## Interpretation and remaining work

The repair is required to make the requested survival fraction meaningful. Changed timings after this repair could reflect both changed garbage volume and changed root distribution. Collector comparisons must use the same corrected harness for baseline and candidate binaries. Performance campaigns and hosted regression tests remain pending; no performance benefit is claimed here.
