"""Falsifiers for an external diagnostic wrapper, not collector tests."""
import copy
import sys
import unittest
from unittest.mock import patch

import run_focused_collections as driver


def valid_result():
    return {
        "heap_type": "chain", "heap_size": 500000, "num_runs": 5,
        "serial_time_ms": 10.0, "parallel_time_ms": 8.0,
        "serial_stdev": 0.0, "parallel_stdev": 0.0,
        "serial_samples_ms": [10.0] * 5,
        "parallel_samples_ms": [8.0] * 5,
        "serial_object_counts": [499712] * 5,
        "parallel_object_counts": [499712] * 5,
    }


class ResultValidationTests(unittest.TestCase):
    def test_valid_generated_counts_need_not_equal_nominal_heap_size(self):
        driver.validate_result(valid_result(), "chain")

    def test_wrong_case_or_parameters(self):
        for field, value in (("heap_type", "tree"), ("heap_size", 1000),
                             ("num_runs", 1)):
            with self.subTest(field=field):
                row = valid_result()
                row[field] = value
                with self.assertRaises(ValueError):
                    driver.validate_result(row, "chain")

    def test_missing_and_incomplete_samples(self):
        for field in ("serial_samples_ms", "parallel_samples_ms",
                      "serial_object_counts", "parallel_object_counts"):
            for value in (None, [], [1.0] * 4):
                with self.subTest(field=field, value=value):
                    row = valid_result()
                    row[field] = value
                    with self.assertRaises(ValueError):
                        driver.validate_result(row, "chain")

    def test_nonfinite_negative_and_boolean_times(self):
        for value in (float("nan"), float("inf"), -1.0, True):
            row = valid_result()
            row["parallel_samples_ms"][2] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                driver.validate_result(row, "chain")

    def test_counts_differ_between_arms(self):
        row = valid_result()
        row["parallel_object_counts"][2] += 1
        with self.assertRaises(ValueError):
            driver.validate_result(row, "chain")

    def test_invalid_counts(self):
        for value in (True, -1, 3.5):
            row = valid_result()
            row["serial_object_counts"][2] = value
            row["parallel_object_counts"][2] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                driver.validate_result(row, "chain")

    def test_mean_must_match_samples(self):
        row = valid_result()
        row["parallel_time_ms"] = 7.0
        with self.assertRaises(ValueError):
            driver.validate_result(row, "chain")


class WrapperTests(unittest.TestCase):
    def test_benchmark_is_registered_module(self):
        self.assertIs(sys.modules[driver.benchmark.__name__], driver.benchmark)

    def test_all_cases_forward_the_original_parameters(self):
        calls = []

        def capture(**kwargs):
            calls.append(copy.deepcopy(kwargs))
            row = valid_result()
            row["heap_type"] = kwargs["heap_type"]
            return driver.benchmark.CollectionResult(**row)

        with patch.object(driver.benchmark, "run_collection_benchmark", capture):
            rows = driver.run_cases(worker_ceiling=16)
        expected = [(rooting, shape) for rooting in ("frame", "module")
                    for shape in driver.HEAP_TYPES]
        self.assertEqual([(call["rooting"], call["heap_type"])
                          for call in calls], expected)
        self.assertEqual([(row["rooting"], row["heap_type"])
                          for row in rows], expected)
        for call in calls:
            self.assertEqual(call, {
                "rooting": call["rooting"], "heap_type": call["heap_type"],
                "heap_size": 500000, "num_runs": 5, "parallel_workers": 16,
                "survivor_ratio": 0.8, "creation_threads": 4, "warmup_runs": 3,
            })

    def test_unexpected_generator_set_refused_before_measurement(self):
        with patch.object(driver.benchmark, "HEAP_GENERATORS", {"chain": None}):
            with self.assertRaises(ValueError):
                driver.run_cases(worker_ceiling=16)


if __name__ == "__main__":
    unittest.main()
