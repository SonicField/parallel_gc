"""Run existing controlled cases only; not a full-suite performance result."""
import dataclasses
import json
import math
import os
from pathlib import Path
import statistics
import sys
import sysconfig

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import gc_perf_benchmark as benchmark

HEAP_TYPES = (
    "chain", "tree", "wide_tree", "graph", "layered", "independent",
    "ai_workload", "web_server",
)


def validate_result(row, heap_type):
    for field, expected in (("heap_type", heap_type), ("heap_size", 500000),
                            ("num_runs", 5)):
        if row.get(field) != expected:
            raise ValueError(f"{field}: expected {expected!r}, got {row.get(field)!r}")
    for mode in ("serial", "parallel"):
        samples = row.get(f"{mode}_samples_ms")
        counts = row.get(f"{mode}_object_counts")
        if not isinstance(samples, list) or len(samples) != 5:
            raise ValueError(f"{heap_type}/{mode}: expected five samples, got {samples!r}")
        if any(type(value) not in (int, float) or not math.isfinite(value)
               or value < 0 for value in samples):
            raise ValueError(f"{heap_type}/{mode}: invalid collection times {samples!r}")
        if not isinstance(counts, list) or len(counts) != 5:
            raise ValueError(f"{heap_type}/{mode}: expected five counts, got {counts!r}")
        if any(type(value) is not int or value <= 0 for value in counts):
            raise ValueError(f"{heap_type}/{mode}: invalid generated counts {counts!r}")
        for field, expected in (
            (f"{mode}_time_ms", statistics.mean(samples)),
            (f"{mode}_stdev", statistics.stdev(samples)),
        ):
            actual = row.get(field)
            if type(actual) not in (int, float) or not math.isfinite(actual):
                raise ValueError(f"{heap_type}: invalid {field} {actual!r}")
            if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"{heap_type}: {field} {actual!r} differs from samples {expected!r}")
    if row["serial_object_counts"] != row["parallel_object_counts"]:
        raise ValueError(f"{heap_type}: generated counts differ between collector arms")


def run_cases(worker_ceiling):
    if tuple(benchmark.HEAP_GENERATORS) != HEAP_TYPES:
        raise ValueError("benchmark heap cases/order differ from the recorded full suite")
    if (benchmark.BENCHMARK_SEED, benchmark.COLLECTION_WARMUP_RUNS,
        benchmark.COLLECTION_SURVIVOR_RATIO,
        benchmark.COLLECTION_CREATION_THREADS) != (42, 3, 0.8, 4):
        raise ValueError("benchmark constants differ from the recorded full suite")
    rows = []
    for rooting in ("frame", "module"):
        for heap_type in HEAP_TYPES:
            print(f"CASE={rooting}/{heap_type}", file=sys.stderr, flush=True)
            result = benchmark.run_collection_benchmark(
                heap_size=500000, heap_type=heap_type, num_runs=5,
                parallel_workers=worker_ceiling, survivor_ratio=0.8,
                creation_threads=4, warmup_runs=3, rooting=rooting,
            )
            row = dataclasses.asdict(result)
            validate_result(row, heap_type)
            row["rooting"] = rooting
            rows.append(row)
    return rows


def main():
    import _decimal
    import decimal

    if decimal.Decimal is not _decimal.Decimal:
        raise ValueError("native decimal is required for the recorded build pair")
    if sysconfig.get_config_var("Py_DEBUG"):
        raise ValueError("debug builds are not measurement builds")
    if not sysconfig.get_config_var("Py_GIL_DISABLED") or sys._is_gil_enabled():
        raise ValueError("this diagnostic requires a compiled and runtime FT build")
    flags = sysconfig.get_config_var("CONFIG_ARGS") or ""
    if "--enable-optimizations" not in flags or "--with-lto" not in flags:
        raise ValueError("the recorded PGO+LTO configuration is required")
    if sorted(os.sched_getaffinity(0)) != list(range(32)):
        raise ValueError("the recorded CPU affinity 0-31 is required")
    initial = benchmark.gc.get_parallel_config()
    if not initial["available"] or initial["enabled"] or initial["pool_active"]:
        raise ValueError(f"expected available, initially disabled GC with no pool: {initial!r}")
    runtime_config = benchmark.enable_parallel_gc()
    benchmark.disable_parallel_gc()
    metadata = benchmark.get_system_metadata()
    rows = run_cases(runtime_config["num_workers"])
    final = benchmark.gc.get_parallel_config()
    if (sys._is_gil_enabled() or final["startup_failed"]
            or not final["enabled"] or not final["pool_active"]):
        raise ValueError(f"runtime mode or pool startup failed during diagnostic: {final!r}")
    print(json.dumps({
        "scope": "focused-controlled-collections-not-full-suite",
        "build_type": benchmark.BUILD_TYPE,
        "system_metadata": metadata,
        "parameters": {"heap_size": 500000, "num_runs": 5, "seed": 42,
                       "warmup_runs": 3, "creation_threads": 4,
                       "survivor_ratio": 0.8},
        "runtime_config": runtime_config,
        "config_after": final,
        "runtime_gil_enabled_after": sys._is_gil_enabled(),
        "collections": rows,
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
