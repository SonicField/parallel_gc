---
name: parallel-gc-engineering
description: Use when reviewing, modifying, benchmarking or writing about this project's parallel garbage collector for CPython. Applies Verifiable Practice and records why additional coordination must earn its cost across workloads.
---

# Working on the parallel GC

This file is for AI assistants. Humans should start with the
[README](README.md).

## Method

Use [Verifiable Practice](https://github.com/SonicField/verifiable-practice)
(VP): state the goal, state what would falsify each claim, try to falsify it,
and report what happened, including failures. The project's evidence rules
are in [PERFORMANCE.md §6](docs/PERFORMANCE.md). Open problems and the
measured outcome of past attempts are in [OPEN_ISSUES.md](docs/OPEN_ISSUES.md).
Read both before proposing a change.

## Additional coordination must earn its cost

Python GC workloads vary enormously. Evaluate a collector design across:

- heap shapes: chains, trees, random graphs, huge flat containers, many tiny
  objects;
- where live data is rooted: frame locals reached from thread stacks, module
  state reached through `sys.modules`, extension globals;
- container types: lists, tuples, dicts and instance dicts, plus arbitrary
  `tp_traverse`;
- finalizers and resurrection;
- many mutator threads, with free-threaded ownership (BRC) and per-thread
  mimalloc heaps.

A mechanism tuned for one case usually costs something in another. Several
of this collector's mechanisms look naive and are deliberate trades:

- **Helpers give up after a few failed steal sweeps.** This loses
  parallelism in some cases, but the cost is bounded and there is no
  coordination traffic.
- **A private 1,024-entry buffer sits in front of each work-stealing queue.**
  It trades load balance for low contention on the queue ends.

Before replacing a mechanism, find out what cost or failure it protects
against. Check the recorded experiments rather than assuming either that an
upgrade must help or that it has already been conclusively rejected.

### Case study, October 2026

An AI review judged the free-threaded collector's root propagation naive. A
micro-benchmark showed it losing its parallelism when live data was
reachable only from module state, so four "proper" upgrades were built:

1. helpers wait until all work is finished;
2. busy workers publish part of their private buffer to idle ones;
3. large lists are split into stealable index ranges;
4. release stores in the work queue.

They gave up to 10× speedups on synthetic single-collection heaps. In the
project's full ABBA suite they:

- were neutral on frame-rooted workloads;
- helped only module-rooted ones;
- reintroduced steal contention (publishing to idle workers);
- needed a memory-ordering fix (the list splitting);
- showed a sustained `ai_workload` mean-latency increase of 11.1% in the
  final full module-rooted campaign.

This was not three rigorous latency replications. The first full campaign
reported throughput −4.0% and mean latency +1.5%; the intervening quick run
reported a +15% latency warning but was a machinery check, not performance
evidence. All three used the same binary pair. Keep those different metrics
and protocols separate when explaining the candidate's rejection.

The realistic throughput gain (+6%) was similar in size to differences in a
later quick build comparison; its attribution remains uncertain. All four
changes were dropped from the candidate. This teaches the cost of these
mechanisms, not that additional coordination can never help. Evidence:
[campaign data](benchmarks/results/investigations/root-placement-campaigns-2026-10-15/README.md)
and [OPEN_ISSUES.md §2](docs/OPEN_ISSUES.md).

## Evidence rules that caught real mistakes

- **Micro-benchmarks are diagnostic only.** Use them to locate a problem,
  never to claim a benefit.
- **Use the full project suite** (`gc_perf_benchmark.py --full
  --include-synthetic`, PGO+LTO, ABBA order across builds, other cores
  quiet).
- **Use serial mode as a control.** Record its movement alongside the
  parallel result. Identical source need not generate identical PGO machine
  code. Compare per-run means rather than treating pooled samples as
  independent runs.
- **Calibrate comparisons between builds.** A quick cleanup comparison showed
  roughly 6% differences on some workloads; this is not a universal noise
  floor or an exclusion bound. Use identical-source rebuilds when needed.
- **Pre-register what counts as benefit and as harm.** Do not reclassify a
  flagged regression as "probably noise"; re-measure it.
- **Test the tests:** add positive controls and mutation checks. Mistakes
  that occurred here:
  - top-level script variables are module globals, not frame locals;
  - debug counters were last-run values, not cumulative;
  - object ids can be reused while other threads free objects.
- **Prefer general mechanisms.** Container-specific special cases need
  evidence from real applications that the container shape matters, not a
  synthetic heap built to show the problem.

## Writing for the maintainer

Describe changes by what they do and the effect of keeping or dropping them,
not by internal labels. Keep explanations short. Report regressions as
prominently as gains.

The integration plan preserves active atomics, barriers, phase structure,
thresholds and adaptive policy. Discuss changes to those with Alex; evidence
rules are not permission to change the design. Record the experiment's outcome
and what remains unknown before moving on.
