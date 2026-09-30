#!/usr/bin/env python3
"""
High-Locality GC Benchmark

Tests parallel GC performance on memory-local heap layouts where
cache effects dominate and parallelisation is hardest.

This tests sequential chains allocated contiguously - the WORST CASE
for parallel GC traversal, but with real cyclic garbage to collect.

Usage:
    python gc_locality_benchmark.py
    python gc_locality_benchmark.py --size 500000 --survivor-ratio 0.8
"""

import gc
import time
import random
import argparse
import statistics


class Node:
    """Minimal node for chain structures."""
    __slots__ = ['next', 'value']

    def __init__(self, value=0):
        self.next = None
        self.value = value


def build_cyclic_chains(n, cluster_size=100):
    """
    Build isolated circular chains.

    Each chain is: A -> B -> C -> ... -> Z -> A (circular)
    Chains are independent, so discarding one creates cyclic garbage.

    This is the worst case for parallel GC because:
    1. Objects are allocated contiguously (good cache locality)
    2. Traversal within chain is sequential
    3. But chains can be processed independently
    """
    clusters = []
    num_clusters = max(1, n // cluster_size)

    for _ in range(num_clusters):
        # Build circular chain
        nodes = [Node(i) for i in range(cluster_size)]
        for i in range(cluster_size):
            nodes[i].next = nodes[(i + 1) % cluster_size]
        clusters.append(nodes)

    return clusters


def run_gc_timing(create_heap_fn, iterations=5):
    """Run GC and return timing statistics.

    Creates fresh garbage for each iteration to measure actual collection.
    """
    times = []
    collected_counts = []

    for _ in range(iterations):
        # Create fresh heap with garbage for each iteration
        gc.collect()  # Clear any prior state
        keep_refs = create_heap_fn()

        # Time the collection of the garbage
        start = time.perf_counter()
        collected = gc.collect()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        collected_counts.append(collected)

        # Clean up
        del keep_refs

    return {
        'min': min(times),
        'max': max(times),
        'mean': statistics.mean(times),
        'stdev': statistics.stdev(times) if len(times) > 1 else 0,
        'all': times,
        'collected': collected_counts[0] if collected_counts else 0,
    }


def run_benchmark(size, workers, survivor_ratio=0.8, iterations=5, warmup=2):
    """Run the high-locality benchmark with real garbage."""
    print(f"High-Locality GC Benchmark (with real garbage)")
    print(f"=" * 60)
    print(f"Heap size: {size:,} objects")
    garbage_pct = round((1 - survivor_ratio) * 100)
    print(f"Survivor ratio: {survivor_ratio} ({garbage_pct}% garbage)")
    print(f"Parallel GC worker ceiling: {workers}")
    print(f"Iterations: {iterations} (after {warmup} warmup)")
    print()

    def create_heap_with_garbage():
        """Create heap and apply survivor ratio."""
        random.seed(42)
        clusters = build_cyclic_chains(size)
        num_keep = int(len(clusters) * survivor_ratio)
        random.shuffle(clusters)
        keep_refs = clusters[:num_keep]
        # Discard remaining clusters - they become cyclic garbage
        return keep_refs

    # Warmup
    print(f"Warming up ({warmup} iterations)...")
    gc.disable()
    for _ in range(warmup):
        keep_refs = create_heap_with_garbage()
        gc.collect()
        del keep_refs
        gc.collect()
    gc.enable()

    # Serial benchmark
    print()
    print("Running SERIAL benchmark...")
    gc.disable()
    gc.disable_parallel()
    serial_stats = run_gc_timing(create_heap_with_garbage, iterations=iterations)
    gc.collect()
    gc.enable()
    print(f"  Min: {serial_stats['min']:.2f}ms")
    print(f"  Mean: {serial_stats['mean']:.2f}ms")
    print(f"  Max: {serial_stats['max']:.2f}ms")
    print(f"  Collected: {serial_stats['collected']}")

    # Parallel benchmark
    print()
    print("Running PARALLEL benchmark (adaptive workers)...")
    gc.disable()
    gc.enable_parallel()
    config = gc.get_parallel_config()
    if not config.get('enabled'):
        raise RuntimeError(f"parallel GC activation failed: {config!r}")
    parallel_stats = run_gc_timing(create_heap_with_garbage, iterations=iterations)
    gc.collect()
    gc.enable()
    print(f"  Min: {parallel_stats['min']:.2f}ms")
    print(f"  Mean: {parallel_stats['mean']:.2f}ms")
    print(f"  Max: {parallel_stats['max']:.2f}ms")
    print(f"  Collected: {parallel_stats['collected']}")
    phase_timing = gc.get_parallel_stats().get('phase_timing', {})
    if phase_timing:
        print("  Last parallel collection phases:")
        for phase, nanoseconds in sorted(phase_timing.items()):
            print(f"    {phase}: {nanoseconds / 1e6:.3f}ms")

    # Comparison
    print()
    print("=" * 60)
    speedup = serial_stats['mean'] / parallel_stats['mean']
    if speedup >= 1.0:
        print(f"RESULT: {speedup:.2f}x SPEEDUP (parallel is faster)")
    else:
        print(f"RESULT: {1/speedup:.2f}x SLOWDOWN (parallel is slower)")
    print(f"Serial mean: {serial_stats['mean']:.2f}ms")
    print(f"Parallel mean: {parallel_stats['mean']:.2f}ms")
    print(f"Difference: {parallel_stats['mean'] - serial_stats['mean']:.2f}ms")

    return {
        'serial': serial_stats,
        'parallel': parallel_stats,
        'speedup': speedup,
    }


def main():
    parser = argparse.ArgumentParser(description="High-Locality GC Benchmark")
    parser.add_argument('--size', '-s', type=int, default=500000,
                        help='Number of objects in heap (default: 500000)')
    parser.add_argument('--survivor-ratio', '-r', type=float, default=0.8,
                        help='Fraction of objects that survive (default: 0.8)')
    parser.add_argument('--iterations', '-i', type=int, default=5,
                        help='Number of timed iterations (default: 5)')
    parser.add_argument('--warmup', type=int, default=2,
                        help='Number of warmup iterations (default: 2)')
    args = parser.parse_args()

    config_fn = getattr(gc, 'get_parallel_config', None)
    config = config_fn() if config_fn is not None else {}
    if not config.get('available', False):
        print("ERROR: parallel GC is not available in this build")
        return 2
    gc.enable_parallel()
    workers = gc.get_parallel_config()['num_workers']
    gc.disable_parallel()

    run_benchmark(
        size=args.size,
        workers=workers,
        survivor_ratio=args.survivor_ratio,
        iterations=args.iterations,
        warmup=args.warmup,
    )
    return 0


if __name__ == '__main__':
    exit(main())
