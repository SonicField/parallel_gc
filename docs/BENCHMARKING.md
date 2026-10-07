# Benchmarking Guide

How to run the current benchmark tools and produce reviewable results.

## Why this benchmark suite is required

Parallel GC cannot be evaluated solely with a general-purpose Python benchmark
suite. Tools such as `pyperformance` remain useful for detecting broad
interpreter regressions, but many of their workloads create too little cyclic
garbage, run too few substantial collections, or report only whole-program
time. A neutral `pyperformance` result does not show that parallel collection
is effective, ineffective, or even meaningfully exercised.

The benchmark system in this repository is therefore part of the required
evidence for the project. It controls cyclic heap shape and size, exercises
sustained allocation and collection, alternates serial and parallel runs,
records collection and callback intervals as well as throughput, and observes
the adaptive worker controller. Its drivers, workload models, raw results, and
provenance records live outside the CPython fork because they are large,
specialist experimental infrastructure rather than an appropriate addition to
CPython's regression-test tree.

Use `pyperformance` as a complementary whole-interpreter regression check, not
as a substitute for the measurements documented here.

## Whole-interpreter regression with pyperformance

The `pyperformance/` submodule pins the unmodified upstream benchmark suite.
Project-owned activation and verification code lives under
`benchmarks/pyperformance_support/`. Do not patch the submodule to enable
parallel GC.

Create the benchmark driver environment once:

```bash
python3 -m venv .venvs/pyperformance-driver

.venvs/pyperformance-driver/bin/python -m pip install \
    --requirement pyperformance/pyperformance/requirements/requirements.txt

.venvs/pyperformance-driver/bin/python -m pip install \
    --no-deps \
    --editable ./pyperformance \
    --editable ./benchmarks/pyperformance_support
```

The target CPython build must contain its normal optional standard-library
modules. At minimum, `zlib` is required to construct the benchmark virtual
environment. A full suite also requires the dependencies used by its selected
benchmarks. Install CPython's build dependencies before configuring the
optimized interpreter.

Run a short end-to-end check before spending hours on a campaign:

```bash
.venvs/pyperformance-driver/bin/python \
    benchmarks/run_pyperformance.py abba \
    --python build-benchmark-gil/python \
    --benchmarks telco \
    --run-style debug \
    --output-dir benchmarks/results/pyperformance/gil-smoke
```

The debug run verifies the machinery. Its timings are not performance
evidence.

Run the complete comparison with the same optimized binary in both modes:

```bash
.venvs/pyperformance-driver/bin/python \
    benchmarks/run_pyperformance.py abba \
    --python build-benchmark-gil/python \
    --benchmarks default \
    --run-style rigorous \
    --output-dir benchmarks/results/pyperformance/gil-full
```

Repeat the command with the optimized free-threaded binary and a separate
output directory.

The runner uses the order disabled, enabled, enabled, disabled. It preserves
all four raw JSON suites, combines the two runs for each mode, writes the
standard pyperformance comparison, and records repository and executable
provenance in `campaign.json`. This ABBA order cancels first-order linear drift;
it does not remove random variance or machine interference.

Every pyperf worker loads the project support package before measured code.
The support package applies the requested mode, verifies the resulting
`gc.get_parallel_config()` state, and records that state through a pyperf hook.
The runner rejects a result when any benchmark lacks the expected attestation.

The runtime ABBA comparison does not measure the cost of compiling parallel-GC
support into CPython. Measure that separately with matched optimized builds:
one configured without `--with-parallel-gc`, and one configured with the
feature but kept runtime-disabled.

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
builds on the same 72-core AArch64 host. They establish useful regions in the
500,000-requested-object synthetic graphs for both collectors and also expose
negative regions; they are not a claim that every workload improves.

| Build | Mixed throughput | 500K requested heaps | Sustained synthetics |
|-------|------------------|----------------------|----------------------|
| GIL | -0.2% | all 8 faster; 1.26x geomean | +9.5% throughput geomean; -26% mean callback interval |
| Free-threaded | +19.5% | all 8 faster; 1.22x geomean | +2.3% throughput geomean; +31% mean callback interval |

The free-threaded sustained aggregate contains a material negative result:
the finalizer-heavy `ai_workload` was -14.7% in throughput and +105% in mean
callback interval. A diagnostic run found similar candidate totals but fewer,
larger parallel collections and suggested that serial finalization and
deallocation dominated the additional time. No durable raw phase record
accompanies the published result. Treat that observation as a hypothesis, not
as evidence of the cause.

### Free-threaded finalizer/BRC hypothesis

The leading hypothesis is that serial finalization and deletion perform many
decrements from the collecting thread against objects owned by other threads.
Those decrements cannot use the owner-local BRC path. They instead use shared
atomic or queued reference-count processing. A finalizer-driven deallocation
cascade can therefore turn into sustained cross-thread BRC traffic after the
parallel graph phases have completed.

The existing published result does not isolate the serial tail or count
owner-local, shared-atomic, and queued BRC operations during finalization. It
therefore does not establish this mechanism.

A focused experiment must hold graph topology, survivor ratio, finalizer work,
and candidate count constant while changing object ownership. One case creates
the finalizer graph on the collecting thread. Another creates the same graph
on non-collecting threads. Instrumentation must count each BRC path during the
serial finalization and deletion interval. The hypothesis is rejected if the
cross-thread-owned case does not produce both more shared or queued BRC work
and a corresponding increase in the serial tail.

This investigation can explain a performance boundary. It does not expand the
scope of the initial PEP to include BRC changes or parallel finalization.

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
