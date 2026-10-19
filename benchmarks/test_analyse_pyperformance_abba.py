"""Exercise arithmetic and invalid-input rejection with real pyperf files."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import pyperf


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "analysis", Path(__file__).with_name("analyse_pyperformance_abba.py")
        )
        self.analysis = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.analysis)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def campaign(self, means=(2, 4, 6, 4)):
        labels = ("baseline", "candidate", "candidate", "baseline")
        record = {
            "schema": 2, "comparison": "baseline-candidate", "mode": "disabled",
            "order": list(labels), "benchmarks": "default", "run_style": "rigorous",
            "targets": {}, "results": {}, "runs": [],
        }
        for index, (label, mean) in enumerate(zip(labels, means), 1):
            metadata = {
                "name": "probe", "loops": 1, "unit": "second",
                "parallel_gc_mode": "disabled", "parallel_gc_enabled": False,
                "parallel_gc_available": True, "parallel_gc_build_gil_disabled": False,
                "parallel_gc_runtime_gil_enabled": True, "parallel_gc_hook_entries": 1,
            }
            suite = pyperf.BenchmarkSuite([pyperf.Benchmark([
                pyperf.Run(values=[float(mean)], metadata=metadata),
                pyperf.Run(values=[float(mean)], metadata=metadata),
            ])])
            name = f"{index:02d}-{label}.json"
            filename = self.root / name
            suite.dump(str(filename))
            digest = self.analysis.runner.sha256_file(filename)
            record["results"][name] = digest
            programs = filename.with_suffix(".programs")
            programs.mkdir()
            (programs / "001-probe.json").write_bytes(filename.read_bytes())
            record["runs"].append({
                "sequence": index, "target": label, "mode": "disabled", "result": name,
                "programs": [{"program": "probe", "result": "001-probe.json", "sha256": digest}],
            })
        self.save(record)
        return record

    def save(self, record):
        (self.root / "campaign.json").write_text(json.dumps(record))

    def analyse(self):
        return self.analysis.analyse_campaign(self.root, expected_programs=1, expected_results=1)

    def test_leg_means_not_pooled_process_counts_define_effect(self):
        self.campaign()
        row = self.analyse()["rows"][0]
        self.assertEqual(row["baseline_mean_seconds"], 3)
        self.assertEqual(row["candidate_mean_seconds"], 5)
        self.assertAlmostEqual(row["time_change_pct"], 100 * (5 / 3 - 1))
        self.assertEqual(row["half_time_changes_pct"], [100, 50])
        self.assertEqual([leg["measured_processes"] for leg in row["legs"]], [2] * 4)

    def test_opposing_halves_remain_visible(self):
        self.campaign((2, 1, 8, 4))
        row = self.analyse()["rows"][0]
        self.assertEqual(row["half_time_changes_pct"], [-50, 100])
        self.assertEqual(row["half_direction"], "differs")

    def test_missing_leg_is_not_a_comparison(self):
        self.campaign()
        (self.root / "04-baseline.json").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.analyse()

    def test_changed_bytes_invalidate_recorded_identity(self):
        self.campaign()
        with (self.root / "02-candidate.json").open("a") as output:
            output.write(" ")
        with self.assertRaisesRegex(ValueError, "digest"):
            self.analyse()

    def test_smoke_cannot_be_reported_as_rigorous(self):
        record = self.campaign()
        record["run_style"] = "debug"
        self.save(record)
        with self.assertRaisesRegex(ValueError, "rigorous"):
            self.analyse()

    def test_default_cli_scope_does_not_accept_a_small_fixture(self):
        self.campaign()
        with self.assertRaisesRegex(ValueError, "100"):
            self.analysis.analyse_campaign(self.root)

    def test_changed_named_result_is_not_pooled_with_the_original(self):
        record = self.campaign()
        filename = self.root / "03-candidate.json"
        data = json.loads(filename.read_text())
        data["metadata"]["name"] = "another-probe"
        filename.write_text(json.dumps(data))
        digest = self.analysis.runner.sha256_file(filename)
        record["results"][filename.name] = digest
        program = filename.with_suffix(".programs") / "001-probe.json"
        program.write_bytes(filename.read_bytes())
        record["runs"][2]["programs"][0]["sha256"] = digest
        self.save(record)
        with self.assertRaisesRegex(ValueError, "named results"):
            self.analyse()

    def test_original_program_evidence_must_remain_inspectable(self):
        self.campaign()
        (self.root / "02-candidate.programs" / "001-probe.json").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.analyse()


if __name__ == "__main__":
    unittest.main()
