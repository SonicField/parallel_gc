# GIL full synthetic benchmark failure — 2026-09-30

## Configuration

- Platform: Linux aarch64, 72 available CPUs
- Python: CPython 3.16.0a0, revision `323d3cc90adcc5dcc799f79812edd339b347a46c`
- Configure arguments: `--with-parallel-gc --enable-optimizations --with-lto`
- Optimization evidence: `-O3`, `-flto`, `-fprofile-use`, and `-fprofile-correction`
- Parallel-GC worker ceiling: 16
- Benchmark duration: 60 seconds per run
- Runs per configuration: 5
- Ordering: ABBA (alternating serial/parallel order)
- Heap size: 500,000 objects
- Application threads: 4

Command, run from `build-benchmark-restored-gil`:

```sh
./python ../benchmarks/gc_perf_benchmark.py \
    --full \
    --include-synthetic \
    --output \
    ../benchmarks/results/arm64-316-gil-adaptive-full-2026-09-30.md
```

## Completed results before the failure

The report was not written because the process terminated before the suite
completed. These results are retained as diagnostic evidence, not presented as
a completed benchmark report.

### Mixed workload

| Metric | Serial | Parallel adaptive | Change |
|---|---:|---:|---:|
| Throughput | 2,404/s | 2,226/s | -7.4% |
| Run range | 2,391–2,412/s | 2,220–2,234/s | |
| Mean callback latency | 1.7 ms | 5.0 ms | +192% |

### Requested collection time

| Heap type | Serial | Parallel adaptive | Speedup |
|---|---:|---:|---:|
| chain | 157.7 ms | 174.1 ms | 0.91x |
| tree | 191.5 ms | 206.9 ms | 0.93x |
| wide_tree | 196.3 ms | 243.8 ms | 0.81x |
| graph | 447.0 ms | 447.5 ms | 1.00x |
| layered | 316.6 ms | 290.7 ms | 1.09x |
| independent | 210.4 ms | 203.4 ms | 1.03x |
| ai_workload | 181.4 ms | 191.7 ms | 0.95x |
| web_server | 192.9 ms | 178.5 ms | 1.08x |

### Synthetic chain throughput

| Metric | Serial | Parallel adaptive | Change |
|---|---:|---:|---:|
| Throughput | 2,948,935/s | 3,176,945/s | +7.7% |
| Run range | 2,915,745–2,997,837/s | 3,164,153–3,200,880/s | |
| Mean callback latency | 41 ms | 42 ms | +1% |

## Failure

The process received `SIGSEGV` when it entered synthetic graph throughput.
The failure is independently reproducible with one parallel graph run:

```sh
./python -X faulthandler -c \
    "import sys; sys.path.insert(0, '../benchmarks'); \
import gc_perf_benchmark as b; \
b.run_synthetic_benchmark(duration_sec=10.0, heap_size=500000, \
heap_type='graph', num_threads=4, parallel_workers=16)"
```

Control observations:

- The equivalent optimized serial run (`parallel_workers=0`) completed.
- The optimized parallel run reproduced `SIGSEGV` in about one second.
- The faulting thread was a parallel-GC helper while the initiating Python
  thread waited in `_PyGC_DispatchAndWait()` from
  `_PyGC_ParallelMoveUnreachable()`.
- A pydebug parallel run completed, but emitted many
  `freed object ... in drain buffer` warnings.

## Working hypothesis and falsification evidence

The current hypothesis is that `_PyGC_PHASE_MARK_ALIVE_QUEUE` can finish with
objects still in a worker deque. Its per-batch cleanup drains the local buffer,
refills at most 512 objects from the deque, and drains the local buffer once;
it does not repeat until the deque is empty. The next collection can therefore
consume stale pointers to objects freed after the previous collection.

A conditional GDB breakpoint immediately after
`_PyGC_ParallelMarkAliveFromQueue()` dispatch verified that worker deques were
not empty at phase completion. In one observed collection the first four
workers retained respectively 512, 5,120, 0, and 0 entries. This falsifies the
required invariant that all phase work has been drained before collection
continues.

No collector fix was made as part of the benchmark run.

## Follow-up correction

The pre-mark design was retained. The worker now drains its local buffer and
private deque repeatedly after the shared queue reports completion, and debug
builds assert that both are empty before the worker completes the phase. This
changes only the erroneous phase-completion condition; it does not clear or
discard traversal work.

Verification after the correction:

- GIL pydebug affected-area suites: 130 tests passed, with two expected
  free-threaded-only module skips.
- GIL PGO/LTO focused suites: 69 tests passed, one expected skip.
- The former optimized 500,000-object graph reproducer completed for 10 and
  60 seconds.
- Ten consecutive optimized 25,000-object graph stress runs completed.
- The free-threaded focused check passed 34 tests with two expected skips.

The subsequent full 60-second, five-run ABBA suite completed after this
correction and the 16,384-candidate serial-dispatch threshold. In particular,
all five 500,000-object graph collection samples and all five sustained graph
throughput samples completed. The replacement report is
`arm64-316-gil-adaptive-threshold-full-2026-09-30.md`; this file remains the
record of the superseded failure and its diagnosis.
