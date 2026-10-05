import gc
import importlib.util
from pathlib import Path
import unittest


BENCHMARK = (
    Path(__file__).with_name("bm_parallel_gc_container_traversal")
    / "run_benchmark.py"
)
SPEC = importlib.util.spec_from_file_location(
    "parallel_gc_container_traversal_benchmark", BENCHMARK
)
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


class ContainerGraphTests(unittest.TestCase):
    def assert_graph(self, graph, *, kind, containers, auxiliaries, edges):
        self.assertEqual(graph.kind, kind)
        self.assertEqual(graph.container_nodes, containers)
        self.assertEqual(graph.auxiliary_nodes, auxiliaries)
        self.assertEqual(graph.edges, edges)
        benchmark.validate_graph(graph)

    def test_list_graph_shape_and_repeated_edges(self):
        graph = benchmark.build_list_graph(6)
        self.assert_graph(
            graph,
            kind="list",
            containers=6,
            auxiliaries=0,
            edges=sum(range(6)),
        )
        current = graph.root
        for width in reversed(range(1, 6)):
            self.assertEqual(len(current), width)
            self.assertTrue(all(item is current[0] for item in current))
            current = current[0]
        self.assertEqual(current, [])

    def test_tuple_graph_stays_tracked(self):
        graph = benchmark.build_tuple_graph(6)
        self.assert_graph(
            graph,
            kind="tuple",
            containers=6,
            auxiliaries=1,
            edges=sum(width + 1 for width in range(6)),
        )
        gc.collect()
        benchmark.validate_graph(graph)

    def test_unicode_dict_graph_has_only_exact_string_keys(self):
        graph = benchmark.build_unicode_dict_graph(6)
        self.assert_graph(
            graph,
            kind="dict-unicode",
            containers=6,
            auxiliaries=1,
            edges=sum(width + 1 for width in range(6)),
        )
        current = graph.root
        for width in reversed(range(6)):
            self.assertTrue(all(type(key) is str for key in current))
            self.assertEqual(len(current), width + 1)
            if width:
                child = current["value-0"]
                self.assertTrue(
                    all(
                        value is child
                        for key, value in current.items()
                        if key != "anchor"
                    )
                )
                current = child

    def test_general_dict_visits_tracked_keys_and_values(self):
        graph = benchmark.build_general_dict_graph(6)
        self.assert_graph(
            graph,
            kind="dict-general",
            containers=6,
            auxiliaries=1 + sum(range(6)),
            edges=sum(2 * (width + 1) for width in range(6)),
        )
        current = graph.root
        keys = [key for key in current if type(key) is benchmark.TrackedKey]
        self.assertTrue(keys)
        self.assertTrue(all(gc.is_tracked(key) for key in keys))

    def test_split_dict_graph_uses_fixed_shared_keys(self):
        graph = benchmark.build_split_dict_graph(6, width=4)
        self.assert_graph(
            graph,
            kind="dict-split",
            containers=6,
            auxiliaries=1,
            edges=24,
        )
        current = graph.root
        for _ in range(6):
            self.assertEqual(tuple(current), tuple(f"value_{i}" for i in range(4)))
            child = current["value_0"]
            self.assertTrue(all(value is child for value in current.values()))
            current = child

    def test_unknown_graph_kind_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown container"):
            benchmark.build_graph("set")

    def test_collection_reports_no_garbage(self):
        graph = benchmark.build_list_graph(20)
        gc.collect()
        self.assertGreater(benchmark.benchmark_collection(3, graph), 0.0)


if __name__ == "__main__":
    unittest.main()
