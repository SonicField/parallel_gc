# Investigation and choice register

Updated 21 October 2026 under [DOC-000001](records/changes/DOC-000001/record.md).
This is a family-level navigation index for current reviewer documentation,
not exhaustive coverage of every historical action, `.nbs` record, vendor file
or CPython source unit. Entries summarise retained records; they do not grant
new implementation authority or replace original evidence and uncertainty.

## Retained design and earlier performance work

| Question / choice | Retained decision or outcome | Reason and evidence |
|---|---|---|
| GIL partitioning and serial crossover | Keep the candidate walk and whole serial path below 16,384 candidates. | Avoid helper coordination for small collections; [design §2](../docs/DESIGN.md#2-gil-collector), [historical GIL measurements](../benchmarks/results/arm64-316-669ed6b-full-analysis-2026-10-08.md). Not a guarantee of benefit above the crossover. |
| Marking, barriers and private work | Keep distinct GIL authoritative marking and FT idempotent optimization marking, barrier-separated reference updates and the private buffer. | Ownership/correctness and coordination costs differ by phase; [design §2–4](../docs/DESIGN.md). Added coordination still needs evidence, not presumed benefit. |
| Adaptive worker search | Shared normalization uses exact candidates; walk starts at four, searches 2–16, and excludes serial in FT. | Adjacent search can get trapped at the discontinuous serial boundary; [design §5.5](../docs/DESIGN.md#55-adaptive-worker-controller-pycore_gc_random_walkh), [fixed/adaptive results](../docs/PERFORMANCE.md#42-historical-serialparallel-measurements-715-october-2026). Fixed 16 won tested FT phases; no convergence guarantee. |
| Benchmark activation inherited by forkserver | Retired argument-based activation; use the project pyperf hook. | `--worker` is a benchmark argument, not a GC option; [earlier investigation/provenance route](../docs/PERFORMANCE.md#5-investigation-record). |
| Exact list/tuple/dict traversal and inlining | Retain explicit container fast paths and shared dict-layout logic; forced marker inlining was reverted. | Generic callbacks dominated measured FT traversal; mutation checks and binary comparisons, not an assumption that all inlining helps: [exact list](../benchmarks/results/pyperformance/investigations/ft-exact-list-verification-2026-10-05.md), [tuple](../benchmarks/results/pyperformance/investigations/ft-exact-tuple-verification-2026-10-05.md), [dict](../benchmarks/results/pyperformance/investigations/ft-exact-dict-verification-2026-10-05.md), [traversal investigation](../benchmarks/results/pyperformance/investigations/ft-container-traversal-2026-10-05/README.md), [clean baseline](../benchmarks/results/pyperformance/investigations/ft-container-clean-baseline-2026-10-05/README.md). |
| Parallel-aware PGO | Retain supplementary GIL/FT parallel training alongside explicit fast paths. | Otherwise profile training does not exercise optional collector work; [PGO/runtime ABBA](../benchmarks/results/pyperformance/pgo-runtime-abba-arm64-2026-10-07.md), [design §3.9](../docs/DESIGN.md#39-built-in-container-traversal-and-pgo). |
| SQLite first-thread regression | Lazy pool startup retained for both collectors. | An unrelated thread reproduced the eager-start slowdown; [first-thread diagnostic](../benchmarks/results/pyperformance/investigations/sqlite-thread-transition-2026-10-07.md), [GIL lazy ABBA](../benchmarks/results/pyperformance/investigations/gil-lazy-pool-sqlite-abba-2026-10-07/README.md), [FT lazy results](../benchmarks/results/arm64-316-1958301-ft-lazy-analysis-2026-10-08.md). Armed overhead is distinct from unmeasured first-use latency. |
| Fork recovery | Parent pool/history remain; child abandons inherited helpers, resets adaptation and stays armed. | Parent helpers vanish in the child; child workloads need fresh learning. [Design §6](../docs/DESIGN.md#6-fork-lifecycle), [historical lifecycle plan locator](../docs/VALIDATION.md#recorded-evidence-15-october-2026). Subinterpreter/fork tests remain skipped with a feature-off crash recorded. |
| FT root-placement scaling | Weakness remains open. | Module versus frame roots expose different work distribution; [scaling experiment](../benchmarks/results/investigations/claude-scaling-2026-10-15/README.md), [review](../docs/reviews/2026-10-15-claude-scaling-review.md). Synthetic diagnostics are not application-benefit evidence. |
| Wait/publish/list-splitting/release-store candidates | All four experimental coordination changes were dropped, not imported. | Final full module campaign helped some cases but increased AI mean latency +11.1%; earlier signals differ in metric/protocol. [Qualified campaign record](../benchmarks/results/investigations/root-placement-campaigns-2026-10-15/README.md). Not a general argument against complexity. |
| FT AI/finalizer/BRC and float pathology | Unresolved hypotheses; no new repair accepted. | Ownership/finalizer and work-distribution explanations are not measured causes. [Open issues P5/P6](../docs/OPEN_ISSUES.md#2-performance-defects-and-regressions), [explicit BRC falsifier](../docs/PERFORMANCE.md#5-investigation-record). |

## Integration and benchmark correctness, 16–17 October

[Integration plan](../docs/CLAUDE_INTEGRATION_PLAN.md) records approvals,
candidate/destination commits, excluded changes and separate checks. The
comparison sources remain baseline `c67363fa59` and integrated `388fd5bb46`,
not the later selected checkout merely because documentation advanced.

| Investigation / choice | Outcome and reason | Supporting record |
|---|---|---|
| Creation-worker retention | Repair retained: helpers release their last result before completion. Old collection-shape garbage fraction remains unknown, not automatically 100% live. | [Ownership falsifier and schedule controls](../benchmarks/results/investigations/creation-pool-retention-2026-10-16.md) |
| Module-rooted coverage | Retained as a separate benchmark dimension. Sustained mutations allow temporary stack references; controlled collections check module-only roots. Unsafe cross-thread frame inspection was removed from test instrumentation. | [Rooting integration and positive controls](../benchmarks/results/investigations/module-rooting-integration-2026-10-16/README.md) |
| Unreferenced collector code | Cleanup retained after reference, warning, symbol and focused-test checks; no performance neutrality claim. | [Dead-code checks](../benchmarks/results/investigations/dead-code-cleanup-2026-10-16/README.md) |
| Production marking tests | Retained debug-only opt-in verifier, replacing the separate test implementation. Replay-untracked tuples are accounted separately; an older undetailed scratch failure remains unexplained. | [Verifier, mutation and sanitizer checks](../benchmarks/results/investigations/production-verifier-integration-2026-10-16/README.md) |
| Incremental stale objects | Five missing header dependencies repaired independently. No collector behavior change. | [Header dependency controls/rebuilds](../benchmarks/results/investigations/header-dependencies-2026-10-16/README.md) |
| Native decimal build preparation | First build/partial measurement attempt abandoned; corrected fresh PGO/LTO binaries used for comparisons. No mixing of partial old results. | [Protocol and preparation failures](../benchmarks/results/investigations/integration-validation-2026-10-16/INVESTIGATION-STATUS.md), [build evidence](../benchmarks/results/investigations/integration-validation-2026-10-16/build-evidence/README.md) |
| Full project source ABBA | GIL and FT completed, including negative rows. Same corrected harness on both source builds; cause/neutrality unestablished. | [GIL](../benchmarks/results/investigations/integration-validation-2026-10-16/GIL-PROJECT-RESULTS.md), [FT](../benchmarks/results/investigations/integration-validation-2026-10-16/FT-PROJECT-RESULTS.md) |
| Focused FT collection repeat | Broad module slowdown did not recur; process context differed from the full invocation. | [Focused outcome/limits](../benchmarks/results/investigations/integration-validation-2026-10-16/focused-collections/RESULTS.md) |
| Unchanged full FT repeat | Broad module pattern again did not recur; seven frame collections increased in both halves and three throughput means fell. Same binary pair, not independent rebuilds. | [Full repeat](../benchmarks/results/investigations/integration-validation-2026-10-16/full-ft-repeat/RESULTS.md) |
| Local full-suite failures and debug follow-up | Initial release path-sensitive failures occurred on both sources. Physical-source FT debug passed; GIL leak did not recur in a matched full comparison. | [Original local failures](../benchmarks/results/investigations/integration-validation-2026-10-16/local-full-suite/README.md), [physical debug](../benchmarks/results/investigations/integration-validation-2026-10-16/local-full-suite/physical-debug/README.md), [matched GIL](../benchmarks/results/investigations/integration-validation-2026-10-16/local-full-suite/gil-full-comparison/README.md) |

## Dependency choices and execution attestation, 19 October

These repairs preserve original benchmark programs and run on both sources
and build modes. Historical native-SQLAlchemy results are a different
implementation context, not pooled into the new comparison.

| Dependency / tooling | Choice and why | Record |
|---|---|---|
| Cloudpickle | Compatibility patch retained; unavailable opcode names must not break global-name discovery. | [Tests and original Dask checks](../benchmarks/dependency-repair/CLOUDPICKLE.md) |
| Genshi | Compatibility patch retained at 0.7.7; upgrade alone still failed the AST contract. | [Cloning and XML/text checks](../benchmarks/dependency-repair/GENSHI.md) |
| Coverage | Native 7.6.12 CTracer retained; newer default SysMonitor would change the engine measured. | [Engine decision](../benchmarks/dependency-repair/COVERAGE.md) |
| MarkupSafe | Native 3.0.4 retained for unchanged Sphinx operations with FT GIL disabled. | [Native checks](../benchmarks/dependency-repair/MARKUPSAFE.md) |
| Greenlet | Native 3.5.6 retained; its FT fix alone did not fix SQLAlchemy's native modules. | [Context-switch and workload checks](../benchmarks/dependency-repair/GREENLET.md) |
| Dulwich | Native 1.2.17 retained; silent pure-Python fallback rejected. | [Strict build/workload checks](../benchmarks/dependency-repair/DULWICH.md) |
| SQLAlchemy | Alex approved supported pure-Python 1.4.19 everywhere; native 1.4 enabled the FT GIL, and 2.x would change workload APIs. | [Approval, implementation boundary and tests](../benchmarks/dependency-repair/SQLALCHEMY.md) |
| Prepared runner and state validation | No installer during measurements; exact programs, original workloads and per-run Boolean/GIL/hook checks retained. Common metadata omission is not missing per-run hook evidence. | [Prepared runner](../benchmarks/dependency-repair/prepared-execution-evidence/README.md), [varying-hook fix](../benchmarks/dependency-repair/per-run-validation-evidence/README.md), [analysis state controls](../benchmarks/dependency-repair/analysis-state-verification-evidence/README.md) |
| Complete readiness | All 100 programs/127 results execute in all eight source/build/policy contexts; short checks are not timing evidence. | [Readiness](../benchmarks/dependency-repair/full-readiness-evidence/README.md), [dependency progress](../benchmarks/dependency-repair/PLAN.md) |

## Completed comparisons, hosted reports and open decisions

| Investigation / choice | Latest outcome and remaining question | Record |
|---|---|---|
| Rigorous repaired-dependency source ABBA | All sixteen suites complete (100 programs/127 results each). Individual increases remain; near-zero geometric means do not establish neutrality or activation cost. | [Campaign](../docs/PYPERFORMANCE_CAMPAIGN_2026-10-19.md), [four completed result families](../benchmarks/results/pyperformance/repaired-source-abba-2026-10-19/) |
| GIL source-versus-build follow-up | Two enabled and two disabled ABBA blocks completed using recovered original GIL binaries in a shared reconstructed runtime. Earlier +12.70% BTree/+6.48% NetworkX magnitudes did not recur; cause/equivalence unestablished. Stage 3 rebuild/profile work is conditional and uncommissioned. | [Full protocol, all blocks and custody](../docs/investigations/gil-build-effects/INVESTIGATION-STATUS.md) |
| CI feature-off hook probe and unused wrapper | Separate parent probe and core uncalled-wrapper repairs retained. Five subsequent workflow successes are user-reported, not independently checked job/source artifacts. | [Probe repair](../benchmarks/results/investigations/ci-probe-feature-off-2026-10-19/README.md), [wrapper checks](../benchmarks/results/investigations/ci-unused-wrapper-2026-10-19/README.md), [CI conclusions](../docs/ci-results-2026-10-19.md) |
| Documentation audit and repair | Fresh successor independently closes all five initial documentation findings and satisfies W1–W4 dispositions at the fixed repaired input; no new finding. Technical/historical limitations remain open, not accepted by the D verdict. | [DOC-000001](records/changes/DOC-000001/record.md), [initial A-000002](records/audits/A-000002/record.md), [successor A-000003](records/audits/A-000003/record.md) |
| Historical project audit | Inconclusive, six findings still open. Narrow new recovery/reporting does not establish full historical closure. | [A-000001 access and dispositions](records/audits/A-000001/ACCESS.md) |
| Remaining source/API/performance decisions | No new repair authorised here: allocation/rollback/join policies, extension compatibility/provenance, public API, first-use latency/memory, feature-off performance and unresolved workloads remain. | [Open issues and landing gates](../docs/OPEN_ISSUES.md), [validation](../docs/VALIDATION.md) |

Earlier port/restoration plans, source inventories and lifecycle choices have
immutable historical routes in DESIGN, VALIDATION and the handoff log. Their
original producer/authority and evidence gaps remain explicit; this index
does not recreate the old complete runtime or certify those histories.
