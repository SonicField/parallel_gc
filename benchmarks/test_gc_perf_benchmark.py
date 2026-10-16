import gc
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


if __name__ == "__main__":
    unittest.main()
