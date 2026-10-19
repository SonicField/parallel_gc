import importlib.util
from pathlib import Path
import unittest


class PreparedReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).with_name("check_prepared_suite.py")
        spec = importlib.util.spec_from_file_location("prepared_readiness", path)
        cls.checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.checker)

    def test_selection_matches_preserved_default_inventory(self):
        root = Path(__file__).resolve().parents[2]
        inventory = root / "benchmarks/results/investigations/integration-validation-2026-10-16/full-pyperformance-preparation/selected-workloads.txt"
        expected = [line[2:] for line in inventory.read_text().splitlines() if line.startswith("- ")]
        self.assertEqual([bench.name for bench in self.checker.selected_benchmarks()], expected)
        self.assertEqual(len(expected), 100)

    def test_original_scripts_and_parameters_are_retained(self):
        from pyperformance._manifest import load_manifest
        originals = {bench.name: bench for bench in load_manifest(None).resolve_group("default")}
        for bench in self.checker.selected_benchmarks():
            original = originals[bench.name]
            self.assertEqual(bench.runscript, original.runscript)
            self.assertEqual(bench.extra_opts, original.extra_opts)
            self.assertEqual(bench.datadir, original.datadir)

    def test_readiness_options_do_not_force_gil_or_worker_count(self):
        options = self.checker.readiness_options("0-31", 300)
        self.assertIn("--debug-single-value", options)
        self.assertIn("--hook=parallel_gc", options)
        self.assertIn("--timeout=300", options)
        self.assertFalse(any("gil=0" in option or "workers" in option for option in options))


if __name__ == "__main__":
    unittest.main()
