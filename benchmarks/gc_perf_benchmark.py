#!/usr/bin/env python3
"""
Parallel GC Performance Benchmark Suite

A unified benchmark for measuring parallel GC performance using project-specific
mixed and synthetic workloads. Works with both GIL and free-threaded builds.

Usage:
    python gc_perf_benchmark.py                    # Standard suite (~5 min)
    python gc_perf_benchmark.py --quick            # Quick sanity check (~1 min)
    python gc_perf_benchmark.py --full             # Full suite (~15 min)
    python gc_perf_benchmark.py --json             # Output as JSON
    python gc_perf_benchmark.py --include-synthetic # Also run synthetic stress tests
"""

import argparse
import contextlib
import gc
import hashlib
import json
import os
import pickle
import platform
import queue
import random
import statistics
import subprocess
import sys
import sysconfig
import threading
import time
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# =============================================================================
# Build Detection
# =============================================================================

def detect_build() -> str:
    """Detect whether we're running on a GIL or free-threaded build."""
    try:
        gil_enabled = sys._is_gil_enabled()
        return "free-threaded" if not gil_enabled else "gil"
    except AttributeError:
        return "gil"


def is_parallel_gc_available() -> bool:
    """Check if parallel GC is available."""
    try:
        config = gc.get_parallel_config()
        return config.get('available', False)
    except AttributeError:
        return False


def get_cpu_count() -> int:
    """Get number of CPUs available."""
    try:
        if hasattr(os, "process_cpu_count"):
            return os.process_cpu_count() or 4
        return len(os.sched_getaffinity(0))
    except Exception:
        return os.cpu_count() or 4


BUILD_TYPE = detect_build()
PARALLEL_GC_AVAILABLE = is_parallel_gc_available()
CPU_COUNT = get_cpu_count()
BENCHMARK_SEED = 42
COLLECTION_WARMUP_RUNS = 3
COLLECTION_SURVIVOR_RATIO = 0.8
COLLECTION_CREATION_THREADS = 4


def get_system_metadata() -> Dict[str, Any]:
    """Return reproducibility metadata available from the running process."""
    project_dir = Path(__file__).resolve().parent.parent
    source_dir = Path(sysconfig.get_config_var("srcdir") or ".").resolve()

    def git_state(path: Path) -> Dict[str, Any]:
        try:
            revision = subprocess.run(
                ["git", "-C", str(path), "rev-parse", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            status = subprocess.run(
                ["git", "-C", str(path), "status", "--porcelain",
                 "--untracked-files=normal"],
                check=True, capture_output=True, text=True,
            ).stdout
            patch = subprocess.run(
                ["git", "-C", str(path), "diff", "--binary", "HEAD"],
                check=True, capture_output=True,
            ).stdout
            # Normal porcelain output collapses untracked directories. This
            # keeps out-of-tree builds from being read into the fingerprint;
            # the CPython source worktree's new files are listed individually.
            untracked = [
                line[3:] for line in status.splitlines()
                if line.startswith("?? ")
            ]

            digest = hashlib.sha256(patch)
            for name in sorted(untracked):
                digest.update(name.encode("utf-8", "surrogateescape"))
                candidate = path / name
                if candidate.is_file():
                    digest.update(candidate.read_bytes())
            return {
                "revision": revision,
                "dirty": bool(status),
                "worktree_sha256": digest.hexdigest(),
                "untracked_files": sorted(untracked),
            }
        except (OSError, subprocess.CalledProcessError):
            return {"revision": None, "dirty": None}

    metadata = {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "python_implementation": platform.python_implementation(),
        "python_cache_tag": sys.implementation.cache_tag,
        "python_build": platform.python_build(),
        "python_git": getattr(sys, "_git", None),
        "compiler": platform.python_compiler(),
        "configure_args": sysconfig.get_config_var("CONFIG_ARGS"),
        "cflags": sysconfig.get_config_var("CFLAGS"),
        "ldflags": sysconfig.get_config_var("LDFLAGS"),
        "py_cflags_nodist": sysconfig.get_config_var("PY_CFLAGS_NODIST"),
        "py_ldflags_nodist": sysconfig.get_config_var("PY_LDFLAGS_NODIST"),
        "py_parallel_gc": sysconfig.get_config_var("Py_PARALLEL_GC"),
        "py_gil_disabled": sysconfig.get_config_var("Py_GIL_DISABLED"),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "available_cpu_count": CPU_COUNT,
        "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
        "benchmark_seed": BENCHMARK_SEED,
        "command_line": [sys.executable, *sys.argv],
        "project_git": git_state(project_dir),
        "cpython_git": git_state(source_dir),
    }
    try:
        metadata["cpu_affinity"] = sorted(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        metadata["cpu_affinity"] = None
    try:
        metadata["numa_policy"] = subprocess.run(
            ["numactl", "--show"], check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        metadata["numa_policy"] = None
    return metadata

# =============================================================================
# GC Control
# =============================================================================

def enable_parallel_gc(num_workers: int) -> Dict[str, Any]:
    """Enable parallel GC and verify the effective configuration."""
    if not PARALLEL_GC_AVAILABLE:
        raise RuntimeError("parallel GC is not available in this build")
    gc.enable_parallel(num_workers)
    config = gc.get_parallel_config()
    if not config.get("enabled") or config.get("num_workers") != num_workers:
        raise RuntimeError(
            f"failed to activate parallel GC with {num_workers} workers: "
            f"{config!r}"
        )
    return config


def disable_parallel_gc():
    """Disable parallel GC."""
    if not PARALLEL_GC_AVAILABLE:
        raise RuntimeError("parallel GC is not available in this build")
    gc.disable_parallel()


# =============================================================================
# Result Data Structures
# =============================================================================

@dataclass
class CollectionResult:
    """Result from a single collection benchmark (measures GC collection time)."""
    heap_type: str
    heap_size: int
    serial_time_ms: float
    parallel_time_ms: float
    serial_stdev: float = 0.0
    parallel_stdev: float = 0.0
    num_runs: int = 1
    serial_samples_ms: List[float] = field(default_factory=list)
    parallel_samples_ms: List[float] = field(default_factory=list)
    serial_object_counts: List[int] = field(default_factory=list)
    parallel_object_counts: List[int] = field(default_factory=list)

    @property
    def speedup(self) -> float:
        if self.parallel_time_ms > 0:
            return self.serial_time_ms / self.parallel_time_ms
        return 1.0


@dataclass
class BenchmarkRun:
    """Result from a single benchmark run."""
    throughput: float  # workloads/sec or objects/sec
    collection_time_ms: float
    collection_time_pct: float
    collection_latency_mean_ms: float
    collection_latency_max_ms: float
    collections: int
    duration_sec: float


@dataclass
class BenchmarkResult:
    """Aggregated results from multiple runs of a benchmark."""
    name: str
    description: str
    mode: str  # "serial" or "parallel-N"
    runs: List[BenchmarkRun] = field(default_factory=list)

    @property
    def throughput_mean(self) -> float:
        return statistics.mean(r.throughput for r in self.runs) if self.runs else 0

    @property
    def throughput_stdev(self) -> float:
        if len(self.runs) < 2:
            return 0
        return statistics.stdev(r.throughput for r in self.runs)

    @property
    def throughput_best(self) -> float:
        return max(r.throughput for r in self.runs) if self.runs else 0

    @property
    def throughput_worst(self) -> float:
        return min(r.throughput for r in self.runs) if self.runs else 0

    @property
    def collection_latency_mean(self) -> float:
        values = (r.collection_latency_mean_ms for r in self.runs)
        return statistics.mean(values) if self.runs else 0

    @property
    def collection_latency_stdev(self) -> float:
        if len(self.runs) < 2:
            return 0
        return statistics.stdev(
            r.collection_latency_mean_ms for r in self.runs)

    @property
    def collection_latency_max(self) -> float:
        return max(
            (r.collection_latency_max_ms for r in self.runs), default=0)

    @property
    def collection_time_pct_mean(self) -> float:
        values = (r.collection_time_pct for r in self.runs)
        return statistics.mean(values) if self.runs else 0

    @property
    def total_duration(self) -> float:
        return sum(r.duration_sec for r in self.runs)

    @property
    def total_collections(self) -> int:
        return sum(r.collections for r in self.runs)


@dataclass
class ComparisonResult:
    """Comparison between serial and parallel for a benchmark."""
    benchmark_name: str
    serial: BenchmarkResult
    parallel: BenchmarkResult

    @property
    def speedup(self) -> float:
        if self.serial.throughput_mean == 0:
            return 0
        return self.parallel.throughput_mean / self.serial.throughput_mean

    @property
    def speedup_best(self) -> float:
        if self.serial.throughput_best == 0:
            return 0
        return self.parallel.throughput_best / self.serial.throughput_best

    @property
    def speedup_worst(self) -> float:
        if self.serial.throughput_worst == 0:
            return 0
        return self.parallel.throughput_worst / self.serial.throughput_worst


@dataclass
class SuiteResult:
    """Results from running the full benchmark suite."""
    build_type: str
    parallel_gc_available: bool
    num_workers: int
    timestamp: str
    runtime_config: Dict[str, Any] = field(default_factory=dict)
    system_metadata: Dict[str, Any] = field(default_factory=dict)
    duration_per_benchmark: float = 30.0
    num_runs: int = 3
    num_threads: int = 4
    heap_size: int = 500000
    random_seed: int = BENCHMARK_SEED
    collection_warmup_runs: int = COLLECTION_WARMUP_RUNS
    collection_survivor_ratio: float = COLLECTION_SURVIVOR_RATIO
    collection_creation_threads: int = COLLECTION_CREATION_THREADS
    realistic: Optional[ComparisonResult] = None
    synthetic_by_heap: Dict[str, ComparisonResult] = field(default_factory=dict)
    collection_results: List[CollectionResult] = field(default_factory=list)

    @property
    def geometric_mean_speedup(self) -> float:
        """Geometric mean of speedups across all synthetic heap types."""
        if not self.synthetic_by_heap:
            return 1.0
        speedups = [r.speedup for r in self.synthetic_by_heap.values() if r.speedup > 0]
        if not speedups:
            return 1.0
        product = 1.0
        for s in speedups:
            product *= s
        return product ** (1.0 / len(speedups))

    @property
    def geometric_mean_collection_latency_ratio(self) -> float:
        """Geometric mean of collection-latency ratios."""
        if not self.synthetic_by_heap:
            return 1.0
        ratios = []
        for r in self.synthetic_by_heap.values():
            serial = r.serial.collection_latency_mean
            parallel = r.parallel.collection_latency_mean
            if serial > 0 and parallel > 0:
                ratios.append(parallel / serial)
        if not ratios:
            return 1.0
        product = 1.0
        for ratio in ratios:
            product *= ratio
        return product ** (1.0 / len(ratios))

# =============================================================================
# Project-specific mixed workloads
# =============================================================================

def workload_richards() -> None:
    """Richards benchmark - OS task scheduler simulation."""
    BUFSIZE = 4

    class Packet:
        __slots__ = ['link', 'ident', 'kind', 'datum', 'data']
        def __init__(self, link, ident, kind):
            self.link = link
            self.ident = ident
            self.kind = kind
            self.datum = 0
            self.data = [0] * BUFSIZE

    class TaskRec:
        __slots__ = ['pending', 'work_in', 'device_in', 'control', 'count']
        def __init__(self):
            self.pending = None
            self.work_in = None
            self.device_in = None
            self.control = 1
            self.count = 10000

    class Task:
        __slots__ = [
            'link', 'ident', 'priority', 'input', 'handle', 'task_holding',
            'task_waiting',
        ]
        def __init__(self, ident, priority, input_queue, handle):
            self.link = None
            self.ident = ident
            self.priority = priority
            self.input = input_queue
            self.handle = handle
            self.task_holding = False
            self.task_waiting = False

    tasks = []
    packets = []

    for i in range(6):
        rec = TaskRec()
        t = Task(i, i * 10, None, rec)
        if tasks:
            t.link = tasks[-1]
        tasks.append(t)

        for j in range(3):
            pkt = Packet(None, i, j)
            if packets:
                pkt.link = packets[-1]
            packets.append(pkt)

    for _ in range(100):
        for t in tasks:
            if packets:
                pkt = packets.pop()
                old_input = t.input
                t.input = pkt
                pkt.link = old_input


def workload_deltablue() -> None:
    """DeltaBlue benchmark - constraint solver with bidirectional references."""
    class Variable:
        __slots__ = ['value', 'constraints', 'determined_by', 'walk_strength', 'stay', 'mark']
        def __init__(self, value=0):
            self.value = value
            self.constraints = []
            self.determined_by = None
            self.walk_strength = 0
            self.stay = True
            self.mark = 0

    class Constraint:
        __slots__ = ['strength', 'variables']
        def __init__(self, strength, variables):
            self.strength = strength
            self.variables = variables
            for v in variables:
                v.constraints.append(self)

    variables = [Variable(i) for i in range(50)]
    constraints = []

    for i in range(len(variables) - 1):
        c = Constraint(i % 5, [variables[i], variables[i + 1]])
        constraints.append(c)

    for i in range(0, len(variables) - 2, 2):
        c = Constraint((i + 1) % 5, [variables[i], variables[i + 2]])
        constraints.append(c)


def workload_deepcopy() -> None:
    """Deep copy benchmark - creates cyclic garbage."""
    class Node:
        def __init__(self, value):
            self.value = value
            self.children = []
            self.parent = None

    def build_tree(depth, breadth):
        root = Node(0)
        level = [root]
        for d in range(depth):
            next_level = []
            for parent in level:
                for b in range(breadth):
                    child = Node(d * breadth + b)
                    child.parent = parent
                    parent.children.append(child)
                    next_level.append(child)
            level = next_level
        return root

    tree = build_tree(4, 3)
    for _ in range(5):
        copied = deepcopy(tree)
        del copied


class _PickleDataNode:
    def __init__(self, data):
        self.data = data
        self.refs = []


def workload_pickle_copy() -> None:
    """Pickle copy benchmark - serialization creates temporary objects."""

    nodes = [_PickleDataNode(list(range(100))) for _ in range(20)]
    for i, node in enumerate(nodes):
        node.refs = [nodes[(i + 1) % len(nodes)], nodes[(i + 2) % len(nodes)]]

    for _ in range(3):
        data = pickle.dumps(nodes)
        restored = pickle.loads(data)
        del restored


def workload_async_tree() -> None:
    """Async tree benchmark - simulates async task trees."""
    class AsyncTask:
        __slots__ = ['parent', 'children', 'result', 'state']
        def __init__(self, parent=None):
            self.parent = parent
            self.children = []
            self.result = None
            self.state = 'pending'
            if parent:
                parent.children.append(self)

    def build_task_tree(depth, breadth):
        root = AsyncTask()
        level = [root]
        for _ in range(depth):
            next_level = []
            for parent in level:
                for _ in range(breadth):
                    child = AsyncTask(parent)
                    next_level.append(child)
            level = next_level
        return root

    for _ in range(10):
        tree = build_task_tree(4, 3)
        del tree


def workload_nbody() -> None:
    """N-body simulation - minimal cycles, compute heavy."""
    PI = 3.14159265358979323
    SOLAR_MASS = 4 * PI * PI
    DAYS_PER_YEAR = 365.24

    bodies = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, SOLAR_MASS],
        [4.84143144246472090e+00, -1.16032004402742839e+00, -1.03622044471123109e-01,
         1.66007664274403694e-03 * DAYS_PER_YEAR, 7.69901118419740425e-03 * DAYS_PER_YEAR,
         -6.90460016972063023e-05 * DAYS_PER_YEAR, 9.54791938424326609e-04 * SOLAR_MASS],
        [8.34336671824457987e+00, 4.12479856412430479e+00, -4.03523417114321381e-01,
         -2.76742510726862411e-03 * DAYS_PER_YEAR, 4.99852801234917238e-03 * DAYS_PER_YEAR,
         2.30417297573763929e-05 * DAYS_PER_YEAR, 2.85885980666130812e-04 * SOLAR_MASS],
    ]

    dt = 0.01
    for _ in range(100):
        for i, body1 in enumerate(bodies):
            for body2 in bodies[i + 1:]:
                dx = body1[0] - body2[0]
                dy = body1[1] - body2[1]
                dz = body1[2] - body2[2]
                dist = (dx * dx + dy * dy + dz * dz) ** 0.5
                mag = dt / (dist * dist * dist)
                body1[3] -= dx * body2[6] * mag
                body1[4] -= dy * body2[6] * mag
                body1[5] -= dz * body2[6] * mag
                body2[3] += dx * body1[6] * mag
                body2[4] += dy * body1[6] * mag
                body2[5] += dz * body1[6] * mag


def workload_comprehensions() -> None:
    """List/dict/set comprehensions - no cycles."""
    data = list(range(1000))

    result1 = [x * 2 for x in data if x % 3 == 0]
    result2 = {x: x ** 2 for x in data if x % 5 == 0}
    result3 = {x for x in data if x % 7 == 0}

    nested = [[y * x for y in range(10)] for x in range(100)]

    del result1, result2, result3, nested


# Workload registry with cycle characteristics
REALISTIC_WORKLOADS: Dict[str, Callable] = {
    'deltablue': workload_deltablue,      # HIGH_CYCLES
    'deepcopy': workload_deepcopy,        # HIGH_CYCLES
    'pickle_copy': workload_pickle_copy,  # HIGH_CYCLES
    'async_tree': workload_async_tree,    # HIGH_CYCLES
    'richards': workload_richards,        # MINIMAL_CYCLES
    'nbody': workload_nbody,              # MINIMAL_CYCLES
    'comprehensions': workload_comprehensions,  # NO_CYCLES
}

# =============================================================================
# Synthetic Heap Generators
# =============================================================================
#
# All heap generators return List[List[Node]] - a list of independent cyclic
# clusters. This allows survivor_ratio to work correctly by discarding complete
# clusters, ensuring discarded objects are truly unreachable and can be collected.
#
# In free-threaded builds, GC only collects cyclic garbage; reference counting
# handles acyclic structures. Creating isolated cycles is essential for meaningful
# GC benchmarks.

DEFAULT_CLUSTER_SIZE = 100  # Nodes per cluster


class Node:
    """Generic node for building object graphs."""
    __slots__ = ['refs', 'data', '__weakref__']
    def __init__(self):
        self.refs = []
        self.data = None


class FinalizerNode:
    """Node with a finalizer (__del__ method)."""
    __slots__ = ['refs', 'data', '__weakref__']
    def __init__(self):
        self.refs = []
        self.data = None

    def __del__(self):
        pass  # Presence of __del__ is what matters


class ContainerNode:
    """Node using __dict__ with list and dict children - models real objects."""
    def __init__(self):
        self.children_list = []
        self.children_dict = {}
        self.parent_ref = None


def create_chain(n: int, cluster_size: int = DEFAULT_CLUSTER_SIZE,
                 node_class: type = None,
                 rng: Optional[random.Random] = None) -> List[List]:
    """
    Create isolated circular chains: A -> B -> C -> ... -> Z -> A

    Each cluster is a closed loop, so discarding a cluster creates cyclic garbage.
    """
    if node_class is None:
        node_class = Node
    clusters = []
    num_clusters = max(1, n // cluster_size)

    for _ in range(num_clusters):
        nodes = [node_class() for _ in range(cluster_size)]
        # Make circular
        for i in range(cluster_size):
            nodes[i].refs.append(nodes[(i + 1) % cluster_size])
        clusters.append(nodes)

    return clusters


def create_tree(n: int, cluster_size: int = DEFAULT_CLUSTER_SIZE,
                node_class: type = None,
                rng: Optional[random.Random] = None) -> List[List]:
    """
    Create isolated cyclic trees - each tree has back-references to root.

    Each cluster is a tree where leaves reference back to root, creating cycles.
    """
    if node_class is None:
        node_class = Node
    clusters = []
    num_clusters = max(1, n // cluster_size)
    branching = 2

    for _ in range(num_clusters):
        nodes = []
        root = node_class()
        nodes.append(root)

        # Build tree
        level = [root]
        while len(nodes) < cluster_size:
            next_level = []
            for parent in level:
                for _ in range(branching):
                    if len(nodes) >= cluster_size:
                        break
                    child = node_class()
                    parent.refs.append(child)
                    # Back-reference to root creates cycle
                    child.refs.append(root)
                    next_level.append(child)
                    nodes.append(child)
            if not next_level:
                break
            level = next_level

        clusters.append(nodes)

    return clusters


def create_wide_tree(n: int, cluster_size: int = DEFAULT_CLUSTER_SIZE,
                     node_class: type = None,
                     rng: Optional[random.Random] = None) -> List[List]:
    """
    Create isolated wide trees with cyclic back-references.

    Each cluster has one root with many children, all children ref back to root.
    """
    if node_class is None:
        node_class = Node
    clusters = []
    num_clusters = max(1, n // cluster_size)

    for _ in range(num_clusters):
        nodes = []
        root = node_class()
        nodes.append(root)

        for _ in range(cluster_size - 1):
            child = node_class()
            root.refs.append(child)
            child.refs.append(root)  # Back-reference creates cycle
            nodes.append(child)

        clusters.append(nodes)

    return clusters


def create_graph(n: int, cluster_size: int = DEFAULT_CLUSTER_SIZE,
                 node_class: type = None,
                 rng: Optional[random.Random] = None) -> List[List]:
    """
    Create isolated random graphs with internal cycles.

    Each cluster is a fully-connected random graph with many cycles.
    """
    if node_class is None:
        node_class = Node
    if rng is None:
        rng = random
    clusters = []
    num_clusters = max(1, n // cluster_size)

    for _ in range(num_clusters):
        nodes = [node_class() for _ in range(cluster_size)]

        # Add random edges within cluster
        for node in nodes:
            for _ in range(rng.randint(1, 3)):
                target = rng.choice(nodes)
                node.refs.append(target)

        clusters.append(nodes)

    return clusters


def create_layered(n: int, cluster_size: int = DEFAULT_CLUSTER_SIZE,
                   node_class: type = None,
                   rng: Optional[random.Random] = None) -> List[List]:
    """
    Create isolated layered networks with cycles.

    Each cluster is a mini neural-network-like structure with bidirectional
    references between first and last layers, creating cycles.
    """
    if node_class is None:
        node_class = Node
    if rng is None:
        rng = random
    clusters = []
    num_clusters = max(1, n // cluster_size)
    layers_per_cluster = 4
    nodes_per_layer = cluster_size // layers_per_cluster

    for _ in range(num_clusters):
        all_nodes = []
        first_layer = None
        prev_layer = None

        for layer_idx in range(layers_per_cluster):
            layer = [node_class() for _ in range(nodes_per_layer)]
            all_nodes.extend(layer)

            if first_layer is None:
                first_layer = layer

            if prev_layer:
                # Connect to previous layer
                for node in layer:
                    node.refs.append(rng.choice(prev_layer))

            prev_layer = layer

        # Bidirectional references between first and last layer create cycles
        if prev_layer and first_layer:
            for node in prev_layer:
                node.refs.append(rng.choice(first_layer))
            for node in first_layer:
                node.refs.append(rng.choice(prev_layer))

        clusters.append(all_nodes)

    return clusters


def create_independent(n: int, cluster_size: int = DEFAULT_CLUSTER_SIZE,
                       node_class: type = None,
                       rng: Optional[random.Random] = None) -> List[List]:
    """
    Create isolated self-referencing clusters.

    Each cluster contains nodes that reference each other in a cycle.
    """
    if node_class is None:
        node_class = Node
    clusters = []
    num_clusters = max(1, n // cluster_size)

    for _ in range(num_clusters):
        nodes = [node_class() for _ in range(cluster_size)]
        # Simple cycle: each node refs the next
        for i in range(cluster_size):
            nodes[i].refs.append(nodes[(i + 1) % cluster_size])
        clusters.append(nodes)

    return clusters


def create_ai_workload(
    n: int,
    cluster_size: int = DEFAULT_CLUSTER_SIZE,
    rng: Optional[random.Random] = None,
) -> List[List]:
    """
    Create isolated AI-workload-like clusters with cycles.

    Each cluster models a mini ML computation graph:
    - ContainerNode parents with list and dict children
    - 10% of children have finalizers
    - Cross-references within cluster create cycles
    """
    if rng is None:
        rng = random
    clusters = []
    num_clusters = max(1, n // cluster_size)

    for _ in range(num_clusters):
        all_nodes = []

        # Create parent-child structure with cycles
        num_parents = cluster_size // 6  # Each parent has ~5 children

        parents = []
        for _ in range(num_parents):
            parent = ContainerNode()
            parents.append(parent)
            all_nodes.append(parent)

            # Add 3-5 children
            for j in range(rng.randint(3, 5)):
                if rng.random() < 0.1:
                    child = FinalizerNode()
                else:
                    child = Node()

                all_nodes.append(child)

                if rng.random() < 0.5:
                    parent.children_list.append(child)
                else:
                    parent.children_dict[f"child_{j}"] = child

                # Back-reference to parent creates cycle
                child.refs.append(parent)

        # Cross-references between parents (more cycles)
        for parent in parents:
            if parents:
                parent.children_list.append(rng.choice(parents))

        clusters.append(all_nodes)

    return clusters


def create_web_server(
    n: int,
    cluster_size: int = 200,
    rng: Optional[random.Random] = None,
) -> List[List]:
    """
    Create isolated web server request-like clusters with NO cross-cluster references.

    Each cluster models a single HTTP request/response lifecycle:
    - A Request object (ContainerNode) with headers, body, session
    - Associated Response object with data
    - Middleware/handler chain with back-references (creates cycles)
    - Database result objects

    CRITICAL: No cross-cluster references. Each request is fully independent.
    """
    clusters = []
    num_clusters = max(1, n // cluster_size)

    for _ in range(num_clusters):
        all_nodes = []

        # Request object - the root of this request's object graph
        request = ContainerNode()
        all_nodes.append(request)

        # Headers dict (simulated as nodes)
        for i in range(5):
            header = Node()
            request.children_dict[f"header_{i}"] = header
            all_nodes.append(header)

        # Request body / parsed data
        body = ContainerNode()
        request.children_list.append(body)
        all_nodes.append(body)

        # Session object with back-reference to request (cycle!)
        session = ContainerNode()
        session.children_list.append(request)  # Back-ref creates cycle
        request.children_dict["session"] = session
        all_nodes.append(session)

        # Session data items
        for i in range(10):
            item = Node()
            session.children_list.append(item)
            all_nodes.append(item)

        # Response object
        response = ContainerNode()
        request.children_dict["response"] = response
        response.children_list.append(request)  # Back-ref creates cycle
        all_nodes.append(response)

        # Response body chunks
        for i in range(8):
            chunk = Node()
            response.children_list.append(chunk)
            all_nodes.append(chunk)

        # Middleware chain (each references next and previous - cycles)
        middleware_chain = []
        for i in range(5):
            mw = ContainerNode()
            middleware_chain.append(mw)
            all_nodes.append(mw)
            if i > 0:
                mw.children_list.append(middleware_chain[i-1])  # Prev
                middleware_chain[i-1].children_list.append(mw)  # Next

        # First middleware attached to request
        if middleware_chain:
            request.children_list.append(middleware_chain[0])
            middleware_chain[0].children_list.append(request)  # Cycle

        # Database query results (attached to response)
        db_results = ContainerNode()
        response.children_dict["db_results"] = db_results
        all_nodes.append(db_results)

        # Result rows
        for i in range(15):
            row = Node()
            db_results.children_list.append(row)
            all_nodes.append(row)

        # Fill remaining cluster size with generic handler objects
        remaining = cluster_size - len(all_nodes)
        for _ in range(max(0, remaining)):
            handler = Node()
            # Reference something in the request graph (creates more cycles)
            handler.refs.append(request)
            request.children_list.append(handler)
            all_nodes.append(handler)

        clusters.append(all_nodes)

    return clusters


# All 8 heap types for collection benchmarks
HEAP_GENERATORS = {
    "chain": create_chain,
    "tree": create_tree,
    "wide_tree": create_wide_tree,
    "graph": create_graph,
    "layered": create_layered,
    "independent": create_independent,
    "ai_workload": create_ai_workload,
    "web_server": create_web_server,
}

# =============================================================================
# Collection-latency tracking
# =============================================================================

class CollectionLatencyTracker:
    """Track the wall time between GC start and stop callbacks."""

    def __init__(self):
        self.gc_times_ms: List[float] = []
        self.gc_start_time: Optional[float] = None

    def gc_callback(self, phase: str, info: dict):
        if phase == "start":
            self.gc_start_time = time.perf_counter()
        elif phase == "stop":
            if self.gc_start_time is not None:
                gc_time_ms = (time.perf_counter() - self.gc_start_time) * 1000
                self.gc_times_ms.append(gc_time_ms)

    def reset(self):
        self.gc_times_ms.clear()


def _join_threads_or_raise(
    threads: List[threading.Thread], timeout: float
) -> None:
    """Join all threads within one deadline, or fail without touching state."""
    deadline = time.monotonic() + timeout
    for thread in threads:
        remaining = max(0.0, deadline - time.monotonic())
        thread.join(timeout=remaining)

    alive = [thread.name for thread in threads if thread.is_alive()]
    if alive:
        names = ", ".join(alive)
        raise RuntimeError(
            f"benchmark workers did not stop within {timeout:.1f}s: {names}"
        )

# =============================================================================
# Realistic Benchmark Runner
# =============================================================================

def run_realistic_benchmark(
    duration_sec: float,
    num_threads: int,
    parallel_workers: int = 0,
) -> BenchmarkRun:
    """
    Run the project-specific mixed-workload benchmark.

    Args:
        duration_sec: How long to run
        num_threads: Number of worker threads
        parallel_workers: 0 for serial, >0 for parallel GC
    """
    gc.collect()
    gc.disable()

    if parallel_workers > 0:
        enable_parallel_gc(parallel_workers)
    else:
        disable_parallel_gc()

    tracker = CollectionLatencyTracker()
    gc.callbacks.append(tracker.gc_callback)

    workload_counts: Dict[str, int] = {name: 0 for name in REALISTIC_WORKLOADS}
    workload_list = list(REALISTIC_WORKLOADS.items())
    lock = threading.Lock()
    stop_flag = threading.Event()
    worker_errors: List[BaseException] = []

    def worker(worker_id: int):
        local_counts = {name: 0 for name in REALISTIC_WORKLOADS}
        rng = random.Random(BENCHMARK_SEED + worker_id)
        try:
            while not stop_flag.is_set():
                name, func = rng.choice(workload_list)
                func()
                local_counts[name] += 1
        except BaseException as exc:
            with lock:
                worker_errors.append(exc)
            stop_flag.set()
        finally:
            with lock:
                for name, count in local_counts.items():
                    workload_counts[name] += count

    gc.enable()
    start_time = time.perf_counter()

    threads = [
        threading.Thread(target=worker, args=(i,), daemon=True)
        for i in range(num_threads)
    ]
    for t in threads:
        t.start()

    stop_flag.wait(duration_sec)
    stop_flag.set()

    # Do not alter callbacks or GC state unless every worker has stopped.
    _join_threads_or_raise(threads, timeout=2.0)

    end_time = time.perf_counter()
    gc.disable()

    gc.callbacks.remove(tracker.gc_callback)
    gc.enable()

    if worker_errors:
        raise worker_errors[0]

    actual_duration = end_time - start_time
    total_workloads = sum(workload_counts.values())
    throughput = total_workloads / actual_duration

    total_gc_time = sum(tracker.gc_times_ms)
    collection_time_pct = (total_gc_time / 1000) / actual_duration * 100

    latency_mean = statistics.mean(tracker.gc_times_ms) if tracker.gc_times_ms else 0
    latency_max = max(tracker.gc_times_ms) if tracker.gc_times_ms else 0

    return BenchmarkRun(
        throughput=throughput,
        collection_time_ms=total_gc_time,
        collection_time_pct=collection_time_pct,
        collection_latency_mean_ms=latency_mean,
        collection_latency_max_ms=latency_max,
        collections=len(tracker.gc_times_ms),
        duration_sec=actual_duration,
    )

# =============================================================================
# Synthetic Benchmark Runner
# =============================================================================

def run_synthetic_benchmark(
    duration_sec: float,
    heap_size: int,
    heap_type: str,
    num_threads: int,
    parallel_workers: int = 0,
) -> BenchmarkRun:
    """
    Run synthetic throughput benchmark with specified heap type.
    """
    gc.collect()
    gc.disable()

    if parallel_workers > 0:
        enable_parallel_gc(parallel_workers)
    else:
        disable_parallel_gc()

    tracker = CollectionLatencyTracker()
    gc.callbacks.append(tracker.gc_callback)

    heap_generator = HEAP_GENERATORS[heap_type]
    churn_size = heap_size // 100
    objects_per_thread = heap_size // num_threads
    churn_per_thread = churn_size // num_threads

    total_created = [0]
    lock = threading.Lock()
    stop_flag = threading.Event()
    worker_errors: List[BaseException] = []

    def worker(worker_id: int):
        local_created = 0
        rng = random.Random(BENCHMARK_SEED + worker_id)
        try:
            local_heap = heap_generator(objects_per_thread, rng=rng)
            while not stop_flag.is_set():
                num_discard = min(
                    len(local_heap), churn_per_thread // 100 + 1)
                if num_discard > 0:
                    rng.shuffle(local_heap)
                    local_heap = local_heap[num_discard:]

                new_clusters = heap_generator(churn_per_thread, rng=rng)
                local_heap.extend(new_clusters)
                local_created += sum(len(cluster) for cluster in new_clusters)
        except BaseException as exc:
            with lock:
                worker_errors.append(exc)
            stop_flag.set()
        finally:
            with lock:
                total_created[0] += local_created

    gc.enable()
    start_time = time.perf_counter()

    threads = [
        threading.Thread(target=worker, args=(i,), daemon=True)
        for i in range(num_threads)
    ]
    for t in threads:
        t.start()

    stop_flag.wait(duration_sec)
    stop_flag.set()

    # Do not alter callbacks or GC state unless every worker has stopped.
    _join_threads_or_raise(threads, timeout=2.0)

    end_time = time.perf_counter()
    gc.disable()

    gc.callbacks.remove(tracker.gc_callback)
    gc.enable()

    if worker_errors:
        raise worker_errors[0]

    actual_duration = end_time - start_time
    throughput = total_created[0] / actual_duration

    total_gc_time = sum(tracker.gc_times_ms)
    collection_time_pct = (total_gc_time / 1000) / actual_duration * 100

    latency_mean = statistics.mean(tracker.gc_times_ms) if tracker.gc_times_ms else 0
    latency_max = max(tracker.gc_times_ms) if tracker.gc_times_ms else 0

    return BenchmarkRun(
        throughput=throughput,
        collection_time_ms=total_gc_time,
        collection_time_pct=collection_time_pct,
        collection_latency_mean_ms=latency_mean,
        collection_latency_max_ms=latency_max,
        collections=len(tracker.gc_times_ms),
        duration_sec=actual_duration,
    )

# =============================================================================
# Collection Time Benchmark (measures single GC collection times)
# =============================================================================

class CreationThreadPool:
    """
    Thread pool for object creation that keeps threads alive.

    Keeps threads alive so mimalloc pages remain in live thread heaps rather
    than moving to the abandoned pool.
    """

    def __init__(self, num_threads: int):
        self.num_threads = num_threads
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.threads = []

        for i in range(num_threads):
            t = threading.Thread(target=self._worker, args=(i,), daemon=True)
            t.start()
            self.threads.append(t)

    def _worker(self, thread_id: int):
        """Worker thread that waits for creation tasks."""
        while True:
            try:
                task = self.task_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                if task is None:
                    return

                task_id, heap_type, num_objects, seed = task
                try:
                    clusters = HEAP_GENERATORS[heap_type](
                        num_objects, rng=random.Random(seed))
                except BaseException as exc:
                    self.result_queue.put((task_id, False, exc))
                else:
                    self.result_queue.put((task_id, True, clusters))
            finally:
                self.task_queue.task_done()

    def create_objects(self, heap_type: str, total_objects: int) -> List:
        """Create objects using the thread pool."""
        objects_per_thread = total_objects // self.num_threads

        # Submit tasks
        for task_id in range(self.num_threads):
            self.task_queue.put(
                (task_id, heap_type, objects_per_thread,
                 BENCHMARK_SEED + task_id))

        # Wait for completion
        self.task_queue.join()

        # Collect exactly one result per task. Workers report failures rather
        # than dying and leaving task_queue.join() blocked forever.
        results = {}
        errors = []
        for _ in range(self.num_threads):
            task_id, succeeded, result = self.result_queue.get()
            if succeeded:
                results[task_id] = result
            else:
                errors.append(result)

        if errors:
            raise errors[0]

        all_clusters = []
        for task_id in range(self.num_threads):
            all_clusters.extend(results[task_id])
        return all_clusters

    def shutdown(self):
        """Shutdown the thread pool."""
        for _ in range(self.num_threads):
            self.task_queue.put(None)
        _join_threads_or_raise(self.threads, timeout=2.0)


# Global thread pool kept alive between runs.
_creation_pool = None


def get_creation_pool(num_threads: int) -> CreationThreadPool:
    """Get or create the global creation thread pool."""
    global _creation_pool
    if _creation_pool is None or _creation_pool.num_threads != num_threads:
        if _creation_pool is not None:
            _creation_pool.shutdown()
        _creation_pool = CreationThreadPool(num_threads)
    return _creation_pool


def run_collection_benchmark(
    heap_size: int,
    heap_type: str,
    num_runs: int,
    parallel_workers: int = 8,
    survivor_ratio: float = COLLECTION_SURVIVOR_RATIO,
    creation_threads: int = COLLECTION_CREATION_THREADS,
    warmup_runs: int = COLLECTION_WARMUP_RUNS,
) -> CollectionResult:
    """
    Measure GC collection time for a given heap type.

    Objects are created across a persistent thread pool, so pages remain in
    live thread heaps. The survivor ratio is applied to complete clusters.
    """
    pool = get_creation_pool(creation_threads)
    seed = BENCHMARK_SEED

    def run_batch(
        use_parallel: bool,
        num_iterations: int,
        is_warmup: bool,
    ) -> tuple[List[float], List[int]]:
        """Run a batch and return collection times and generated counts."""
        gc.disable()

        if use_parallel:
            enable_parallel_gc(parallel_workers)
        else:
            disable_parallel_gc()

        times = []
        object_counts = []

        try:
            for _ in range(num_iterations):
                selection_rng = random.Random(seed)

                # Create clusters using thread pool (threads stay alive)
                clusters = pool.create_objects(heap_type, heap_size)
                object_counts.append(
                    sum(len(cluster) for cluster in clusters))

                # Apply survivor ratio by keeping complete CLUSTERS
                keep_refs = None
                if survivor_ratio < 1.0:
                    num_keep = int(len(clusters) * survivor_ratio)
                    if num_keep > 0:
                        selection_rng.shuffle(clusters)
                        keep_refs = clusters[:num_keep]
                    else:
                        keep_refs = []
                else:
                    keep_refs = clusters

                clusters = None  # Release original list

                if is_warmup:
                    # Warmup: just collect and cleanup
                    gc.collect()
                    keep_refs = None
                    gc.collect()
                else:
                    # Timed run: measure collection time
                    start = time.perf_counter()
                    gc.collect()
                    elapsed = (time.perf_counter() - start) * 1000
                    times.append(elapsed)

                    # Cleanup
                    keep_refs = None
                    gc.collect()

        finally:
            gc.enable()

        return times, object_counts

    # Warm each configuration before alternating measured pairs.
    run_batch(use_parallel=False, num_iterations=warmup_runs, is_warmup=True)
    run_batch(use_parallel=True, num_iterations=warmup_runs, is_warmup=True)
    serial_times = []
    parallel_times = []
    serial_object_counts = []
    parallel_object_counts = []
    for iteration in range(num_runs):
        modes = (False, True) if iteration % 2 == 0 else (True, False)
        for use_parallel in modes:
            samples, object_counts = run_batch(
                use_parallel=use_parallel,
                num_iterations=1,
                is_warmup=False,
            )
            if use_parallel:
                parallel_times.extend(samples)
                parallel_object_counts.extend(object_counts)
            else:
                serial_times.extend(samples)
                serial_object_counts.extend(object_counts)

    if serial_object_counts != parallel_object_counts:
        raise RuntimeError(
            f"serial and parallel {heap_type} heaps differ: "
            f"{serial_object_counts!r} != {parallel_object_counts!r}"
        )

    serial_mean = statistics.mean(serial_times)
    parallel_mean = statistics.mean(parallel_times)
    serial_stdev = statistics.stdev(serial_times) if len(serial_times) > 1 else 0
    parallel_stdev = statistics.stdev(parallel_times) if len(parallel_times) > 1 else 0

    return CollectionResult(
        heap_type=heap_type,
        heap_size=heap_size,
        serial_time_ms=serial_mean,
        parallel_time_ms=parallel_mean,
        serial_stdev=serial_stdev,
        parallel_stdev=parallel_stdev,
        num_runs=num_runs,
        serial_samples_ms=serial_times,
        parallel_samples_ms=parallel_times,
        serial_object_counts=serial_object_counts,
        parallel_object_counts=parallel_object_counts,
    )

# =============================================================================
# Suite Runner
# =============================================================================

def run_comparison(
    name: str,
    description: str,
    run_fn: Callable[..., BenchmarkRun],
    num_runs: int,
    parallel_workers: int,
    **kwargs
) -> ComparisonResult:
    """Run a benchmark in both serial and parallel modes."""

    serial_runs = []
    parallel_runs = []
    for iteration in range(num_runs):
        modes = (0, parallel_workers)
        if iteration % 2:
            modes = tuple(reversed(modes))
        for workers in modes:
            run = run_fn(parallel_workers=workers, **kwargs)
            if workers:
                parallel_runs.append(run)
            else:
                serial_runs.append(run)

    serial_result = BenchmarkResult(
        name=name,
        description=description,
        mode="serial",
        runs=serial_runs
    )

    parallel_result = BenchmarkResult(
        name=name,
        description=description,
        mode=f"parallel-{parallel_workers}",
        runs=parallel_runs
    )

    return ComparisonResult(
        benchmark_name=name,
        serial=serial_result,
        parallel=parallel_result
    )


def run_suite(
    duration_per_benchmark: float = 30.0,
    num_runs: int = 3,
    num_threads: int = 4,
    parallel_workers: int = 8,
    heap_size: int = 500000,
    include_synthetic: bool = True
) -> SuiteResult:
    """Run the full benchmark suite."""

    if not PARALLEL_GC_AVAILABLE:
        raise RuntimeError("parallel GC is not available in this build")
    runtime_config = enable_parallel_gc(parallel_workers)
    disable_parallel_gc()

    print(f"Parallel GC Performance Benchmark")
    print(f"=" * 60)
    print(f"Build type: {BUILD_TYPE.upper()}")
    print(f"Parallel GC available: {PARALLEL_GC_AVAILABLE}")
    print(f"CPUs: {CPU_COUNT}")
    print(f"Worker threads: {num_threads}")
    print(f"Parallel GC workers: {parallel_workers}")
    print(f"Duration per benchmark: {duration_per_benchmark}s")
    print(f"Runs per configuration: {num_runs}")
    print(f"Heap size: {heap_size:,}")
    print()

    result = SuiteResult(
        build_type=BUILD_TYPE,
        parallel_gc_available=PARALLEL_GC_AVAILABLE,
        num_workers=parallel_workers,
        timestamp=datetime.now().astimezone().isoformat(),
        runtime_config=runtime_config,
        system_metadata=get_system_metadata(),
        duration_per_benchmark=duration_per_benchmark,
        num_runs=num_runs,
        num_threads=num_threads,
        heap_size=heap_size
    )

    print("Running: Project-specific mixed workload")
    print("-" * 60)
    result.realistic = run_comparison(
        name="mixed_workload",
        description="Project-specific mixed allocation workloads",
        run_fn=run_realistic_benchmark,
        num_runs=num_runs,
        parallel_workers=parallel_workers,
        duration_sec=duration_per_benchmark,
        num_threads=num_threads
    )
    _print_comparison(result.realistic)
    print()

    if include_synthetic:
        # Collection time benchmarks (measures single GC collection time)
        # Run all 8 heap types - these are fast
        all_heap_types = list(HEAP_GENERATORS.keys())
        print("Running: Collection Time Benchmarks (all heap types)")
        print("-" * 60)
        for heap_type in all_heap_types:
            coll = run_collection_benchmark(
                heap_size=heap_size,
                heap_type=heap_type,
                num_runs=num_runs,
                parallel_workers=parallel_workers,
                survivor_ratio=result.collection_survivor_ratio,
                creation_threads=result.collection_creation_threads,
                warmup_runs=result.collection_warmup_runs,
            )
            result.collection_results.append(coll)
            print(
                f"  {heap_type:<12}: {coll.serial_time_ms:6.1f}ms -> "
                f"{coll.parallel_time_ms:6.1f}ms ({coll.speedup:.2f}x)"
            )
        print()

        # Synthetic throughput for a smaller subset (takes longer).
        throughput_heap_types = ["chain", "graph", "ai_workload"]
        for heap_type in throughput_heap_types:
            print(f"Running: Synthetic {heap_type} throughput")
            print("-" * 60)
            comp = run_comparison(
                name=f"synthetic_{heap_type}",
                description=f"{heap_type} heap structure",
                run_fn=run_synthetic_benchmark,
                num_runs=num_runs,
                parallel_workers=parallel_workers,
                duration_sec=duration_per_benchmark,
                heap_size=heap_size,
                heap_type=heap_type,
                num_threads=num_threads
            )
            result.synthetic_by_heap[heap_type] = comp
            _print_comparison(comp)
            print()

        # Print geometric mean summary
        if result.synthetic_by_heap:
            print("Synthetic Summary (geometric mean across heap types)")
            print("-" * 60)
            gm_speedup = result.geometric_mean_speedup
            gm_latency = result.geometric_mean_collection_latency_ratio
            print(f"  Throughput change: {_format_change(gm_speedup)}")
            print(f"  Collection latency change: {(gm_latency - 1) * 100:+.0f}%")
            print()

    return result


def _format_change(ratio: float) -> str:
    """Format a ratio as a percentage change with +/- sign."""
    pct = (ratio - 1) * 100
    if pct >= 0:
        return f"+{pct:.1f}%"
    else:
        return f"{pct:.1f}%"


def _format_latency_ms(ms: float) -> str:
    """Format collection latency with appropriate precision.

    Uses 1 decimal place for values < 10ms to avoid showing "0ms"
    when the actual value is e.g. 0.4ms.
    """
    if ms < 10:
        return f"{ms:.1f}"
    return f"{ms:.0f}"


def _print_comparison(comp: ComparisonResult):
    """Print a comparison result."""
    print(
        f"  Serial:   {comp.serial.throughput_mean:,.0f}/sec "
        f"(range: {comp.serial.throughput_worst:,.0f} - "
        f"{comp.serial.throughput_best:,.0f})"
    )
    print(
        f"  Parallel: {comp.parallel.throughput_mean:,.0f}/sec "
        f"(range: {comp.parallel.throughput_worst:,.0f} - "
        f"{comp.parallel.throughput_best:,.0f})"
    )
    print(f"  Throughput change: {_format_change(comp.speedup)}")
    serial_latency = comp.serial.collection_latency_mean
    if serial_latency > 0:
        parallel_latency = comp.parallel.collection_latency_mean
        change = (parallel_latency / serial_latency - 1) * 100
        print(
            "  Collection latency: "
            f"{_format_latency_ms(serial_latency)}ms -> "
            f"{_format_latency_ms(parallel_latency)}ms ({change:+.0f}%)"
        )

# =============================================================================
# Output Formatters
# =============================================================================

def format_markdown(result: SuiteResult) -> str:
    """Format results as markdown with aligned tables."""
    lines = []
    lines.append("# Parallel GC Performance Benchmark Results")
    lines.append("")
    lines.append("## Configuration")
    lines.append("")
    lines.append(f"- Build type: {result.build_type.upper()}")
    lines.append(f"- Parallel GC available: {result.parallel_gc_available}")
    lines.append(f"- Parallel workers: {result.num_workers}")
    lines.append(f"- Worker threads: {result.num_threads}")
    lines.append(f"- Duration per benchmark: {result.duration_per_benchmark}s")
    lines.append(f"- Runs per configuration: {result.num_runs}")
    lines.append(f"- Heap size (synthetic): {result.heap_size:,}")
    lines.append(f"- Random seed: {result.random_seed}")
    lines.append(
        f"- Collection warmup runs: {result.collection_warmup_runs}")
    lines.append(
        f"- Collection survivor ratio: {result.collection_survivor_ratio}")
    lines.append(
        "- Collection creation threads: "
        f"{result.collection_creation_threads}"
    )
    lines.append(f"- Timestamp: {result.timestamp}")
    lines.append(f"- Runtime parallel-GC config: `{result.runtime_config!r}`")
    for key, value in result.system_metadata.items():
        lines.append(f"- {key.replace('_', ' ').title()}: `{value}`")
    lines.append("")

    # Project-specific mixed-workload results.
    if result.realistic:
        r = result.realistic
        lines.append("## Mixed Workload Throughput")
        lines.append("")
        lines.append("Results for this project's handwritten allocation workload.")
        lines.append("")

        # Runtime info
        serial_dur = r.serial.total_duration
        parallel_dur = r.parallel.total_duration
        serial_coll = r.serial.total_collections
        parallel_coll = r.parallel.total_collections
        lines.append(f"Runtime: {serial_dur + parallel_dur:.0f}s total "
                     f"({serial_coll + parallel_coll} collections)")
        lines.append("")

        # Aligned table for realistic results
        lines.append("| Metric           | Serial             | Parallel           | Change     |")
        lines.append("|------------------|--------------------|--------------------|------------|")

        # Throughput with stddev
        s_tp = f"{r.serial.throughput_mean:,.0f} ± {r.serial.throughput_stdev:,.0f}/s"
        p_tp = f"{r.parallel.throughput_mean:,.0f} ± {r.parallel.throughput_stdev:,.0f}/s"
        change_str = f"{(r.speedup - 1) * 100:+.1f}%"
        lines.append(f"| Throughput       | {s_tp:<18} | {p_tp:<18} | {change_str:<10} |")

        serial_latency = r.serial.collection_latency_mean
        if serial_latency > 0:
            parallel_latency = r.parallel.collection_latency_mean
            serial_stdev = r.serial.collection_latency_stdev
            parallel_stdev = r.parallel.collection_latency_stdev
            s_latency = (
                f"{_format_latency_ms(serial_latency)} ± "
                f"{_format_latency_ms(serial_stdev)}ms"
            )
            p_latency = (
                f"{_format_latency_ms(parallel_latency)} ± "
                f"{_format_latency_ms(parallel_stdev)}ms"
            )
            latency_change = (parallel_latency / serial_latency - 1) * 100
            lines.append(
                f"| Collection latency (mean) | {s_latency:<18} | "
                f"{p_latency:<18} | {latency_change:+.0f}% |"
            )

            s_max = f"{_format_latency_ms(r.serial.collection_latency_max)}ms"
            p_max = f"{_format_latency_ms(r.parallel.collection_latency_max)}ms"
            max_change = (
                r.parallel.collection_latency_max /
                r.serial.collection_latency_max - 1
            ) * 100
            lines.append(
                f"| Collection latency (max) | {s_max:<18} | "
                f"{p_max:<18} | {max_change:+.0f}% |"
            )

        s_overhead = f"{r.serial.collection_time_pct_mean:.1f}%"
        p_overhead = f"{r.parallel.collection_time_pct_mean:.1f}%"
        overhead_change = (
            r.parallel.collection_time_pct_mean -
            r.serial.collection_time_pct_mean
        )
        overhead_str = f"{overhead_change:+.1f}%"
        lines.append(
            f"| Collection time | {s_overhead:<18} | {p_overhead:<18} | "
            f"{overhead_str:<10} |"
        )
        lines.append("")

    # Collection time benchmarks
    if result.collection_results:
        lines.append(f"## GC Collection Time ({result.heap_size:,}-object heap)")
        lines.append("")
        lines.append(
            f"Time to collect one requested {result.heap_size:,}-object heap. "
            "Lower is better."
        )
        lines.append("")

        # Aligned table - wider heap type column for ai_workload, web_server
        lines.append("| Heap Type    | Serial (ms)        | Parallel (ms)      | Speedup |")
        lines.append("|--------------|--------------------|--------------------|---------|")

        for coll in result.collection_results:
            s_time = f"{coll.serial_time_ms:.1f} ± {coll.serial_stdev:.1f}"
            p_time = f"{coll.parallel_time_ms:.1f} ± {coll.parallel_stdev:.1f}"
            speedup_str = f"{coll.speedup:.2f}x"
            lines.append(
                f"| {coll.heap_type:<12} | {s_time:<18} | {p_time:<18} | "
                f"{speedup_str:<7} |"
            )

        # Geometric mean of collection speedups
        if len(result.collection_results) > 1:
            product = 1.0
            for coll in result.collection_results:
                product *= coll.speedup
            gm_speedup = product ** (1.0 / len(result.collection_results))
            gm_str = f"{gm_speedup:.2f}x"
            lines.append(
                "| Geomean      |                    |                    | "
                f"{gm_str:<7} |"
            )
        lines.append("")

    # Synthetic throughput results
    if result.synthetic_by_heap:
        lines.append("## Synthetic Throughput (Per Heap Type)")
        lines.append("")
        lines.append("Steady-state throughput with continuous allocation.")
        lines.append("")

        # Aligned table
        lines.append(
            "| Heap Type    | Serial             | Parallel           | "
            "Throughput | Latency change |"
        )
        lines.append(
            "|--------------|--------------------|--------------------|"
            "------------|----------------|"
        )

        for heap_type, comp in result.synthetic_by_heap.items():
            s_tp = f"{comp.serial.throughput_mean:,.0f}/s"
            p_tp = f"{comp.parallel.throughput_mean:,.0f}/s"
            tp_change = f"{(comp.speedup - 1) * 100:+.1f}%"
            serial_latency = comp.serial.collection_latency_mean
            if serial_latency > 0:
                latency_change = (
                    comp.parallel.collection_latency_mean / serial_latency - 1
                ) * 100
                latency_change_text = f"{latency_change:+.0f}%"
            else:
                latency_change_text = "N/A"
            lines.append(
                f"| {heap_type:<12} | {s_tp:<18} | {p_tp:<18} | "
                f"{tp_change:<10} | {latency_change_text:<14} |"
            )

        # Geometric mean summary
        gm_speedup = f"{(result.geometric_mean_speedup - 1) * 100:+.1f}%"
        gm_latency = (
            result.geometric_mean_collection_latency_ratio - 1
        ) * 100
        lines.append(
            "| Geomean      |                    |                    | "
            f"{gm_speedup:<10} | {gm_latency:+.0f}% |"
        )
        lines.append("")

        lines.append("### Collection Latencies")
        lines.append("")
        lines.append(
            "| Heap Type    | Serial Mean (ms) | Serial Max (ms) | "
            "Parallel Mean (ms) | Parallel Max (ms) |"
        )
        lines.append(
            "|--------------|------------------|-----------------|"
            "--------------------|-------------------|"
        )

        for heap_type, comp in result.synthetic_by_heap.items():
            s_mean = _format_latency_ms(comp.serial.collection_latency_mean)
            s_max = _format_latency_ms(comp.serial.collection_latency_max)
            p_mean = _format_latency_ms(comp.parallel.collection_latency_mean)
            p_max = _format_latency_ms(comp.parallel.collection_latency_max)
            lines.append(
                f"| {heap_type:<12} | {s_mean:<16} | {s_max:<15} | "
                f"{p_mean:<18} | {p_max:<18} |"
            )

        lines.append("")

    lines.append("## Raw Samples")
    lines.append("")
    lines.append(
        "Callback latency is the full interval between the GC start and stop "
        "callbacks; it is not a stop-the-world measurement."
    )
    lines.append("")
    lines.append(
        "| Benchmark | Mode | Run | Throughput/s | Callback latency mean "
        "(ms) | Callback latency max (ms) | Collections | Duration (s) |"
    )
    lines.append(
        "|-----------|------|-----|--------------|----------------------------|"
        "---------------------------|-------------|--------------|"
    )
    comparisons = []
    if result.realistic is not None:
        comparisons.append(result.realistic)
    comparisons.extend(result.synthetic_by_heap.values())
    for comparison in comparisons:
        for benchmark_result in (comparison.serial, comparison.parallel):
            for index, run in enumerate(benchmark_result.runs, 1):
                lines.append(
                    f"| {comparison.benchmark_name} | {benchmark_result.mode} | "
                    f"{index} | {run.throughput:.6f} | "
                    f"{run.collection_latency_mean_ms:.6f} | "
                    f"{run.collection_latency_max_ms:.6f} | "
                    f"{run.collections} | {run.duration_sec:.6f} |"
                )
    for collection in result.collection_results:
        lines.append("")
        lines.append(
            f"- `{collection.heap_type}` serial collection samples (ms): "
            f"`{collection.serial_samples_ms!r}`"
        )
        lines.append(
            f"- `{collection.heap_type}` parallel collection samples (ms): "
            f"`{collection.parallel_samples_ms!r}`"
        )
        lines.append(
            f"- `{collection.heap_type}` generated object counts: "
            f"`{collection.serial_object_counts!r}`"
        )
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    if result.realistic:
        pct = (result.realistic.speedup - 1) * 100
        if pct > 0:
            lines.append(
                f"Parallel GC provides {pct:.1f}% throughput improvement "
                "on the mixed workload."
            )
        else:
            lines.append(f"Parallel GC shows {pct:.1f}% throughput change on the mixed workload.")

    if result.collection_results:
        product = 1.0
        for coll in result.collection_results:
            product *= coll.speedup
        gm_coll = product ** (1.0 / len(result.collection_results))
        lines.append(
            f"GC collection time improved by {gm_coll:.2f}x "
            "(geometric mean across heap types)."
        )

    return "\n".join(lines)


def format_json(result: SuiteResult) -> str:
    """Format results as JSON."""
    def run_to_dict(run: BenchmarkRun) -> Dict[str, Any]:
        return {
            "throughput": run.throughput,
            "collection_time_ms": run.collection_time_ms,
            "collection_time_pct": run.collection_time_pct,
            "collection_latency_mean_ms": run.collection_latency_mean_ms,
            "collection_latency_max_ms": run.collection_latency_max_ms,
            "collections": run.collections,
            "duration_sec": run.duration_sec,
        }

    def comparison_to_dict(comp: Optional[ComparisonResult]) -> Optional[Dict]:
        if comp is None:
            return None
        latency_change = 0
        if comp.serial.collection_latency_mean > 0:
            latency_change = (
                comp.parallel.collection_latency_mean /
                comp.serial.collection_latency_mean - 1
            ) * 100
        return {
            "name": comp.benchmark_name,
            "serial": {
                "throughput_mean": comp.serial.throughput_mean,
                "throughput_stdev": comp.serial.throughput_stdev,
                "collection_latency_mean_ms": comp.serial.collection_latency_mean,
                "collection_latency_stdev_ms": comp.serial.collection_latency_stdev,
                "collection_latency_max_ms": comp.serial.collection_latency_max,
                "collection_time_pct": comp.serial.collection_time_pct_mean,
                "total_duration_sec": comp.serial.total_duration,
                "total_collections": comp.serial.total_collections,
                "runs": [run_to_dict(run) for run in comp.serial.runs],
            },
            "parallel": {
                "throughput_mean": comp.parallel.throughput_mean,
                "throughput_stdev": comp.parallel.throughput_stdev,
                "collection_latency_mean_ms": comp.parallel.collection_latency_mean,
                "collection_latency_stdev_ms": comp.parallel.collection_latency_stdev,
                "collection_latency_max_ms": comp.parallel.collection_latency_max,
                "collection_time_pct": comp.parallel.collection_time_pct_mean,
                "total_duration_sec": comp.parallel.total_duration,
                "total_collections": comp.parallel.total_collections,
                "runs": [run_to_dict(run) for run in comp.parallel.runs],
            },
            "throughput_change_pct": (comp.speedup - 1) * 100,
            "collection_latency_change_pct": latency_change,
        }

    def collection_to_dict(coll: CollectionResult) -> Dict:
        return {
            "heap_type": coll.heap_type,
            "heap_size": coll.heap_size,
            "serial_time_ms": coll.serial_time_ms,
            "serial_stdev": coll.serial_stdev,
            "parallel_time_ms": coll.parallel_time_ms,
            "parallel_stdev": coll.parallel_stdev,
            "speedup": coll.speedup,
            "num_runs": coll.num_runs,
            "serial_samples_ms": coll.serial_samples_ms,
            "parallel_samples_ms": coll.parallel_samples_ms,
            "serial_object_counts": coll.serial_object_counts,
            "parallel_object_counts": coll.parallel_object_counts,
        }

    synthetic_dict = {}
    for heap_type, comp in result.synthetic_by_heap.items():
        synthetic_dict[heap_type] = comparison_to_dict(comp)

    collection_list = [collection_to_dict(c) for c in result.collection_results]

    # Geometric mean of collection speedups
    gm_collection = 1.0
    if result.collection_results:
        product = 1.0
        for coll in result.collection_results:
            product *= coll.speedup
        gm_collection = product ** (1.0 / len(result.collection_results))

    data = {
        "configuration": {
            "build_type": result.build_type,
            "parallel_gc_available": result.parallel_gc_available,
            "num_workers": result.num_workers,
            "num_threads": result.num_threads,
            "duration_per_benchmark": result.duration_per_benchmark,
            "num_runs": result.num_runs,
            "heap_size": result.heap_size,
            "random_seed": result.random_seed,
            "collection_warmup_runs": result.collection_warmup_runs,
            "collection_survivor_ratio": result.collection_survivor_ratio,
            "collection_creation_threads": result.collection_creation_threads,
            "runtime_parallel_gc_config": result.runtime_config,
        },
        "system": result.system_metadata,
        "timestamp": result.timestamp,
        "mixed_workload": comparison_to_dict(result.realistic),
        "collection_results": collection_list,
        "synthetic_by_heap": synthetic_dict,
        "summary": {
            "mixed_workload_throughput_change_pct": (
                (result.realistic.speedup - 1) * 100
                if result.realistic else 0
            ),
            "collection_speedup_geomean": gm_collection,
            "synthetic_throughput_geomean_pct": (result.geometric_mean_speedup - 1) * 100,
            "synthetic_collection_latency_geomean_pct": (
                result.geometric_mean_collection_latency_ratio - 1
            ) * 100,
        },
    }

    return json.dumps(data, indent=2)

# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Parallel GC Performance Benchmark Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s                      # Standard suite (~5 min)
    %(prog)s --quick              # Quick sanity check (~1 min)
    %(prog)s --full               # Full suite (~15 min)
    %(prog)s --json -o results.json
    %(prog)s --include-synthetic  # Also run stress tests
"""
    )

    parser.add_argument('--quick', '-q', action='store_true',
                        help='Quick sanity check (~1 min)')
    parser.add_argument('--full', '-f', action='store_true',
                        help='Full benchmark suite (~15 min)')
    parser.add_argument('--duration', '-d', type=float, default=30.0,
                        help='Duration per benchmark in seconds (default: 30)')
    parser.add_argument('--runs', '-r', type=int, default=3,
                        help='Number of runs per configuration (default: 3)')
    parser.add_argument('--threads', '-t', type=int, default=4,
                        help='Number of worker threads (default: 4)')
    parser.add_argument('--workers', '-w', type=int, default=8,
                        help='Number of parallel GC workers (default: 8)')
    parser.add_argument('--heap-size', '-s', type=int, default=500000,
                        help='Heap size for synthetic benchmarks (default: 500000)')
    parser.add_argument('--json', '-j', action='store_true',
                        help='Output as JSON instead of markdown')
    parser.add_argument('--output', '-o', type=str,
                        help='Output file (default: stdout)')
    parser.add_argument('--include-synthetic', action='store_true',
                        help='Include synthetic stress test benchmarks')

    args = parser.parse_args()

    # Adjust parameters for quick/full modes
    if args.quick:
        args.duration = 10.0
        args.runs = 2
    elif args.full:
        args.duration = 60.0
        args.runs = 5

    try:
        output_stream = sys.stderr if args.json else sys.stdout
        with contextlib.redirect_stdout(output_stream):
            result = run_suite(
                duration_per_benchmark=args.duration,
                num_runs=args.runs,
                num_threads=args.threads,
                parallel_workers=args.workers,
                heap_size=args.heap_size,
                include_synthetic=args.include_synthetic,
            )
    except (AttributeError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    # Format output
    if args.json:
        output = format_json(result)
    else:
        output = format_markdown(result)

    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"\nResults saved to: {args.output}")
    else:
        if not args.json:
            print("\n" + "=" * 60)
        print(output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
