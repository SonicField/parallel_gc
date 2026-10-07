import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


BENCHMARK_PATH = Path(__file__).with_name("gc_adaptive_benchmark.py")
SPEC = importlib.util.spec_from_file_location(
    "gc_adaptive_benchmark_test",
    BENCHMARK_PATH,
)
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


class WorkerModeTests(unittest.TestCase):
    def test_adaptive_mode_has_no_fixed_count(self):
        self.assertIsNone(benchmark.parse_worker_mode("adaptive", 16))

    def test_fixed_mode_accepts_controller_bounds(self):
        self.assertEqual(benchmark.parse_worker_mode("2", 16), 2)
        self.assertEqual(benchmark.parse_worker_mode("16", 16), 16)

    def test_fixed_mode_rejects_out_of_range_counts(self):
        for value in ("1", "17"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    benchmark.parse_worker_mode(value, 16)


class FakeGC:
    def __init__(self, events):
        self.events = events
        self.candidates = 100
        self.attempts = 10
        self.workers = 4

    def collect(self, generation=2):
        self.events.append("collect")
        self.candidates += 20_000
        self.attempts += 1
        return 0

    def get_count(self):
        return (0, 0, 0)

    def get_stats(self):
        return [
            {"candidates": self.candidates},
            {"candidates": 0},
            {"candidates": 0},
        ]

    def get_parallel_config(self):
        return {
            "available": True,
            "enabled": True,
            "num_workers": 16,
            "adaptive_workers": self.workers,
        }

    def get_parallel_stats(self):
        return {
            "collections_attempted": self.attempts,
            "prev_cost_per_obj_ns": 7.0,
            "phase_timing": {"total_ns": 140_000},
        }


class JsonDocumentTests(unittest.TestCase):
    def test_document_records_protocol_and_observations(self):
        args = SimpleNamespace(
            seed=42,
            cycles=3,
            collections_per_phase=20,
            workers="adaptive",
        )
        fake_gc = FakeGC([])
        with mock.patch.object(benchmark, "gc", fake_gc):
            document = benchmark.make_json_document(args, [{"sample": 1}])

        self.assertEqual(document["protocol"]["seed"], 42)
        self.assertEqual(document["protocol"]["workers"], "adaptive")
        self.assertEqual(document["parallel_config"]["num_workers"], 16)
        self.assertEqual(document["observations"], [{"sample": 1}])


class PoolWarmupTests(unittest.TestCase):
    def test_warmup_requires_an_eligible_parallel_dispatch(self):
        events = []
        with mock.patch.object(benchmark, "gc", FakeGC(events)):
            benchmark.prime_parallel_pool(target_objects=1)
        self.assertEqual(events, ["collect"])

    def test_warmup_rejects_a_collection_that_did_not_dispatch(self):
        events = []
        fake_gc = FakeGC(events)

        def serial_collect(generation=2):
            events.append("collect")
            fake_gc.candidates += 20_000
            return 0

        fake_gc.collect = serial_collect
        with mock.patch.object(benchmark, "gc", fake_gc):
            with self.assertRaisesRegex(RuntimeError, "did not dispatch"):
                benchmark.prime_parallel_pool(target_objects=1)


class PhaseRunnerTests(unittest.TestCase):
    def make_phase(self, events):
        def phase(rng, target_objects):
            events.append("create")
            return object()

        return phase

    def test_fixed_count_is_applied_immediately_before_each_collection(self):
        events = []
        fake_gc = FakeGC(events)

        def set_workers(count):
            events.append(f"set:{count}")
            fake_gc.workers = count

        observations = []
        with mock.patch.object(benchmark, "gc", fake_gc):
            benchmark.run_phase(
                "test",
                self.make_phase(events),
                20_000,
                SimpleNamespace(),
                2,
                observations,
                fixed_workers=7,
                worker_setter=set_workers,
                cycle_index=3,
            )

        self.assertEqual(
            events,
            ["create", "set:7", "collect"] * 2,
        )
        self.assertEqual(
            [item["workers_used"] for item in observations],
            [7, 7],
        )
        self.assertEqual(
            [item["cycle_index"] for item in observations],
            [3, 3],
        )
        self.assertEqual(
            [item["dispatch_counter_delta"] for item in observations],
            [1, 1],
        )
        self.assertEqual(
            [item["candidates"] for item in observations],
            [20_000, 20_000],
        )

    def test_adaptive_mode_never_calls_fixed_worker_control(self):
        events = []
        observations = []
        with mock.patch.object(benchmark, "gc", FakeGC(events)):
            benchmark.run_phase(
                "test",
                self.make_phase(events),
                20_000,
                SimpleNamespace(),
                1,
                observations,
                fixed_workers=None,
                worker_setter=mock.Mock(
                    side_effect=AssertionError("unexpected fixed control")
                ),
            )

        self.assertEqual(events, ["create", "collect"])
        self.assertEqual(observations[0]["workers_used"], 4)


if __name__ == "__main__":
    unittest.main()
