# Parallel Garbage Collection for CPython

This project develops and evaluates parallel cyclic garbage collection for GIL
and free-threaded CPython builds. Parallel collection is optional at build time
(`--with-parallel-gc`) and at runtime (`gc.enable_parallel()`). Both collectors
remain stop-the-world: helpers share collector work while application threads
are paused.

The goal is to reduce cyclic-GC pauses progressively as a heap exposes useful
parallel work, while preserving collection coverage. Applications turn the
feature on; the collector tunes its worker count without user configuration.
Activation should cost little when parallel work does not help. This is the
design goal, not a claim that every measured workload already meets it.

It is a starting point for discussion with CPython core developers, not a
claim of readiness to land. The
[PEP-shaped discussion draft](docs/pep-parallel-gc-v2.rst) was written by Codex
under Alex Turner's guidance using
[Verifiable Practice](https://github.com/SonicField/verifiable-practice).

**Validation checkpoint, 17 October 2026:** Four fresh optimized baseline/current GIL/FT builds and selected local tests passed. Full project ABBA comparisons are recorded, including negative results; performance neutrality is not established. Full-default pyperformance comparisons are incomplete because of dependency API errors and FT extensions enabling the GIL. Current hosted CI outcomes remain unverified. Start with [Validation](docs/VALIDATION.md) and [the integration comparison, §4.1](docs/PERFORMANCE.md), not an older green run or aggregate speedup.

## Start here

| Question | Read |
|----------|------|
| How do I build, test and use it? | [Getting started](docs/GETTING_STARTED.md) |
| How do the collectors work, and what are the invariants? | [Design](docs/DESIGN.md) |
| What has been measured, how, and what must a change achieve? | [Performance](docs/PERFORMANCE.md) |
| What is broken, unproven or undecided? What blocks upstreaming? | [Open issues](docs/OPEN_ISSUES.md) |
| Which tests and CI runs apply to which source revision? | [Validation](docs/VALIDATION.md), [Testing](docs/TESTING.md) |
| What was adopted from the review work, and what remains? | [Integration plan and progress log](docs/CLAUDE_INTEGRATION_PLAN.md) |
| What is proposed for discussion? | [Discussion draft](docs/pep-parallel-gc-v2.rst) |
| Why does root propagation scale poorly in some heaps? | [Scaling review, 15 October 2026](docs/reviews/2026-10-15-claude-scaling-review.md) |
| I am an AI assistant working on this project. | [SKILL.md](SKILL.md): method, evidence rules and why simple designs are kept |

Superseded plans, ledgers and earlier documents were removed; they remain in
git history (for example `git show 724b74b:docs/ARCHITECTURE.md`).

## Repositories and source identity

- `cpython/` is the `SonicField/cpython` fork: implementation, build
  integration, focused tests and CPython-facing documentation.
- This parent repository holds the design and evidence documents, CI, the
  benchmark laboratory and raw results, and pins the exact CPython commit.
- `pyperformance/` pins the unmodified upstream benchmark suite.

```bash
git clone --recurse-submodules https://github.com/SonicField/parallel_gc.git
cd parallel_gc
git ls-tree HEAD cpython          # source selected by this parent revision
git -C cpython rev-parse HEAD     # must match
```

The design baseline is CPython `c67363fa59` on branch
`parallel-gc-upstream-port`, based on upstream `333071231d`. Subsequent cleanup,
production-test and dependency commits are recorded in
[Validation](docs/VALIDATION.md) and the integration log. A clone obtains the
commit recorded by the gitlink, not the branch tip. The root `Makefile` and
`tools/` describe an older workflow; use the commands in
[Getting started](docs/GETTING_STARTED.md).

## What runs in parallel

| Collector | Parallel phases | Serial phases |
|-----------|-----------------|---------------|
| GIL, ≥ 16,384 candidates | interpreter-root pre-marking, reference subtraction, reachability marking | count/split walk, list reconstruction, finalization, deallocation |
| GIL, < 16,384 candidates | none | whole collection |
| Free-threaded | `update_refs`, `mark_heap`, `scan_heap`; known-root propagation runs on the pool but scales only under some conditions (below) | deferred stack scan, finalization, deallocation |

Free-threaded known-root propagation dominated the measured large live
graphs. In measurements on 15 October 2026 it scaled to 3.39× at 16 workers when
a live 1M-object graph was reachable from a frame local, but when the same
graph was reachable only from a module global one worker did about 99% of the
phase and the collection ran at 0.61–0.83× serial speed. A deep binary tree
reached 1.22× either way. See [Design](docs/DESIGN.md) §3.3 and the
[scaling review](docs/reviews/2026-10-15-claude-scaling-review.md) §7.

Both collectors use persistent helper pools created lazily at first use, a
shared adaptive worker controller (2–16 participants, starting at four),
transactional startup with serial fallback, and fork recovery that leaves the
child armed without helpers.

## Performance summary

The completed 16–17 October comparison asks whether integration changed the baseline implementation, using the repaired benchmark on both source revisions. It is not a new estimate of parallel-versus-serial benefit. GIL has lower throughput in four of eight sustained cases and longer controlled collection time in thirteen of sixteen; several serial controls also move. FT has consistently slower module-rooted controlled collections (+18.72% to +34.81%) and module-cache mixed throughput −7.41%. Attribution remains unresolved. [Full results and limitations, §4.1](docs/PERFORMANCE.md).

The following serial/parallel results are historical, measured before the integration:

PGO+LTO, one 72-logical-CPU AArch64 host; GIL collector `669ed6b17e`, FT
collector `195830171f`. Full tables and negative results:
[Performance](docs/PERFORMANCE.md) §4.

- **GIL:** eight 500,000-object collection shapes 1.08× geomean (graph
  unstable and negative); mixed throughput unchanged, mean callback interval
  +3%, maximum +21%; sustained throughput +7.6%.
- **FT:** all eight shapes faster, 1.24× geomean; mixed throughput +23.5%.
  Sustained `ai_workload` throughput −9.9% with mean callback interval +116%;
  pyperformance `float` −10.5%. SQLite and startup neutral after lazy startup.
- **Adaptive controller:** fixed 16 workers beat it in all tested FT phases.
- **Root-propagation scaling:** depends on root placement and heap shape.
  Experiments improved some module-rooted cases but failed the wider workload
  requirements and were dropped ([Open issues](docs/OPEN_ISSUES.md) §2).
  Proposed measurement criteria are in [Performance](docs/PERFORMANCE.md) §6.

These are same-binary serial/parallel comparisons on one machine, not general
CPython performance claims. FT callback intervals are not stop-the-world pause
times.

The historical collection-shape measurements used creation workers that could
retain discarded clusters. Their intended garbage fraction was therefore not
established; the actual retained fraction is unknown. Mixed, sustained and
pyperformance results did not use that creation pool. See the investigation
record in [Performance](docs/PERFORMANCE.md) §5.

General-purpose suites such as pyperformance do not reliably create large
cyclic heaps or distinguish collector throughput and pauses, so they cannot by
themselves show whether parallel GC works. The dedicated benchmarks here are
part of the evidence. A broad pyperformance regression is still a blocker.

## Key files

| File | Purpose |
|------|---------|
| `cpython/Python/gc_parallel.c` | GIL parallel collector |
| `cpython/Python/gc_free_threading_parallel.c` | Free-threaded parallel phases |
| `cpython/Python/gc.c`, `cpython/Python/gc_free_threading.c` | Integration with the serial collectors |
| `cpython/Include/internal/pycore_gc_parallel.h`, `pycore_gc_ft_parallel.h` | Collector state |
| `cpython/Include/internal/pycore_ws_deque.h`, `pycore_gc_barrier.h`, `pycore_gc_random_walk.h` | Deque, barrier, adaptive controller |
| `cpython/Modules/gcmodule.c` | Python API |

## Links

- [Project repository](https://github.com/SonicField/parallel_gc)
- [Project CPython fork](https://github.com/SonicField/cpython)
- [Upstream CPython](https://github.com/python/cpython)
