#!/usr/bin/env python3
"""Measure adaptive and fixed-worker parallel GC on changing workloads.

This program runs one experimental arm per process. Use separate processes in
an ABBA order to compare the adaptive controller with a fixed worker count.
The fixed arms use a private test API and do not represent a public runtime
configuration interface.

The workload cycles through three phases with different GC load profiles:

Phase 1 - Dense Graph (simulates training): Many objects with high connectivity.
Phase 2 - Shallow/Wide (simulates serving): Many small independent objects.
Phase 3 - Small Cycles: Small independent cyclic batches.

Usage:
    python gc_adaptive_benchmark.py --workers adaptive
    python gc_adaptive_benchmark.py --workers 4
    python gc_adaptive_benchmark.py --json
    python gc_adaptive_benchmark.py --cycles 5
    python gc_adaptive_benchmark.py --collections-per-phase 20

Requires: --with-parallel-gc build with adaptive controller implemented.
"""

import argparse
import gc
import json
import os
import platform
import random
import sys
import time


REPORT_STREAM = sys.stdout


def report(*args, **kwargs):
    print(*args, file=REPORT_STREAM, **kwargs)


# =============================================================================
# Build Detection
# =============================================================================

def is_parallel_gc_available():
    """Check if parallel GC with adaptive controller is available."""
    try:
        config = gc.get_parallel_config()
        return config.get('available', False)
    except AttributeError:
        return False


def get_parallel_config():
    """Get current parallel GC config, or empty dict if unavailable."""
    try:
        return gc.get_parallel_config()
    except AttributeError:
        return {}


def get_parallel_stats():
    """Get current parallel GC stats, or empty dict if unavailable."""
    try:
        return gc.get_parallel_stats()
    except AttributeError:
        return {}


def make_json_document(args, observations):
    return {
        "protocol": {
            "seed": args.seed,
            "cycles": args.cycles,
            "collections_per_phase": args.collections_per_phase,
            "workers": args.workers,
        },
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "compiler": platform.python_compiler(),
        },
        "platform": {
            "description": platform.platform(),
            "machine": platform.machine(),
        },
        "parallel_config": get_parallel_config(),
        "observations": observations,
    }


def parse_worker_mode(value, num_workers):
    """Return a fixed worker count, or None for the adaptive controller."""
    if value == "adaptive":
        return None
    try:
        workers = int(value)
    except ValueError as exc:
        raise ValueError(
            "--workers must be 'adaptive' or an integer"
        ) from exc
    if not 2 <= workers <= num_workers:
        raise ValueError(
            f"fixed workers must be between 2 and {num_workers}, got {workers}"
        )
    return workers


def set_fixed_workers(workers):
    """Pin the next collection to a worker count through a private test API."""
    try:
        import _testinternalcapi
        setter = _testinternalcapi.parallel_gc_set_adaptive_workers
    except (ImportError, AttributeError) as exc:
        raise RuntimeError(
            "this build lacks the fixed-worker benchmark control"
        ) from exc
    setter(workers)


def candidate_total():
    return sum(item.get("candidates", 0) for item in gc.get_stats())


def dispatch_counter():
    """Return the build-specific parallel-dispatch counter name and value."""
    try:
        import _testinternalcapi
    except ImportError:
        _testinternalcapi = None
    if _testinternalcapi is not None:
        get_test_count = getattr(
            _testinternalcapi,
            "parallel_gc_dispatch_count",
            None,
        )
        if get_test_count is not None:
            return "test_parallel_dispatches", get_test_count()

    stats = get_parallel_stats()
    if "collections_attempted" in stats:
        return "gil_collection_attempts", stats["collections_attempted"]
    get_pool_stats = getattr(gc, "_get_thread_pool_stats", None)
    if get_pool_stats is not None:
        pool_stats = get_pool_stats()
        return "ft_phase_dispatches", pool_stats["collections_completed"]
    raise RuntimeError("this build does not expose a parallel dispatch counter")


def prime_parallel_pool(target_objects=20_000):
    """Start helpers before measurement with a live, eligible collection."""
    counter_name, dispatches_before = dispatch_counter()
    candidates_before = candidate_total()
    warmup = [[None] for _ in range(target_objects)]
    gc.collect(0)
    del warmup
    counter_name_after, dispatches_after = dispatch_counter()
    if counter_name_after != counter_name:
        raise RuntimeError("parallel dispatch counter changed during warmup")
    dispatches = dispatches_after - dispatches_before
    candidates = candidate_total() - candidates_before
    if dispatches < 1 or candidates < target_objects:
        raise RuntimeError(
            "pool warmup did not dispatch an eligible parallel collection: "
            f"dispatches={dispatches}, candidates={candidates}"
        )


# =============================================================================
# Workload Generators
# =============================================================================

def phase_dense_graph(rng, target_objects=100_000):
    """Phase 1: Dense graph — high connectivity, deep traversal.

    Creates a graph of dicts with 5-10 cross-references each, forming
    dense cycles. This maximises per-object traversal cost, making
    parallelism profitable with more workers.
    """
    nodes = [{"id": i, "refs": []} for i in range(target_objects)]
    for i in range(target_objects):
        num_refs = rng.randint(5, 10)
        targets = rng.sample(range(target_objects), min(num_refs, target_objects))
        for t in targets:
            nodes[i]["refs"].append(nodes[t])
    return nodes


def phase_shallow_wide(rng, target_objects=100_000):
    """Phase 2: Shallow/wide — many independent small objects.

    Creates clusters of 10 objects with internal cycles but few
    cross-cluster references. Per-object traversal is cheap, so
    dispatch overhead is a larger fraction of total cost.
    """
    cluster_size = 10
    num_clusters = target_objects // cluster_size
    clusters = []
    for c in range(num_clusters):
        cluster = [
            {"id": c * cluster_size + i, "next": None}
            for i in range(cluster_size)
        ]
        # Internal cycle within cluster
        for i in range(cluster_size):
            cluster[i]["next"] = cluster[(i + 1) % cluster_size]
        clusters.append(cluster)

    # Sparse cross-cluster references (1% of clusters)
    num_cross = max(1, num_clusters // 100)
    for _ in range(num_cross):
        a = rng.randint(0, num_clusters - 1)
        b = rng.randint(0, num_clusters - 1)
        if a != b:
            clusters[a][0]["cross"] = clusters[b][0]

    return clusters


def phase_small_cycles(rng, target_objects=5_000):
    """Phase 3: small independent cyclic batches."""
    batches = []
    for batch in range(50):
        objs = [
            {"batch": batch, "idx": i, "ref": None}
            for i in range(target_objects // 50)
        ]
        for i in range(len(objs) - 1):
            objs[i]["ref"] = objs[(i + 1) % len(objs)]
        batches.append(objs)
    return batches


# =============================================================================
# Observation
# =============================================================================

def observe_controller_state(generation=None):
    """Capture the current adaptive controller state after a collection."""
    config = get_parallel_config()
    stats = get_parallel_stats()

    state = {
        "timestamp": time.monotonic(),
    }

    # Adaptive worker count (random walk position)
    if "adaptive_workers" in config:
        state["adaptive_workers"] = config["adaptive_workers"]

    # Previous per-object cost (random walk comparison baseline)
    if "prev_cost_per_obj_ns" in stats:
        state["prev_cost_per_obj_ns"] = stats["prev_cost_per_obj_ns"]

    state["num_workers"] = config.get("num_workers", 0)
    state["enabled"] = config.get("enabled", False)

    if generation is not None:
        state["generation"] = generation

    return state


# =============================================================================
# Phase Runner
# =============================================================================

PHASES = [
    ("dense_graph", phase_dense_graph, 100_000),
    ("shallow_wide", phase_shallow_wide, 100_000),
    ("small_cycles", phase_small_cycles, 5_000),
]


def run_phase(phase_name, phase_fn, target_objects, rng,
              num_collections, observations, *, fixed_workers=None,
              worker_setter=set_fixed_workers, cycle_index=0):
    """Run a single phase, collecting observations after each GC."""
    for i in range(num_collections):
        # Create workload
        objs = phase_fn(rng, target_objects)

        # Measure collection of this workload, not a live-heap traversal or
        # garbage retained from the preceding iteration.
        del objs

        counter_name, dispatches_before = dispatch_counter()
        candidates_before = candidate_total()

        if fixed_workers is not None:
            worker_setter(fixed_workers)
        workers_used = get_parallel_config().get("adaptive_workers")

        # Trigger full collection and measure
        t0 = time.perf_counter_ns()
        gc.collect()
        elapsed_ns = time.perf_counter_ns() - t0

        # Observe controller state
        obs = observe_controller_state(generation=2)
        stats_after = get_parallel_stats()
        candidates = candidate_total() - candidates_before
        counter_name_after, dispatches_after = dispatch_counter()
        if counter_name_after != counter_name:
            raise RuntimeError("parallel dispatch counter changed during run")
        dispatches = dispatches_after - dispatches_before
        obs["phase"] = phase_name
        obs["cycle_index"] = cycle_index
        obs["collection_index"] = i
        obs["elapsed_ns"] = elapsed_ns
        obs["target_objects"] = target_objects
        obs["mode"] = (
            "adaptive" if fixed_workers is None else f"fixed-{fixed_workers}"
        )
        obs["workers_used"] = workers_used
        obs["candidates"] = candidates
        obs["dispatch_counter"] = counter_name
        obs["dispatch_counter_delta"] = dispatches
        total_ns = stats_after.get("phase_timing", {}).get("total_ns", 0)
        obs["parallel_total_ns"] = total_ns
        obs["parallel_ns_per_candidate"] = (
            total_ns / candidates
            if dispatches > 0 and candidates > 0
            else None
        )
        observations.append(obs)


# =============================================================================
# Main Benchmark
# =============================================================================

def run_dynamic_benchmark(args):
    """Run the full dynamic benchmark: cycle through phases."""
    seed = args.seed
    rng = random.Random(seed)

    observations = []
    num_collections = args.collections_per_phase

    # Disable automatic collections so workload construction cannot add
    # unobserved controller measurements between explicit collections.
    gc.disable()

    # Start each process arm from a newly enabled controller so the requested
    # seed is applied before the first measurement.
    config = get_parallel_config()
    if config.get("enabled", False):
        gc.disable_parallel()
    gc.enable_parallel()
    config = get_parallel_config()
    fixed_workers = parse_worker_mode(args.workers, config["num_workers"])

    # Thread creation is intentionally excluded from these steady-state arms.
    # Lazy-start overhead is measured separately by the pyperformance suite.
    prime_parallel_pool()
    if fixed_workers is not None:
        set_fixed_workers(fixed_workers)
    config = get_parallel_config()

    report("Adaptive Worker Benchmark")
    report(f"  Seed: {seed}")
    report(f"  Cycles: {args.cycles}")
    report(f"  Collections per phase: {num_collections}")
    report(f"  Parallel GC available: {is_parallel_gc_available()}")
    mode = "adaptive" if fixed_workers is None else f"fixed-{fixed_workers}"
    report(f"  Worker mode: {mode}")
    report(f"  Config: {config}")
    report()

    for cycle in range(args.cycles):
        report(f"--- Cycle {cycle + 1}/{args.cycles} ---")
        for phase_name, phase_fn, target_objects in PHASES:
            report(f"  Phase: {phase_name} ({num_collections} collections, "
                   f"{target_objects} objects)...", end="", flush=True)

            t0 = time.monotonic()
            run_phase(phase_name, phase_fn, target_objects, rng,
                      num_collections, observations,
                      fixed_workers=fixed_workers, cycle_index=cycle)
            elapsed = time.monotonic() - t0

            # Report latest controller state
            latest = observations[-1] if observations else {}
            workers_val = latest.get("adaptive_workers", "?")
            prev_cost = latest.get("prev_cost_per_obj_ns", "?")
            median_ns = int(sorted(
                o["elapsed_ns"] for o in observations[-num_collections:]
            )[num_collections // 2])

            report(f" {elapsed:.1f}s, median={median_ns/1e6:.1f}ms, "
                   f"workers={workers_val}, prev_cost={prev_cost}")

    return observations


def print_adaptation_summary(observations):
    """Print a summary of how the controller adapted across phases."""
    if not observations:
        return

    report("\n=== Adaptation Summary ===\n")

    # Group by phase
    phases_seen = []
    current_phase = None
    for obs in observations:
        if obs["phase"] != current_phase:
            current_phase = obs["phase"]
            phases_seen.append({"phase": current_phase, "observations": []})
        phases_seen[-1]["observations"].append(obs)

    for phase_group in phases_seen:
        phase = phase_group["phase"]
        obs_list = phase_group["observations"]
        n = len(obs_list)

        # Worker count at start and end of phase
        if "adaptive_workers" in obs_list[0]:
            start_w = obs_list[0]["adaptive_workers"]
            end_w = obs_list[-1]["adaptive_workers"]
            report(f"  {phase}: workers {start_w} → {end_w} "
                   f"over {n} collections")
        else:
            report(f"  {phase}: {n} collections (no worker data)")

        # Timing trend
        first_half = [o["elapsed_ns"] for o in obs_list[:n//2]]
        second_half = [o["elapsed_ns"] for o in obs_list[n//2:]]
        if first_half and second_half:
            median_first = sorted(first_half)[len(first_half)//2]
            median_second = sorted(second_half)[len(second_half)//2]
            improvement = (median_first - median_second) / median_first * 100
            report(f"    Timing: {median_first/1e6:.1f}ms → "
                   f"{median_second/1e6:.1f}ms ({improvement:+.1f}%)")


# =============================================================================
# Entry Point
# =============================================================================

def main():
    global REPORT_STREAM

    parser = argparse.ArgumentParser(
        description="Dynamic workload benchmark for adaptive GC controller")
    parser.add_argument("--seed", type=int, default=42,
                        help="PRNG seed for reproducibility (default: 42)")
    parser.add_argument("--cycles", type=int, default=3,
                        help="Number of phase cycles (default: 3)")
    parser.add_argument("--collections-per-phase", type=int, default=20,
                        help="GC collections per phase (default: 20)")
    parser.add_argument(
        "--workers",
        default="adaptive",
        help="'adaptive' or a fixed count from 2 to the build ceiling",
    )
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    args = parser.parse_args()

    if not is_parallel_gc_available():
        print("ERROR: Parallel GC not available. Build with --with-parallel-gc.",
              file=sys.stderr)
        sys.exit(1)

    if args.json:
        REPORT_STREAM = sys.stderr

    # Set deterministic PRNG for controller if env var supported
    if "GC_TEST_SEED" not in os.environ:
        os.environ["GC_TEST_SEED"] = str(args.seed)

    observations = run_dynamic_benchmark(args)
    print_adaptation_summary(observations)
    if args.json:
        document = make_json_document(args, observations)
        print(json.dumps(document, indent=2, default=str))


if __name__ == "__main__":
    main()
