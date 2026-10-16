import gc
import json
import pathlib
import sys
import random
import threading
import unittest
import weakref
from unittest import mock

from benchmarks import gc_perf_benchmark as benchmark


class GeneratorTests(unittest.TestCase):
    @staticmethod
    def graph_signature(clusters):
        positions = {
            id(node): (cluster_index, node_index)
            for cluster_index, cluster in enumerate(clusters)
            for node_index, node in enumerate(cluster)
        }
        return tuple(
            tuple(
                tuple(positions[id(referent)] for referent in node.refs)
                for node in cluster
            )
            for cluster in clusters
        )

    def test_graph_uses_supplied_random_stream(self):
        first = benchmark.create_graph(200, rng=random.Random(17))
        second = benchmark.create_graph(200, rng=random.Random(17))
        other = benchmark.create_graph(200, rng=random.Random(18))

        self.assertEqual(
            self.graph_signature(first), self.graph_signature(second))
        self.assertNotEqual(
            self.graph_signature(first), self.graph_signature(other))


class ThreadFailureTests(unittest.TestCase):
    def test_join_timeout_fails_closed(self):
        release = threading.Event()
        thread = threading.Thread(target=release.wait)
        thread.start()
        try:
            with self.assertRaisesRegex(RuntimeError, "did not stop"):
                benchmark._join_threads_or_raise([thread], timeout=0.01)
        finally:
            release.set()
            thread.join()

    def test_mixed_worker_exception_is_propagated(self):
        def fail():
            raise ValueError("mixed worker failed")

        with (
            mock.patch.object(benchmark, "REALISTIC_WORKLOADS", {"fail": fail}),
            mock.patch.object(benchmark, "disable_parallel_gc"),
        ):
            with self.assertRaisesRegex(ValueError, "mixed worker failed"):
                benchmark.run_realistic_benchmark(1.0, 1)

    def test_synthetic_worker_exception_is_propagated(self):
        def fail(size, *, rng=None):
            raise ValueError("synthetic worker failed")

        with (
            mock.patch.dict(benchmark.HEAP_GENERATORS, {"fail": fail}),
            mock.patch.object(benchmark, "disable_parallel_gc"),
        ):
            with self.assertRaisesRegex(ValueError, "synthetic worker failed"):
                benchmark.run_synthetic_benchmark(1.0, 100, "fail", 1)


class CreationPoolTests(unittest.TestCase):
    def assert_pool_results_released(self, schedule, keep_count=0):
        release = threading.Event()
        barrier = threading.Barrier(4, timeout=5)
        original_worker = benchmark.CreationThreadPool._worker
        original_generator = benchmark.HEAP_GENERATORS["graph"]

        def scheduled_worker(pool, thread_id):
            if schedule == "one_worker" and thread_id != 0:
                release.wait()
            original_worker(pool, thread_id)

        def scheduled_generator(size, *, rng=None):
            if schedule == "all_workers":
                # Each worker must claim a task before any can finish one.
                barrier.wait()
            return original_generator(size, rng=rng)

        with (
            mock.patch.object(
                benchmark.CreationThreadPool, "_worker", scheduled_worker),
            mock.patch.dict(
                benchmark.HEAP_GENERATORS, {"graph": scheduled_generator}),
        ):
            pool = benchmark.CreationThreadPool(4)
            try:
                clusters = pool.create_objects("graph", 4000)
                probes = [weakref.ref(cluster[0]) for cluster in clusters]
                self.assertEqual(len(probes), 40)
                kept = clusters[:keep_count]
                clusters = None
                gc.collect()
                alive = sum(probe() is not None for probe in probes)
                self.assertEqual(
                    alive, keep_count,
                    f"{alive}/{len(probes)} clusters remain alive, expected "
                    f"the {keep_count} caller-retained clusters only "
                    f"under {schedule}; idle creation workers must release "
                    "their results before reporting task completion")
                self.assertEqual(
                    [probe() is not None for probe in probes],
                    [True] * keep_count + [False] * (40 - keep_count))
                self.assertEqual(len(kept), keep_count)
                self.assertTrue(all(thread.is_alive() for thread in pool.threads))
            finally:
                release.set()
                pool.shutdown()

    def test_pool_threads_do_not_retain_results(self):
        self.assert_pool_results_released("natural")

    def test_one_worker_does_not_retain_its_last_result(self):
        self.assert_pool_results_released("one_worker")

    def test_each_worker_releases_its_result(self):
        self.assert_pool_results_released("all_workers")

    def test_only_caller_retained_clusters_survive(self):
        self.assert_pool_results_released("all_workers", keep_count=32)

    def test_results_use_task_order_and_fixed_seeds(self):
        def probe(size, *, rng=None):
            return [[rng.randrange(1_000_000)]]

        pool = benchmark.CreationThreadPool(4)
        try:
            with mock.patch.dict(
                benchmark.HEAP_GENERATORS, {"probe": probe}
            ):
                result = pool.create_objects("probe", 4)
        finally:
            pool.shutdown()

        expected = [
            [random.Random(benchmark.BENCHMARK_SEED + index).randrange(1_000_000)]
            for index in range(4)
        ]
        self.assertEqual(result, expected)

    def test_generator_exception_is_propagated(self):
        def fail(size, *, rng=None):
            raise ValueError("creation failed")

        pool = benchmark.CreationThreadPool(2)
        try:
            with mock.patch.dict(
                benchmark.HEAP_GENERATORS, {"fail": fail}
            ):
                with self.assertRaisesRegex(ValueError, "creation failed"):
                    pool.create_objects("fail", 2)
        finally:
            pool.shutdown()


# random.shuffle's own frame references the list it shuffles; the module
# variants document that brief exposure, so it is not counted as a frame root.
_SHUFFLE_CODE = random.Random.shuffle.__code__


def _nested_codes(code):
    """A code object and every code object nested in it (genexprs etc.)."""
    codes = {code}
    for const in code.co_consts:
        if isinstance(const, type(code)):
            codes |= _nested_codes(const)
    return codes


def _frame_hits(targets, skip_codes=()):
    """Find holder references on the calling thread's stack.

    `targets` is a list of the objects themselves, so they stay alive (and
    their ids cannot be reused by new objects) while other threads run.

    Other executing threads' f_locals are unsafe to read in FT Python; see
    CPython's Doc/howto/free-threading-python.rst, "Frame objects". Each
    sustained worker probes its own stack. Collection tests combine this
    calling-stack check with the separate creation-pool ownership tests.
    """
    target_ids = {id(target) for target in targets}
    hits = []
    # Exclude the probe helpers, which deliberately hold the targets.
    skip = (set(skip_codes) | {_SHUFFLE_CODE, _holder_objects.__code__}
            | _nested_codes(_frame_hits.__code__))
    thread_id = threading.get_ident()
    frame = sys._getframe(1)
    while frame is not None:
        if frame.f_code not in skip:
            for name, value in frame.f_locals.items():
                if id(value) in target_ids or (
                        isinstance(value, (list, tuple))
                        and any(id(item) in target_ids for item in value)):
                    hits.append((thread_id, frame.f_code.co_name, name))
        frame = frame.f_back
    return hits


def _holder_objects(holder):
    """A heap holder (a list of clusters) and each of its clusters."""
    return [holder, *holder]


def _no_parallel_control():
    """Patch out parallel-GC switching so the tests are build-agnostic."""
    return (
        mock.patch.object(benchmark, "enable_parallel_gc", lambda: {}),
        mock.patch.object(benchmark, "disable_parallel_gc", lambda: None),
    )


class FrameProbeTests(unittest.TestCase):
    def test_probe_reads_only_its_calling_stack(self):
        holder = [object()]
        with mock.patch.object(
                sys, "_current_frames",
                side_effect=AssertionError("unsafe cross-thread probe")):
            hits = _frame_hits([holder])
        self.assertIn(
            (threading.get_ident(),
             "test_probe_reads_only_its_calling_stack", "holder"), hits)


class ModuleRootedCollectionTests(unittest.TestCase):
    """No collecting-stack keep-set alias at the module-only boundary.

    CreationPoolTests independently checks that idle helpers release results.
    """

    def _run(self, rooting):
        real_collect = gc.collect
        observations = []

        def probe(*args, **kwargs):
            holder = benchmark._MODULE_ROOT.get("collection")
            if rooting == "module" and holder is not None:
                ids = _holder_objects(holder)
            else:
                ids = []
                # Frame variant (positive control): find keep_refs by scanning.
                frame = sys._getframe(1)
                while frame is not None:
                    keep = frame.f_locals.get("keep_refs")
                    if isinstance(keep, list) and keep:
                        ids = _holder_objects(keep)
                        break
                    frame = frame.f_back
                keep = frame = None
            holder = None
            if ids:
                observations.append(_frame_hits(ids, _nested_codes(probe.__code__)))
            return real_collect(*args, **kwargs)

        enable, disable = _no_parallel_control()
        with enable, disable, mock.patch.object(benchmark.gc, "collect", probe):
            result = benchmark.run_collection_benchmark(
                heap_size=2000, heap_type="graph", num_runs=2,
                warmup_runs=1, rooting=rooting)
        return result, observations

    def test_module_rooted_keep_set_has_no_frame_references(self):
        result, observations = self._run("module")
        self.assertTrue(observations, "probe never saw the module holder")
        self.assertEqual([hit for obs in observations for hit in obs], [])
        self.assertNotIn("collection", benchmark._MODULE_ROOT,
                         "module holder not cleared after the benchmark")

    def test_frame_rooted_keep_set_is_detected_by_probe(self):
        # Positive control: the probe must find the frame reference that the
        # existing benchmark deliberately holds.
        result, observations = self._run("frame")
        self.assertTrue(any(observations),
                        "probe failed to detect the frame-rooted keep set")

    def test_rooting_variants_build_identical_heaps(self):
        frame_result, _ = self._run("frame")
        module_result, _ = self._run("module")
        self.assertEqual(frame_result.serial_object_counts,
                         module_result.serial_object_counts)
        self.assertEqual(frame_result.parallel_object_counts,
                         module_result.parallel_object_counts)

    def test_unknown_rooting_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "rooting"):
            benchmark.run_collection_benchmark(
                heap_size=200, heap_type="graph", num_runs=1,
                warmup_runs=0, rooting="stack")


class ModuleRootedSyntheticTests(unittest.TestCase):
    """Module state owns sustained heaps; temporary churn batches are allowed.

    Probe at allocation boundaries for a persistent whole-heap frame local.
    This is not an assertion that mutating heaps never have stack references.
    """

    def _run(self, rooting):
        observations = []
        calls = threading.local()

        def probe_graph(size, *, rng=None):
            calls.count = getattr(calls, "count", 0) + 1
            if calls.count > 1:   # churn step: a long-lived heap exists
                ids = []
                slots = benchmark._MODULE_ROOT.get("synthetic")
                if rooting == "module" and slots is not None:
                    for heap in slots:
                        if heap is not None:
                            ids.append(heap)
                else:
                    frame = sys._getframe(1)
                    while frame is not None:
                        heap = frame.f_locals.get("local_heap")
                        if isinstance(heap, list):
                            ids = [heap]
                            break
                        frame = frame.f_back
                    frame = None
                slots = heap = None
                if ids:
                    observations.append(
                        _frame_hits(ids, _nested_codes(probe_graph.__code__)))
            return benchmark.create_graph(size, rng=rng)

        enable, disable = _no_parallel_control()
        with enable, disable, mock.patch.dict(
                benchmark.HEAP_GENERATORS, {"probe": probe_graph}):
            benchmark.run_synthetic_benchmark(
                0.5, 4000, "probe", 2, rooting=rooting)
        return observations

    def test_module_rooted_heaps_have_no_persistent_holder_local(self):
        observations = self._run("module")
        self.assertTrue(observations, "probe never ran during churn")
        self.assertEqual([hit for obs in observations for hit in obs], [])
        self.assertNotIn("synthetic", benchmark._MODULE_ROOT,
                         "module holder not cleared after the benchmark")

    def test_frame_rooted_heaps_are_detected_by_probe(self):
        observations = self._run("frame")
        self.assertTrue(any(observations),
                        "probe failed to detect frame-rooted local_heap")

    def test_module_variant_propagates_worker_exception(self):
        def fail(size, *, rng=None):
            raise ValueError("module synthetic worker failed")

        enable, disable = _no_parallel_control()
        with enable, disable, mock.patch.dict(
                benchmark.HEAP_GENERATORS, {"fail": fail}):
            with self.assertRaisesRegex(ValueError, "module synthetic"):
                benchmark.run_synthetic_benchmark(
                    1.0, 100, "fail", 1, rooting="module")
        self.assertNotIn("synthetic", benchmark._MODULE_ROOT)


class ModuleCacheTests(unittest.TestCase):
    """The mixed workload's long-lived cache lives only in the module holder
    during the timed region and is removed afterwards."""

    def test_cache_is_module_rooted_during_timed_region(self):
        size = 1000
        expected = sum(
            len(cluster) for cluster in benchmark.create_ai_workload(
                size, rng=random.Random(benchmark.BENCHMARK_SEED)))
        observations = []

        def probe():
            cache = benchmark._MODULE_ROOT.get("cache")
            if cache is not None:
                count = sum(len(cluster) for cluster in cache)
                hits = _frame_hits(_holder_objects(cache), _nested_codes(probe.__code__))
                cache = None
                observations.append((count, hits))

        enable, disable = _no_parallel_control()
        with enable, disable, mock.patch.object(
                benchmark, "REALISTIC_WORKLOADS", {"probe": probe}):
            benchmark.run_realistic_benchmark(
                0.3, 1, module_cache_size=size)
        self.assertTrue(observations, "probe never saw the cache")
        self.assertEqual({count for count, _ in observations}, {expected})
        self.assertEqual([hit for _, hits in observations for hit in hits], [])
        self.assertNotIn("cache", benchmark._MODULE_ROOT)

    def test_default_has_no_cache(self):
        seen = []
        enable, disable = _no_parallel_control()
        with enable, disable, mock.patch.object(
                benchmark, "REALISTIC_WORKLOADS", {
                    "probe": lambda: seen.append(
                        "cache" in benchmark._MODULE_ROOT)}):
            benchmark.run_realistic_benchmark(0.2, 1)
        self.assertTrue(seen)
        self.assertFalse(any(seen))

    def test_activation_failure_does_not_leave_a_cache(self):
        try:
            with mock.patch.object(
                    benchmark, "enable_parallel_gc",
                    side_effect=RuntimeError("activation failed")):
                with self.assertRaisesRegex(RuntimeError, "activation failed"):
                    benchmark.run_realistic_benchmark(
                        0.2, 1, parallel_workers=1, module_cache_size=1000)
            self.assertFalse("cache" in benchmark._MODULE_ROOT,
                             "failed activation retained the cache")
        finally:
            benchmark._MODULE_ROOT.pop("cache", None)
            gc.enable()


def _key_tree(obj):
    if isinstance(obj, dict):
        return {key: _key_tree(value) for key, value in sorted(obj.items())}
    if isinstance(obj, list):
        return [_key_tree(obj[0])] if obj else []
    return type(obj).__name__


class JsonCompatibilityTests(unittest.TestCase):
    """Existing JSON keys and value types are unchanged; module-rooted results
    appear under their own keys."""

    def _suite(self):
        run = benchmark.BenchmarkRun(1.0, 1.0, 1.0, 1.0, 1.0, 1, 1.0, 4, 4)

        def comp(name):
            return benchmark.ComparisonResult(
                name,
                benchmark.BenchmarkResult(name, name, "serial", [run]),
                benchmark.BenchmarkResult(
                    name, name, "parallel-adaptive", [run]))

        def coll():
            return benchmark.CollectionResult(
                "graph", 100, 1.0, 1.0,
                serial_samples_ms=[1.0], parallel_samples_ms=[1.0],
                serial_object_counts=[100], parallel_object_counts=[100])

        result = benchmark.SuiteResult(
            build_type="ftp", parallel_gc_available=True,
            worker_ceiling=16, timestamp="t")
        result.realistic = comp("mixed_workload")
        result.synthetic_by_heap["graph"] = comp("synthetic_graph")
        result.collection_results.append(coll())
        result.realistic_module_cache = comp("mixed_workload_module_cache")
        result.synthetic_by_heap_module["graph"] = comp("synthetic_graph")
        result.collection_results_module.append(coll())
        return result

    def test_existing_keys_and_types_unchanged(self):
        data = json.loads(benchmark.format_json(self._suite()))
        data["system"] = "dict"
        data["configuration"]["runtime_parallel_gc_config"] = "dict"
        fixture_path = (pathlib.Path(__file__).parent / "test_data"
                        / "gc_perf_json_keys_724b74b.json")
        expected = json.loads(fixture_path.read_text())
        actual = _key_tree(data)
        for key, structure in expected.items():
            if key == "configuration":
                for name, kind in structure.items():
                    self.assertEqual(actual[key].get(name), kind, name)
            else:
                self.assertEqual(actual.get(key), structure, key)

    def test_module_rooted_results_have_own_keys(self):
        result = self._suite()
        data = json.loads(benchmark.format_json(result))
        self.assertEqual(
            data["mixed_workload_module_cache"]["name"],
            "mixed_workload_module_cache")
        self.assertIn("graph", data["synthetic_by_heap_module"])
        self.assertEqual(
            data["collection_results_module"][0]["heap_type"], "graph")
        self.assertEqual(data["configuration"]["module_cache_size"],
                         result.module_cache_size)


if __name__ == "__main__":
    unittest.main()
