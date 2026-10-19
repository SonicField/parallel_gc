# Complete default readiness: 19 October 2026

All eight baseline/current × GIL/FT × parallel-GC enabled/disabled contexts executed all **100 original default programs**, producing the same **127 named results** per context. No program failed or was excluded. Every result passed the existing requested-mode and worker runtime checks; FT execution remained GIL-disabled.

These are one-value diagnostic execution checks, **not performance measurements**. They resolve the dependency-readiness blocker. They do not establish speed, neutrality, adaptation quality or a successful full rigorous ABBA comparison.

## Execution and identity

The parent-only [launcher](../check_prepared_suite.py) uses upstream `Benchmark.run` on explicitly prepared environments. It retains original scripts, data and workload options, while avoiding the usual installer's restoration of incompatible original pins. Before each context it runs `pip check`, the dependency correctness tests, four native probes and the existing mode preflight. [Execution details](../PREPARED_READINESS.md).

- Baseline source: `c67363fa59543ef5d572383af927f1cff88514a1`.
- Current source: `388fd5bb46fdda6b464db566faf818505c3d6eef`.
- All four existing optimized ARM64 PGO+LTO binary hashes still match their original manifests.
- Prepared environments: `/tmp/parallel-gc-pyperformance-repaired-20261019-ZKtZmg`.
- Driver: `/tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW/driver/bin/python`.
- Contexts ran sequentially, bound to NUMA node 0 and CPUs 0–31. Worker timeout was 300 seconds. Full expanded commands are preserved in each log.
- No CPython source, original benchmark program, workload parameter or collector-policy change was made. The existing untracked lib2to3 package metadata in the pyperformance checkout was preserved.

Package versions match across all four environments. Baseline/current use byte-identical package inventories within each build mode; GIL/FT extension-wheel paths and hashes differ as required by their ABIs. SQLAlchemy 1.4.19 uses Alex's approved supported pure-Python build in all contexts. Coverage retains CTracer. Coverage, Dulwich, MarkupSafe and Greenlet retain verified native extensions. No forced-GIL override or unsupported native-module declaration is used.

Dulwich's transitive urllib3 requirement initially failed `pip check`; the failure is preserved in `urllib3-before-check.log.gz`. Installing urllib3 2.2.2 consistently in all four new environments resolved that inconsistency. Historical environments remain untouched.

## Preserved evidence

Each context has its combined raw `suite.json.gz`, `summary.json.gz` and full `readiness.log.gz`. The suite includes every named result and its runtime metadata. Package inventories, installation logs, `pip check` logs, Python paths and original binary manifests are also retained.

`verification.json.gz` records source identities, all eight summaries, the exact program and result inventories, package versions and SHA-256 hashes of the uncompressed evidence files. Independent checks reloaded all eight summaries, required exactly 100 program files and zero failures, revalidated each program result, required matching 127-result inventories, compared package inventories/versions and verified all four original binary hashes before writing this evidence.

The next performance step remains all sixteen rigorous suites using these same prepared dependency implementations and original workload settings. The diagnostic launcher deliberately does not provide that measurement mode. Historical native-SQLAlchemy timings must not be pooled with the newly approved pure-Python comparisons.
