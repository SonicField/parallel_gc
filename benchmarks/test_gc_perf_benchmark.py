import random
import threading
import unittest
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
