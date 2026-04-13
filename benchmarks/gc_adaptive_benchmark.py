#!/usr/bin/env python3
"""
Dynamic Workload Benchmark for Adaptive Worker Count Controller

Validates that the stochastic hill-climbing controller adapts to changing
workloads. Cycles through three phases with different GC load profiles:

Phase 1 - Dense Graph (simulates training): Many objects with high connectivity.
  Optimal workers: high (6-8) due to large traversal work.

Phase 2 - Shallow/Wide (simulates serving): Many small independent objects.
  Optimal workers: medium (3-4) — parallelism helps but less per-object work.

Phase 3 - Allocation Spike (simulates checkpoint): Rapid alloc/dealloc,
  small heaps, frequent gen0 collections.
  Optimal workers: low (2) — overhead dominates on small heaps.

Usage:
    python gc_adaptive_benchmark.py                # Full dynamic benchmark
    python gc_adaptive_benchmark.py --phase-only   # Run phases in isolation
    python gc_adaptive_benchmark.py --json          # JSON output
    python gc_adaptive_benchmark.py --cycles 5      # Number of phase cycles
    python gc_adaptive_benchmark.py --collections-per-phase 20

Requires: --with-parallel-gc build with adaptive controller implemented.
"""

import gc
import sys
import time
import random
import argparse
import json
import os
from datetime import datetime


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
        cluster = [{"id": c * cluster_size + i, "next": None} for i in range(cluster_size)]
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


def phase_alloc_spike(rng, target_objects=5_000):
    """Phase 3: Allocation spike — rapid create/destroy, small heaps.

    Creates and immediately discards small batches of objects,
    triggering frequent gen0 collections. Small heap means parallel
    dispatch overhead dominates — fewer workers is better.
    """
    # Create small batches and immediately discard them to trigger gen0
    survivors = []
    for batch in range(50):
        # Create a small batch with cycles
        objs = [{"batch": batch, "idx": i, "ref": None} for i in range(target_objects // 50)]
        for i in range(len(objs) - 1):
            objs[i]["ref"] = objs[(i + 1) % len(objs)]
        # Keep a few survivors to prevent gen0 from being trivially empty
        if batch % 10 == 0:
            survivors.append(objs)
        # Rest are discarded — triggers gen0 collection
        del objs
        gc.collect(0)  # Force gen0 collection
    return survivors


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
    ("alloc_spike", phase_alloc_spike, 5_000),
]


def run_phase(phase_name, phase_fn, target_objects, rng,
              num_collections, observations):
    """Run a single phase, collecting observations after each GC."""
    for i in range(num_collections):
        # Create workload
        objs = phase_fn(rng, target_objects)

        # Trigger full collection and measure
        t0 = time.perf_counter_ns()
        gc.collect()
        elapsed_ns = time.perf_counter_ns() - t0

        # Observe controller state
        obs = observe_controller_state(generation=2)
        obs["phase"] = phase_name
        obs["collection_index"] = i
        obs["elapsed_ns"] = elapsed_ns
        obs["target_objects"] = target_objects
        observations.append(obs)

        # Drop workload to make objects collectible on next cycle
        del objs


def run_phase_isolation(phase_name, phase_fn, target_objects, rng,
                        worker_counts, num_collections=10):
    """Run a phase with fixed worker counts to find optimal.

    This is the falsification step: if all phases have the same optimal
    worker count, the per-generation controller is unnecessary complexity.
    """
    results = {}
    for workers in worker_counts:
        try:
            gc.enable_parallel(workers)
        except (AttributeError, RuntimeError):
            continue

        times = []
        for _ in range(num_collections):
            objs = phase_fn(rng, target_objects)
            t0 = time.perf_counter_ns()
            gc.collect()
            elapsed_ns = time.perf_counter_ns() - t0
            times.append(elapsed_ns)
            del objs

        results[workers] = {
            "median_ns": int(sorted(times)[len(times) // 2]),
            "mean_ns": int(sum(times) / len(times)),
            "min_ns": min(times),
            "max_ns": max(times),
            "raw_ns": times,
        }

    return results


# =============================================================================
# Main Benchmark
# =============================================================================

def run_dynamic_benchmark(args):
    """Run the full dynamic benchmark: cycle through phases."""
    seed = args.seed
    rng = random.Random(seed)

    observations = []
    num_collections = args.collections_per_phase

    # Ensure parallel GC is enabled
    config = get_parallel_config()
    if not config.get("enabled", False):
        gc.enable_parallel(8)
        config = get_parallel_config()

    print(f"Dynamic Adaptive Benchmark")
    print(f"  Seed: {seed}")
    print(f"  Cycles: {args.cycles}")
    print(f"  Collections per phase: {num_collections}")
    print(f"  Parallel GC available: {is_parallel_gc_available()}")
    print(f"  Config: {config}")
    print()

    for cycle in range(args.cycles):
        print(f"--- Cycle {cycle + 1}/{args.cycles} ---")
        for phase_name, phase_fn, target_objects in PHASES:
            print(f"  Phase: {phase_name} ({num_collections} collections, "
                  f"{target_objects} objects)...", end="", flush=True)

            t0 = time.monotonic()
            run_phase(phase_name, phase_fn, target_objects, rng,
                      num_collections, observations)
            elapsed = time.monotonic() - t0

            # Report latest controller state
            latest = observations[-1] if observations else {}
            workers_val = latest.get("adaptive_workers", "?")
            prev_cost = latest.get("prev_cost_per_obj_ns", "?")
            median_ns = int(sorted(
                o["elapsed_ns"] for o in observations[-num_collections:]
            )[num_collections // 2])

            print(f" {elapsed:.1f}s, median={median_ns/1e6:.1f}ms, "
                  f"workers={workers_val}, prev_cost={prev_cost}")

    return observations


def run_isolation_benchmark(args):
    """Run each phase in isolation with fixed worker counts.

    Falsification: if all phases have the same optimal worker count,
    the per-generation adaptive controller is unnecessary.
    """
    seed = args.seed
    rng = random.Random(seed)

    config = get_parallel_config()
    max_workers = config.get("num_workers", 0)
    if not config.get("enabled", False) or max_workers < 2:
        # Parallel GC not yet enabled; enable with 8 workers to determine max
        gc.enable_parallel(8)
        config = get_parallel_config()
        max_workers = config.get("num_workers", 8)
    worker_counts = [w for w in [2, 3, 4, 6, max_workers] if w <= max_workers]

    print(f"Phase Isolation Benchmark (falsification)")
    print(f"  Seed: {seed}")
    print(f"  Worker counts: {worker_counts}")
    print(f"  Collections per config: {args.collections_per_phase}")
    print()

    all_results = {}
    for phase_name, phase_fn, target_objects in PHASES:
        print(f"Phase: {phase_name} ({target_objects} objects)")
        results = run_phase_isolation(
            phase_name, phase_fn, target_objects, rng,
            worker_counts, args.collections_per_phase
        )
        all_results[phase_name] = results

        # Find optimal
        if results:
            optimal = min(results.items(), key=lambda x: x[1]["median_ns"])
            print(f"  Optimal: {optimal[0]} workers "
                  f"(median {optimal[1]['median_ns']/1e6:.1f}ms)")
            for w, r in sorted(results.items()):
                ratio = r["median_ns"] / optimal[1]["median_ns"]
                print(f"    {w} workers: {r['median_ns']/1e6:.1f}ms ({ratio:.2f}x)")
        print()

    # Check falsification: are the optima different?
    optima = {}
    for phase_name, results in all_results.items():
        if results:
            optima[phase_name] = min(results.items(),
                                     key=lambda x: x[1]["median_ns"])[0]

    if len(set(optima.values())) == 1:
        print("WARNING: All phases have the same optimal worker count "
              f"({list(optima.values())[0]}). Per-generation controller "
              "may be unnecessary complexity.")
    else:
        print(f"CONFIRMED: Phases have different optima: {optima}")
        print("Per-generation adaptive controller is justified.")

    return all_results


def print_adaptation_summary(observations):
    """Print a summary of how the controller adapted across phases."""
    if not observations:
        return

    print("\n=== Adaptation Summary ===\n")

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
            print(f"  {phase}: workers {start_w} → {end_w} "
                  f"over {n} collections")
        else:
            print(f"  {phase}: {n} collections (no worker data)")

        # Timing trend
        first_half = [o["elapsed_ns"] for o in obs_list[:n//2]]
        second_half = [o["elapsed_ns"] for o in obs_list[n//2:]]
        if first_half and second_half:
            median_first = sorted(first_half)[len(first_half)//2]
            median_second = sorted(second_half)[len(second_half)//2]
            improvement = (median_first - median_second) / median_first * 100
            print(f"    Timing: {median_first/1e6:.1f}ms → "
                  f"{median_second/1e6:.1f}ms ({improvement:+.1f}%)")


# =============================================================================
# Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Dynamic workload benchmark for adaptive GC controller")
    parser.add_argument("--seed", type=int, default=42,
                        help="PRNG seed for reproducibility (default: 42)")
    parser.add_argument("--cycles", type=int, default=3,
                        help="Number of phase cycles (default: 3)")
    parser.add_argument("--collections-per-phase", type=int, default=20,
                        help="GC collections per phase (default: 20)")
    parser.add_argument("--phase-only", action="store_true",
                        help="Run phases in isolation with fixed worker counts")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    args = parser.parse_args()

    if not is_parallel_gc_available():
        print("ERROR: Parallel GC not available. Build with --with-parallel-gc.",
              file=sys.stderr)
        sys.exit(1)

    # Set deterministic PRNG for controller if env var supported
    if "GC_TEST_SEED" not in os.environ:
        os.environ["GC_TEST_SEED"] = str(args.seed)

    if args.phase_only:
        results = run_isolation_benchmark(args)
        if args.json:
            # Convert raw_ns lists for JSON serialization
            print(json.dumps(results, indent=2, default=str))
    else:
        observations = run_dynamic_benchmark(args)
        print_adaptation_summary(observations)
        if args.json:
            print(json.dumps(observations, indent=2, default=str))


if __name__ == "__main__":
    main()
