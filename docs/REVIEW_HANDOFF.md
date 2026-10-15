# Parallel GC: starting place for informal review

## Purpose and checkpoint

This package is for Matt and Pablo to learn how the collectors work, reproduce
the experiments and discuss the proposal. It is not a formal CPython PR or a
claim that the implementation is ready to land.

The reviewed source is `SonicField/cpython` commit
`c67363fa59543ef5d572383af927f1cff88514a1`, based on `python/cpython` commit
`333071231d3a46cccc32d7f44b99328c3299d0b1`. The parent repository pins that
source as its `cpython/` submodule. The handoff was reconciled on 12 October
2026. Publication and CI confirmation for this checkpoint are pending.

## What the design is trying to achieve

Parallel GC should reduce cyclic-collection pauses as the heap exposes useful
parallel work, preserve the serial collector's collection coverage, and tune
itself to the workload and available hardware. Applications enable or disable
it through `gc`; they do not choose worker counts or a heap threshold.

The GIL collector obtains the candidate count during its required list walk.
Below 16,384 candidates it continues serially on the collecting thread. The FT
collector adapts within the parallel range of 2–16 participants. Serial is
deliberately outside that search: a local optimiser can retreat into a serial
minimum and never discover a faster parallel configuration beyond a slower
intermediate count. The adjacent random walk can encounter other local minima
too; it does not guarantee a global optimum.

Both collectors start at four participants, share the same random walk and
normalization function, and retain their learning between collections. The
cost is elapsed nanoseconds divided by the exact candidate count, not the
number of objects reclaimed. Child processes reset learning after a supported
fork because their workloads commonly differ from their parent's.

## Why two repositories and two benchmark suites

- `SonicField/cpython` contains core implementation, build integration,
  correctness tests and CPython-facing reference documentation.
- `SonicField/parallel_gc` contains design rationale, CI, the performance
  laboratory, raw results and reproduction records. It pins the CPython source.
- The parent's `pyperformance/` submodule pins the unmodified upstream suite.
  Project activation and ABBA orchestration live outside that submodule.

Pyperformance measures whole-program regressions. The dedicated GC suite
measures controlled heap topologies, sustained allocation, collection
intervals, throughput and adaptation. Both are needed. The substantial GC
benchmark system belongs in the parent, not in CPython's regression-test tree.

## Read, build and explore

Once this checkpoint is published, start with the complete parent checkout:

```bash
git clone --recurse-submodules https://github.com/SonicField/parallel_gc.git
cd parallel_gc
git submodule update --init --recursive
git rev-parse HEAD
git ls-tree HEAD cpython
git -C cpython rev-parse HEAD
```

The last two commands must identify the same pinned CPython commit. Cloning the
fork alone omits the performance and design material. A submodule's branch
setting does not override the parent's recorded commit. Use separate build
directories for GIL, FT and feature-off controls. The root Makefile and legacy
tools are not the current build path.

Suggested reading order:

1. [Getting Started](GETTING_STARTED.md): build both collectors and run focused tests.
2. [Design Post](DESIGN_POST.md): why the phases, marking protocols and work distribution exist.
3. [Architecture](ARCHITECTURE.md): source-level flow, timing boundaries and invariants.
4. [Fork Architecture](FORK_ARCHITECTURE.md) and [Lazy Pool Plan](LAZY_POOL_CREATION_PLAN.md): lifecycle contract and failure evidence.
5. [Benchmarking](BENCHMARKING.md): reproduce measurements and interpret their limits.
6. [Discussion draft](pep-parallel-gc-v2.rst), [Decisions](CORE_DEV_DECISIONS.md) and [Source Audit](../AUTIT-TODO.md): design and unresolved work.

The source entry points are `deduce_unreachable()` in `cpython/Python/gc.c`
and `gc_collect_main()` in `cpython/Python/gc_free_threading.c`. Their phase
implementations are in `gc_parallel.c` and `gc_free_threading_parallel.c`.
`pycore_gc_random_walk.h` defines the shared controller. The
[source inventory](SOURCE_INVENTORY.md) maps the rest of the integration.

## Implemented lifecycle

| Event | GIL | Free-threaded |
|-------|-----|---------------|
| Enable | Arm; create no helper. | Arm; create no helper. |
| First parallel use | At least 16,384 candidates and usable splits; start 16 helpers. | At the first collection, before stopping the world; start 15 helpers plus collecting worker zero. |
| Later use | Reuse pool; activate selected helpers. | Reuse pool; activate selected participants. |
| Startup failure | Roll back partial startup, collect serially, warn once, enter FAILED. | Same contract. |
| Explicit enable after failure | Re-arm and permit one later attempt. | Same contract. |
| Disable | Stop helpers; may retain reusable storage. | Stop helpers and free pool. |
| Supported fork | Parent unchanged; enabled child armed, no inherited helper used. | Same contract, with lifecycle locking before stop-the-world. |

An inherited collection completes serially in the child and does not train
the reset controller. Startup failure does not cause automatic retry. Warning
delivery follows safe collection cleanup; even a warnings-as-errors filter
does not turn successful serial fallback into a failed collection.

## Evidence and limits

Latest project measurements used optimized PGO+LTO Python 3.16 on one
72-logical-CPU AArch64 Linux host. Parallel phases were included in PGO.

| Evidence | Recorded outcome | Limitation |
|----------|------------------|------------|
| [GIL full project run](../benchmarks/results/arm64-316-669ed6b-full-analysis-2026-10-08.md), collector `669ed6b17e` | Mixed throughput effectively unchanged; mean callback interval +3%, maximum +21%. Eight collection shapes: 1.08x geomean, including one unstable negative graph result. Sustained throughput +7.6% geomean. | No full GIL pyperformance sweep after lazy startup; focused SQLite ABBA is neutral. |
| [FT full project and pyperformance run](../benchmarks/results/arm64-316-1958301-ft-lazy-analysis-2026-10-08.md), collector `195830171f` | Mixed throughput +23.5%, mean callback interval −26%; all eight collection shapes improve, 1.24x geomean. | Sustained AI throughput −9.9%, mean callback interval +116%; chain mean interval +13%. |
| Same FT pyperformance ABBA | SQLite and startup neutral; `gc_traversal` 41.8% faster; `float` 10.5% slower. | 93 programs/119 measurements; seven excluded for dependency or build-module gaps. |
| FT adaptive/fixed ABBA | Adaptive beats fixed 2 and 4; fixed 16 wins the three tested phases. | Three cycles do not establish convergence time or optimality. |
| Local GIL/FT memory and race checks | Recorded ASan and TSan selections pass without diagnostics. | Bounded selections, not a proof of correctness; ASan leak detection disabled and TSan fork options/suppressions recorded. |

`c67363fa59` changes release-build test guards only after measured FT collector
`195830171f`. Later source changes must receive new measurements. Full callback
intervals are not direct FT stop-the-world pauses. The raw results, executable
hashes, sample dispersion and exclusions remain in the linked reports.

Earlier Linux and Windows full workflows passed at collector `d396f837b9`
(runs `37615265794` and `37615268403`). The later four-build matrix passed in
run `37663869128`, before the current local commits. These are historical
results. The current checkpoint needs remote matrix and full-suite repeats;
live GitHub status was unavailable during this reconciliation. Full workflows
run CPython's default runtime state, with support compiled in but disabled;
focused tests explicitly exercise active collectors. See [Testing](TESTING.md).

## Known work to discuss

The [audit](../AUTIT-TODO.md) still records unchecked GIL split-vector growth,
unchecked FT unique-ID accumulation, uncertain FT scan rollback, unchecked
joins, unexplained freed-entry handling, unused alternatives and duplicated
condition-variable operations. Some are source-visible hazards; the scan
rollback item remains a hypothesis awaiting fault injection.

Performance regressions remain visible. The FT finalizer/BRC explanation and
the `float` graph-distribution explanation are hypotheses, not established
causes. Discontinuous serial/parallel costs are a deliberate controller design
constraint, not a missing worker-count option.

Subinterpreter cleanup after fork remains untested because feature-off controls
also crash in that upstream scenario. Extension `tp_traverse` compatibility,
exact provenance/licensing, memory use and first-use startup latency need
further review. Native macOS active-collector evidence is missing; current
Windows and Linux x86-64 evidence must be repeated after the FT lifecycle work.
CPython-facing `Doc/library/gc.rst` still has stale configuration wording;
the parent architecture and discussion draft describe this checkpoint.

Useful review questions are whether the phase invariants and failure policies
are sound, which public diagnostics belong in the proposal, what extension
tests are needed, and what performance limits should apply. The
[readiness plan](CORE_DEV_SPRINT_READINESS_PLAN.md) tracks submission work
separately from this informal review.
