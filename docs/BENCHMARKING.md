# Benchmarking Guide

How to run the current benchmark tools and produce reviewable results.

## Quick Start

```bash
git clone --recurse-submodules https://github.com/SonicField/parallel_gc.git
cd parallel_gc

mkdir -p build-benchmark-gil build-benchmark-ft

# Build both optimized configurations in separate directories.
(cd build-benchmark-gil && \
    ../cpython/configure \
        --with-parallel-gc --enable-optimizations --with-lto)
make -C build-benchmark-gil -j"$(nproc)"

(cd build-benchmark-ft && \
    ../cpython/configure \
        --with-parallel-gc --disable-gil --enable-optimizations --with-lto)
make -C build-benchmark-ft -j"$(nproc)"

# Quick sanity checks of the mixed workload.
build-benchmark-gil/python benchmarks/gc_perf_benchmark.py --quick
build-benchmark-ft/python benchmarks/gc_perf_benchmark.py --quick

# Standard mixed-workload runs.
build-benchmark-gil/python benchmarks/gc_perf_benchmark.py
build-benchmark-ft/python benchmarks/gc_perf_benchmark.py

# Longer runs including collection and synthetic-throughput benchmarks
# (runtime is workload- and machine-dependent)
build-benchmark-gil/python benchmarks/gc_perf_benchmark.py \
    --full --include-synthetic
build-benchmark-ft/python benchmarks/gc_perf_benchmark.py \
    --full --include-synthetic
```

The root `Makefile` and scripts under `tools/` target the older project
workflow. Do not use `make build-release`, `make bench-quick`, or the legacy
sanitizer/build helpers for current-port measurements.

---

## Benchmark Scripts

### gc_perf_benchmark.py — Primary Benchmark Suite

The main benchmark measuring parallel GC performance across realistic and synthetic workloads.

**Options:**

| Flag | Description | Default |
|------|-------------|---------|
| `--quick` | Set 2 runs per configuration and a 10-second duration | — |
| `--full` | Set 5 runs per configuration and a 60-second duration | — |
| `--duration, -d` | Duration per benchmark (seconds) | 30 |
| `--runs, -r` | Number of runs per configuration | 3 |
| `--threads, -t` | Application worker threads | 4 |
| `--heap-size, -s` | Objects for synthetic benchmarks | 500,000 |
| `--json, -j` | Output JSON instead of markdown | — |
| `--output, -o` | Output file (default: stdout) | — |
| `--include-synthetic` | Add collection and synthetic-throughput tests | off |

The realistic benchmark is one mixed workload. Its application threads
randomly select from these seven components; it does not report a separate
result for each component.

**Mixed-workload components (7):**

| Workload | Cycles | Description |
|----------|--------|-------------|
| deltablue | HIGH | Constraint solver, bidirectional references |
| deepcopy | HIGH | Tree copy creating cyclic garbage |
| pickle_copy | HIGH | Serialisation round-trip |
| async_tree | HIGH | Async task tree simulation |
| richards | MINIMAL | OS task scheduler simulation |
| nbody | MINIMAL | N-body physics (compute-heavy) |
| comprehensions | NONE | List/dict/set comprehensions (acyclic) |

**Synthetic heap types (8):**

| Heap Type | Description |
|-----------|-------------|
| chain | Circular linked lists |
| tree | Binary trees with back-references |
| wide_tree | Single root, many children |
| graph | Random graphs with cycles |
| layered | Neural-network-like layers |
| independent | Self-referencing isolated clusters |
| ai_workload | ML computation graph with finalisers |
| web_server | HTTP request/response lifecycle |

**Output metrics:**
- **Throughput** (workloads/sec or objects/sec) — mean, stddev, min/max
- **Collection latency** (ms) — mean and max callback-to-callback duration
- **GC callback-active time** (% of wall time; not additive in the
  free-threaded build)
- **Speedup** — ratio of parallel to serial
- **Geometric mean** — collection ratios across all eight heap types, and
  throughput ratios across the three synthetic throughput types

**Examples:**

```bash
# Standard adaptive-worker run
./python ../benchmarks/gc_perf_benchmark.py

# JSON output for automated processing
./python ../benchmarks/gc_perf_benchmark.py --json -o results.json

# Full run with synthetic heaps
./python ../benchmarks/gc_perf_benchmark.py --full --include-synthetic
```

### gc_creation_analysis.py — Multi-Threaded Allocation Impact

Investigates how multi-threaded object creation affects parallel GC performance through heap distribution analysis.

**Modes:**

```bash
# Test impact of creation thread count
./python ../benchmarks/gc_creation_analysis.py --creation-threads --heap ai_workload

# Compare chain vs cluster heap structures
./python ../benchmarks/gc_creation_analysis.py --chain-vs-clusters

# Compare abandoned threads vs thread pool
./python ../benchmarks/gc_creation_analysis.py --abandon-vs-pool --heap ai_workload

# Show one isolated serial/parallel comparison
./python ../benchmarks/gc_creation_analysis.py --comparison --heap ai_workload
```

**Key options:**
- `--threads` — creation threads (default: 1)
- `--size` — objects to create (default: 400,000)
- `--heap` — structure: chain, clusters, ai_workload
- `--survivors` — keep all objects alive (100% survivors)

### gc_locality_benchmark.py — Contiguous Chain Locality

Tests serial and parallel collection on contiguous circular chains. It is a
single-worker-count locality experiment, not a NUMA-scaling benchmark.

```bash
./python ../benchmarks/gc_locality_benchmark.py --size 500000 --survivor-ratio 0.8
```

**Options:**
- `--size, -s` — number of objects (default: 500,000)
- `--survivor-ratio, -r` — fraction surviving (default: 0.8 = 20% garbage)
- `--iterations, -i` — timed iterations (default: 5)
- `--warmup` — warmup iterations (default: 2)

### gc_production_experiment.py — Cyclic Garbage Survey

Measures which project-specific workload patterns produce cyclic garbage.
This helps identify workloads that may benefit from parallel GC.

```bash
# Run all 14 benchmarks
./python ../benchmarks/gc_production_experiment.py

# Specific benchmarks
./python ../benchmarks/gc_production_experiment.py --benchmarks deltablue richards

# List available benchmarks
./python ../benchmarks/gc_production_experiment.py --list

# JSON output
./python ../benchmarks/gc_production_experiment.py --output results.json
```

Classifies each benchmark as HIGH_CYCLES, MODERATE_CYCLES, MINIMAL_CYCLES, or NO_CYCLES.

---

## Methodology

### Reproducibility

`gc_perf_benchmark.py` uses deterministic per-worker random streams seeded
from 42. Its paired collection runs also reconstruct heaps from fixed per-task
streams and reject a serial/parallel pair if the generated object counts
differ. The other multi-threaded tools use Python's process-global generator;
their seed makes single-threaded construction repeatable but does not guarantee
identical multi-threaded heaps. `gc_production_experiment.py` uses
deterministic workloads.

Each result file reports means over the samples in that invocation. Retain all
raw samples and report every invocation rather than selecting a favorable run.
The primary harness aborts on worker exceptions or shutdown timeouts rather
than emitting a partial result. Its JSON records actual generated-object
counts and SHA-256 fingerprints for dirty worktrees; clean published revisions
are still preferred for final evidence.

### Run-to-Run Variance

Collection measurements can have substantial within-run and run-to-run
variance. To obtain useful numbers:

1. Use at least 5 iterations (`--runs 5` or `--full`)
2. Pin to a single NUMA node if possible: `numactl --cpunodebind=0 --membind=0 ./python ...`
3. Run on a quiet machine (no competing workloads)
4. Report every run and the raw samples or their full distribution
5. Record the exact command, both repository commits, dirty state, compiler,
   build flags, configured ceiling and observed adaptive worker counts, and
   affinity/NUMA policy

### Comparing Serial vs Parallel

The benchmarks compare `gc.disable_parallel()` and `gc.enable_parallel()` in
the same Python process and binary. They rebuild equivalent heaps for serial
and parallel measurements; they do not collect the same heap twice.
`gc_perf_benchmark.py` alternates measured serial and parallel runs to reduce
systematic drift.

This same-binary comparison measures the runtime-mode delta. It does not
measure compile-time overhead from building with `--with-parallel-gc`. A
submission campaign must also compare against optimized GIL and free-threaded
builds compiled without the feature.

`gc_perf_benchmark.py` measures both serial and parallel collection latency as
the wall-clock interval between `gc.callbacks` start and stop events. This is
the complete callback span, not a claim about the strictly stop-the-world
portion of free-threaded collection.

### What the Numbers Mean

- **Collection speedup:** How much faster a single `gc.collect()` call is with parallel workers. This is the primary metric.
- **Collection latency:** Callback-to-callback wall-clock duration for both
  serial and parallel modes.
- **Throughput change:** Overall application throughput, including allocation,
  collection, and application work.
- **GC callback-active time:** Sum of callback start-to-stop intervals as a
  percentage of benchmark wall time. In the free-threaded build, intervals can
  overlap application work, so this is not an exclusive overhead percentage
  and should not be added to application time.

---

## Benchmark results

The current full results were collected with optimized PGO+LTO CPython 3.16
builds on the same 72-core AArch64 host. They establish useful large-heap
regions for both collectors and also expose negative regions; they are not a
claim that every workload improves.

| Build | Mixed throughput | 500K requested heaps | Sustained synthetics |
|-------|------------------|----------------------|----------------------|
| GIL | -0.2% | all 8 faster; 1.26x geomean | +9.5% throughput geomean; -26% mean callback interval |
| Free-threaded | +19.5% | all 8 faster; 1.22x geomean | +2.3% throughput geomean; +31% mean callback interval |

The free-threaded sustained aggregate contains a material negative result:
the finalizer-heavy `ai_workload` was -14.7% in throughput and +105% in mean
callback interval. A diagnostic run found similar candidate totals but fewer,
larger parallel collections; the recorded phase timings were dominated by
serial finalization and deallocation. That is a falsifiable explanation to
investigate, not proof of a single cause.

- [GIL full result](../benchmarks/results/arm64-316-gil-adaptive-threshold-full-2026-09-30.md)
- [Free-threaded full result](../benchmarks/results/arm64-316-ft-92f-full-2026-09-30.md)
- [Free-threaded standard result](../benchmarks/results/arm64-316-ft-92f-standard-2026-09-30.md)

The GIL report records the dirty pre-commit worktree later committed as
`92f992042c`; the free-threaded report records that commit directly. Final
submission evidence should repeat both builds from clean, published commits
and add feature-off optimized controls. New result sets must record exact
commits, configuration flags, machine description, command line, raw samples,
and variance.

---

## Tips

- **Always use an optimised build** for benchmarking. Debug builds have assertions and Py_REF_DEBUG overhead that distort results.
- **Warm up** before timing. `gc_perf_benchmark.py` uses 3 fixed collection
  warmups; `gc_locality_benchmark.py` exposes `--warmup` (default: 2).
- **Don't compare across machines** without documenting hardware. NUMA topology, cache sizes, and core count all affect results.
- **The `--quick` flag** is for sanity checking, not publishable results.
  `--full` increases duration and sample count but does not enable synthetic
  tests; add `--include-synthetic` explicitly.
- **Budget enough time.** With the documented 60-second duration and five
  samples, `--full --include-synthetic` has a 40-minute timed floor per build
  before heap construction and cleanup. On the current AArch64 host, allow
  roughly 45–70 minutes per build and run the GIL and free-threaded campaigns
  sequentially.
- **JSON output** (`--json`) is machine-readable for automated analysis and regression tracking.
