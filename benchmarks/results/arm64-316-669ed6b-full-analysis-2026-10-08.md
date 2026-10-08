# Current-head GIL and free-threaded full benchmark analysis

## Scope and provenance

This report records the completed project-specific full benchmark runs from
the overnight campaign started on 7 October 2026. It does not treat an
incomplete adaptive-worker or pyperformance campaign as evidence.

- Parent repository: `ae53aca599fe25398a6b106476fd448049534448`
- CPython repository: `669ed6b17e7eb5e7435951cda9f2123a1d6a907b`
- Host: 72-logical-CPU AArch64 Linux
- Compiler: GCC 11.5.0
- GIL configuration: `--with-parallel-gc --enable-optimizations --with-lto`
- Free-threaded configuration: `--with-parallel-gc --disable-gil --enable-optimizations --with-lto`
- Full-suite parameters: five runs per mode, 60 seconds per sustained run,
  500,000 requested objects, and synthetic workloads enabled

The CPython worktree was clean. The parent worktree contained unrelated
untracked build and result directories; the benchmark driver itself matched
the recorded parent commit.

Both optimized builds completed their PGO training and passed the three-file
focused selection before measurement. The GIL build ran 154 tests with 59
expected skips. The free-threaded build ran 119 tests with 54 expected skips.

Raw reports:

- [GIL full result](arm64-316-669ed6b-gil-full-2026-10-07.md)
- [Free-threaded full result](arm64-316-669ed6b-ft-full-2026-10-07.md)

## Metric limitation

The sustained-workload callback interval is the time between GC start and
stop callbacks. It is not a direct stop-the-world pause measurement. This
report therefore calls it a callback interval and does not present it as a
pause.

## GIL result

Mixed-workload throughput was unchanged within measurement resolution:
2,404 operations per second in serial mode and 2,403 in parallel mode. The
parallel configuration performed 116,336 collections, 2.1 percent fewer than
the serial configuration's 118,788. The run did not record candidate counts
per mixed-workload collection, so it cannot establish whether the parallel
collections were larger.

The mixed-workload latency result regressed. Mean callback interval increased
by 3 percent, maximum callback interval increased from 152 to 185 milliseconds
by 21 percent, and the fraction of wall time inside callbacks increased from
65.5 to 66.3 percent. Four of the five paired parallel runs had a higher
maximum callback interval than their serial counterpart.

Requested collection of the eight 500,000-object heap shapes improved by a
1.08 geometric mean. The graph shape regressed from 398.0 to 409.5
milliseconds. That graph mean is unstable: one parallel sample took 533
milliseconds while the other four ranged from 359 to 395 milliseconds.

Sustained synthetic throughput improved by 7.6 percent geometric mean:
7.9 percent for chain, 8.2 percent for graph, and 6.6 percent for the AI
workload. Mean callback interval improved for chain and graph but increased by
8 percent for the AI workload. Maximum callback interval decreased for all
three sustained synthetic workloads.

The GIL result therefore supports higher throughput and lower worst-case
callback intervals on the sustained synthetic heaps. It does not support a
mixed-workload mean-latency improvement.

## Free-threaded result

Mixed-workload throughput increased from 2,738 to 3,382 operations per second,
or 23.5 percent. Mean callback interval decreased by 25 percent and maximum
callback interval decreased by 44 percent.

Requested collection time improved for every 500,000-object heap shape. The
geometric-mean improvement was 1.27 times, ranging from 1.13 times for the AI
workload to 1.46 times for graph.

The sustained synthetic result contains material regressions despite a
3.0 percent throughput geometric mean:

- Chain throughput decreased by 8.0 percent. Mean callback interval increased
  from 4.26 to 5.35 seconds by 26 percent, and the maximum increased from 28.8
  to 41.1 seconds by 43 percent. Four of five paired runs had a higher mean
  interval in parallel mode.
- AI-workload throughput decreased by 7.9 percent. Mean callback interval
  increased from 2.16 to 3.07 seconds by 42 percent, and the maximum increased
  from 11.4 to 15.8 seconds by 38 percent. Every parallel run had a higher
  mean interval than its serial counterpart.
- Graph throughput increased, but its maximum callback interval increased
  from 409 to 590 milliseconds by 44 percent. Four of five parallel runs
  exceeded the largest serial interval.

The free-threaded result supports a large improvement on the mixed workload
and requested 500,000-object collections. It also identifies chain and AI
sustained workloads as unresolved throughput and callback-latency regressions.

## Incomplete overnight work

The GIL adaptive-versus-fixed campaigns completed for fixed counts 2, 4, 8,
and 16. They are not analysed here because the equivalent free-threaded
campaign did not run. The optimized free-threaded build does not expose the
debug-only phase-dispatch counter used by the benchmark's warm-up assertion.
The benchmark stopped before its first free-threaded measurement.

Neither current-head pyperformance campaign ran. The overnight sequence
stopped before reaching them. The fresh optimized builds also lacked `zlib`
and `_sqlite3`, so they are not suitable pyperformance executables. These are
benchmark-environment failures, not collector results.

The remaining work is to provide release-build dispatch observability through
private test infrastructure, rerun both adaptive-versus-fixed campaigns with
one harness revision, implement and verify free-threaded lazy pool creation,
rebuild with the complete optional dependency set, and repeat the
free-threaded project and pyperformance benchmarks.
