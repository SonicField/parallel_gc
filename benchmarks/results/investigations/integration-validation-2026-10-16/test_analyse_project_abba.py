"""Analysis machinery tests use artificial values, never performance evidence."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import analyse_project_abba as analysis


def fixture(parallel_factor=1, serial_factor=1, revision="baseline"):
    def arm(factor):
        return {"runs": [
            {key: factor * (index + 1) for key in analysis.RUN_METRICS}
            for index in range(5)
        ]}

    def comparison():
        return {"serial": arm(serial_factor), "parallel": arm(parallel_factor)}

    collections = [{
        "heap_type": heap,
        "serial_samples_ms": [serial_factor * x for x in range(1, 6)],
        "parallel_samples_ms": [parallel_factor * x for x in range(1, 6)],
        "serial_object_counts": [123] * 5,
        "parallel_object_counts": [123] * 5,
    } for heap in analysis.COLLECTION_HEAPS]
    return {
        "configuration": dict(analysis.STANDARD_CONFIGURATION, build_type="gil"),
        "system": {
            "cpython_git": {"revision": revision, "dirty": False},
            "py_gil_disabled": 0,
            "py_parallel_gc": 1,
            "cpu_affinity": list(range(32)),
            "numa_policy": "bind node 0",
        },
        "mixed_workload": comparison(),
        "mixed_workload_module_cache": comparison(),
        "synthetic_by_heap": {h: comparison() for h in analysis.SYNTHETIC_HEAPS},
        "synthetic_by_heap_module": {h: comparison() for h in analysis.SYNTHETIC_HEAPS},
        "collection_results": collections,
        "collection_results_module": copy.deepcopy(collections),
    }


class AnalysisTests(unittest.TestCase):
    def campaign(self):
        return [fixture(), fixture(2, revision="candidate"),
                fixture(2, revision="candidate"), fixture()]

    def analyse(self, documents):
        return analysis.analyse_documents(documents, mode="gil",
                                          baseline="baseline", candidate="candidate")

    def throughput_row(self, report):
        return next(row for row in report["rows"]
                    if row["workload"] == "mixed"
                    and row["rooting"] == "frame"
                    and row["metric"] == "throughput")

    def test_null_comparison_is_zero_percent_not_a_verdict(self):
        documents = self.campaign()
        for document in documents:
            for key in ("mixed_workload", "mixed_workload_module_cache"):
                document[key]["parallel"] = copy.deepcopy(document[key]["serial"])
        row = self.throughput_row(self.analyse(documents))
        self.assertEqual(row["parallel"]["change_pct"], 0)
        self.assertNotIn("passed", row)
        self.assertNotIn("threshold", row)

    def test_signed_changes_and_both_halves(self):
        row = self.throughput_row(self.analyse(self.campaign()))
        self.assertEqual(row["parallel"]["change_pct"], 100)
        self.assertEqual(row["parallel"]["half_changes_pct"], [100, 100])
        self.assertEqual(row["serial"]["change_pct"], 0)
        self.assertEqual(row["parallel_vs_serial_pct"], [0, 100, 100, 0])

    def test_overall_weights_whole_legs_equally(self):
        documents = [fixture(), fixture(2, revision="candidate"),
                     fixture(3, revision="candidate"), fixture(2)]
        row = self.throughput_row(self.analyse(documents))
        self.assertAlmostEqual(row["parallel"]["change_pct"], 200 / 3)
        self.assertEqual(row["parallel"]["half_changes_pct"], [100, 50])

    def test_callback_means_are_not_weighted_by_collection_count(self):
        documents = self.campaign()
        runs = documents[0]["mixed_workload"]["parallel"]["runs"]
        for run, mean, count in zip(runs, [1, 9, 1, 9, 5], [1000, 1, 1000, 1, 1]):
            run["collection_latency_mean_ms"] = mean
            run["collections"] = count
        report = self.analyse(documents)
        row = next(r for r in report["rows"] if r["workload"] == "mixed"
                   and r["rooting"] == "frame"
                   and r["metric"] == "collection_latency_mean_ms")
        self.assertEqual(row["parallel"]["legs"][0]["mean"], 5)

    def test_samples_and_descriptive_variation_are_preserved(self):
        row = self.throughput_row(self.analyse(self.campaign()))
        leg = row["parallel"]["legs"][0]
        self.assertEqual(leg["samples"], [1, 2, 3, 4, 5])
        self.assertEqual((leg["n"], leg["min"], leg["max"]), (5, 1, 5))
        self.assertGreater(leg["stdev"], 0)

    def test_complete_workload_coverage(self):
        report = self.analyse(self.campaign())
        self.assertEqual(len(report["rows"]), 16 + 8 * len(analysis.RUN_METRICS))

    def test_incomplete_campaign_is_rejected(self):
        with self.assertRaises(ValueError):
            self.analyse(self.campaign()[:3])

    def test_wrong_source_order_is_rejected(self):
        documents = self.campaign()
        documents[2]["system"]["cpython_git"]["revision"] = "baseline"
        with self.assertRaises(ValueError):
            self.analyse(documents)

    def test_changed_configuration_is_rejected(self):
        documents = self.campaign()
        documents[2]["configuration"]["num_runs"] = 1
        with self.assertRaises(ValueError):
            self.analyse(documents)

    def test_changed_affinity_is_rejected(self):
        documents = self.campaign()
        documents[2]["system"]["cpu_affinity"] = [0]
        with self.assertRaises(ValueError):
            self.analyse(documents)

    def test_changed_numa_policy_is_rejected(self):
        documents = self.campaign()
        documents[2]["system"]["numa_policy"] = "unbound"
        with self.assertRaises(ValueError):
            self.analyse(documents)

    def test_ft_mode_requires_ft_configuration(self):
        documents = self.campaign()
        with self.assertRaises(ValueError):
            analysis.analyse_documents(documents, mode="ft",
                                       baseline="baseline", candidate="candidate")
        for document in documents:
            document["configuration"]["build_type"] = "free-threaded"
            document["system"]["py_gil_disabled"] = 1
        report = analysis.analyse_documents(documents, mode="ft",
                                            baseline="baseline", candidate="candidate")
        self.assertEqual(report["mode"], "ft")

    def test_ft_launcher_label_is_not_harness_build_metadata(self):
        documents = self.campaign()
        for document in documents:
            document["configuration"]["build_type"] = "ft"
            document["system"]["py_gil_disabled"] = 1
        with self.assertRaisesRegex(ValueError, "wrong build mode"):
            analysis.analyse_documents(documents, mode="ft",
                                       baseline="baseline", candidate="candidate")

    def test_dirty_source_is_rejected(self):
        documents = self.campaign()
        documents[0]["system"]["cpython_git"]["dirty"] = True
        with self.assertRaises(ValueError):
            self.analyse(documents)

    def test_missing_module_rooted_workload_is_rejected(self):
        documents = self.campaign()
        del documents[2]["synthetic_by_heap_module"]["graph"]
        with self.assertRaises(ValueError):
            self.analyse(documents)

    def test_duplicate_collection_shape_is_rejected(self):
        documents = self.campaign()
        documents[0]["collection_results"][1] = documents[0]["collection_results"][0]
        with self.assertRaises(ValueError):
            self.analyse(documents)

    def test_short_sample_is_rejected(self):
        documents = self.campaign()
        documents[2]["mixed_workload"]["serial"]["runs"].pop()
        with self.assertRaises(ValueError):
            self.analyse(documents)

    def test_nonfinite_measurement_is_rejected(self):
        documents = self.campaign()
        documents[0]["mixed_workload"]["parallel"]["runs"][0]["throughput"] = float("nan")
        with self.assertRaises(ValueError):
            self.analyse(documents)

    def test_changed_actual_object_counts_are_rejected(self):
        documents = self.campaign()
        documents[2]["collection_results"][0]["parallel_object_counts"][0] = 124
        with self.assertRaises(ValueError):
            self.analyse(documents)

    def test_actual_counts_need_not_equal_requested_heap_size(self):
        row = next(r for r in self.analyse(self.campaign())["rows"]
                   if r["kind"] == "controlled_collection")
        self.assertEqual(row["object_counts"], [123] * 5)

    def test_zero_denominator_is_undefined_not_zero_change(self):
        documents = self.campaign()
        for document in documents:
            for run in document["mixed_workload"]["parallel"]["runs"]:
                run["collection_latency_mean_ms"] = 0
        row = next(r for r in self.analyse(documents)["rows"]
                   if r["workload"] == "mixed" and r["rooting"] == "frame"
                   and r["metric"] == "collection_latency_mean_ms")
        self.assertIsNone(row["parallel"]["change_pct"])

    def test_missing_metric_is_rejected(self):
        documents = self.campaign()
        del documents[2]["mixed_workload"]["parallel"]["runs"][0]["throughput"]
        with self.assertRaises(ValueError):
            self.analyse(documents)

    def test_cli_preserves_input_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, (label, document) in enumerate(
                    zip(analysis.LABELS, self.campaign()), 1):
                path = Path(directory) / f"gil-{index}-{label}.json"
                path.write_text(json.dumps(document))
            result = subprocess.run(
                [sys.executable, analysis.__file__, directory, "--mode", "gil",
                 "--baseline", "baseline", "--candidate", "candidate"],
                capture_output=True, text=True, check=True,
            )
            report = json.loads(result.stdout)
            self.assertEqual(len(report["inputs"]), 4)
            self.assertTrue(all(len(i["sha256"]) == 64 for i in report["inputs"]))

    def test_cli_refuses_missing_files_without_partial_report(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, analysis.__file__, directory, "--mode", "gil"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("Analysis refused", result.stderr)


if __name__ == "__main__":
    unittest.main()
