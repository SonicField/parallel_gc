# Uncalled GIL wrapper: compiler repair

CPython `b91445e0b95454e32b982770f6e3c864beb5a528` removes only the seven-line definition/comment of GIL `steal_batch_from_worker`. The definition has no callers or other references. The shared `_PyGC_BatchSteal` implementation and the called FT wrapper are unchanged. No atomic, barrier, queue operation, threshold or adaptive policy is changed.

CI compiler run `39248590252` rejects the wrapper in all four Clang GIL/FT debug/release configurations. Local Clang 21.1 reproduces those four failures. GCC 11.5 passes the same pre-fix selection. After removal, all 32 compilations pass: GCC/Clang × GIL/FT × release/debug × four GC translation units. The strict `-Werror=unused-function -Werror=unused-variable` checks remain enabled. The existing FT debug signedness warning remains in the logs; this is not an all-warning-clean claim.

GCC release `gc_parallel.o` is byte-identical before/after for both GIL and FT, compiled with the same `-O3 -DNDEBUG` settings. These are non-PGO object checks, not regenerated optimized interpreter builds or performance measurements.

## Runtime verification

Two fresh GCC debug builds use the current checkout with `--with-pydebug --with-parallel-gc`, plus `--disable-gil` for FT. The collector selection covers GC, parallel collector, fork, deque, properties, marking, PGO-workload correctness, configuration and embedding; FT additionally runs upstream free-threaded GC tests.

| Fresh build | Collector result | Parent harness result |
|---|---|---|
| GIL | SUCCESS: 349 run, 85 skipped; two FT-only modules skipped | 76 tests pass; one FT-only skip |
| FT | SUCCESS: 377 run, 40 skipped; all 11 selected modules pass | 76 tests pass; no skips |

These builds report missing optional system dependencies; the complete module inventory and skip summaries are retained in the build/test logs. They do not establish full CPython-suite success on this machine. ASan, TSan, performance campaigns and hosted checks were not rerun for this removal.

The separate [feature-off probe repair](../ci-probe-feature-off-2026-10-19/README.md), parent commit `d448e16`, already passes all 76 harness tests on both feature-on and feature-off GIL/FT binaries. This core commit does not include that test fix.

## Commands and evidence

Workspace: `/tmp/parallel-gc-ci-repair-20261019-IuvW1e`. `verify-gc-objects.sh.gz` retains the exact compiler loop and configuration paths. It uses existing configuration headers, compiles current source into new output directories and keeps errors as errors. `objects-before-summary.log.gz` and `objects-after-summary.log.gz` record every compilation result. The compiler versions, full per-object diagnostics and object hashes are in `verification.json.gz`.

Two initial fresh Clang configure attempts were explicitly stopped before completion; their logs are retained separately. The completed compiler checks instead use the existing configuration headers and the underlying compiler executable. Neither interrupted configure attempt is reported as a passing build.

Fresh GCC build/configuration logs, configuration headers and all runtime/harness test output are retained. The verification record also includes interpreter hashes and SHA-256 hashes of each uncompressed evidence file.

From the parent repository, the collector command is:

```bash
"$fresh_python" -m test -j8 --timeout=300 \
  test_gc test_gc_ft_parallel test_gc_ws_deque \
  test_gc_parallel test_gc_parallel_fork \
  test_gc_parallel_properties test_gc_parallel_mark_alive \
  test_parallel_gc_profile test_capi.test_config test_embed
# FT also includes test_free_threading.test_gc.
```

The parent harness command is recorded in the separate probe repair. Fresh test environments contain the unchanged pure-Python pyperf 2.10.0 package. These results fix the two diagnosed CI causes locally; the next hosted runs must test the updated parent gitlink before CI is called green.
