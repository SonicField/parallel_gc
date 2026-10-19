"""Tests for execution without reinstalling benchmark dependencies.

Run in the pyperformance driver environment; original workload integration is
checked separately against the prepared GIL and FT environments.
"""

import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "prepared_runner_test", Path(__file__).with_name("run_pyperformance.py")
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class PreparedExecutionTests(unittest.TestCase):
    def suite(self, *, free_threaded=False, gil_enabled=True, hook_entries=1):
        import pyperf
        metadata = {
            "name": "probe", "loops": 1,
            "parallel_gc_mode": "disabled", "parallel_gc_enabled": False,
            "parallel_gc_available": True,
            "parallel_gc_build_gil_disabled": free_threaded,
            "parallel_gc_runtime_gil_enabled": gil_enabled,
            "parallel_gc_hook_entries": hook_entries,
        }
        return pyperf.BenchmarkSuite([pyperf.Benchmark([
            pyperf.Run(values=[1.0], metadata=metadata)
        ])])

    def test_ft_metadata_cannot_claim_gil_enabled_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "suite.json"
            self.suite(free_threaded=True).dump(str(filename))
            with self.assertRaisesRegex(runner.CampaignError, "runtime GIL"):
                runner.validate_prepared_result(filename, "disabled", True)

    def test_result_requires_an_active_hook(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "suite.json"
            self.suite(hook_entries=0).dump(str(filename))
            with self.assertRaisesRegex(runner.CampaignError, "hook"):
                runner.validate_prepared_result(filename, "disabled", False)

    def test_valid_gil_and_ft_metadata_are_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            for ft in (False, True):
                filename = Path(directory) / f"suite-{ft}.json"
                self.suite(free_threaded=ft, gil_enabled=not ft).dump(str(filename))
                self.assertEqual(runner.validate_prepared_result(filename, "disabled", ft), ("probe",))

    def test_program_failure_preserves_partial_results_and_restores_mode(self):
        suite = self.suite()
        successful = SimpleNamespace(
            name="first", tags=[], extra_opts=[], runscript="original-first.py",
            run=mock.Mock(return_value=suite),
        )
        failing = SimpleNamespace(
            name="second", run=mock.Mock(side_effect=RuntimeError("workload failed")),
        )
        environment = {"free_threaded": False, "packages": []}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "suite.json"
            with (
                mock.patch.dict(runner.os.environ, {runner.MODE_ENV: "enabled"}),
                mock.patch.object(runner, "require_prepared_target", return_value=environment),
                mock.patch.object(runner, "preflight", return_value={}),
                mock.patch.object(runner, "prepared_selection", return_value=[successful, failing]),
            ):
                with self.assertRaisesRegex(RuntimeError, "workload failed"):
                    runner.run_prepared_suite(
                        target_python="target", prepared_python="prepared",
                        mode="disabled", output=output, work_root=Path(directory),
                        benchmarks="default", manifest=None, run_style="rigorous",
                        affinity="0-31", timeout=300,
                    )
                self.assertEqual(runner.os.environ[runner.MODE_ENV], "enabled")
            self.assertFalse(output.exists())
            self.assertTrue(output.with_suffix(".programs").joinpath("001-first.json").is_file())

    def test_binary_prepared_execution_requires_both_environments(self):
        with self.assertRaises(SystemExit):
            runner.parse_args([
                "binary-abba", "--baseline-python", "baseline/python",
                "--candidate-python", "candidate/python", "--mode", "enabled",
                "--baseline-prepared-python", "baseline-env/bin/python",
                "--output-dir", "results",
            ])

    def test_binary_cli_accepts_both_prepared_environments(self):
        args = runner.parse_args([
            "binary-abba", "--baseline-python", "baseline/python",
            "--candidate-python", "candidate/python", "--mode", "enabled",
            "--baseline-prepared-python", "baseline-env/bin/python",
            "--candidate-prepared-python", "candidate-env/bin/python",
            "--output-dir", "results",
        ])
        self.assertEqual(args.baseline_prepared_python, "baseline-env/bin/python")
        self.assertEqual(args.candidate_prepared_python, "candidate-env/bin/python")

    def test_rigorous_options_match_upstream_without_parameter_overrides(self):
        from pyperformance.run import get_pyperf_opts
        options = SimpleNamespace(
            debug_single_value=False, rigorous=True, fast=False, verbose=False,
            affinity="0-31", track_memory=False,
            inherit_environ=runner.INHERITED_ENV.split(","), min_time=None,
            timeout=300, hook=[runner.HOOK_NAME], warmups=None,
        )
        actual = runner.prepared_options("rigorous", "0-31", 300)
        self.assertEqual(actual, get_pyperf_opts(options))
        self.assertNotIn("--debug-single-value", actual)
        self.assertFalse(any("loops" in item or "workers" in item for item in actual))

    def test_default_selection_retains_original_inventory_and_scripts(self):
        from pyperformance._manifest import load_manifest
        expected = sorted(load_manifest(None).resolve_group("default"))
        actual = runner.prepared_selection("default", None)
        self.assertEqual(len(actual), 100)
        self.assertEqual([item.name for item in actual], [item.name for item in expected])
        for item, original in zip(actual, expected):
            self.assertEqual(item.runscript, original.runscript)
            self.assertEqual(item.extra_opts, original.extra_opts)
            self.assertEqual(item.datadir, original.datadir)

    def test_prepared_environment_cannot_use_another_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"
            prepared = Path(directory) / "prepared"
            target.write_bytes(b"baseline")
            prepared.write_bytes(b"candidate")
            with self.assertRaisesRegex(runner.CampaignError, "different executable"):
                runner.require_prepared_target(prepared, target)

    def test_prepared_execution_does_not_enter_dependency_installer(self):
        detail = {"prepared": True}
        with (
            mock.patch.object(runner, "ensure_target_venv", side_effect=AssertionError("installer called")),
            mock.patch.object(runner, "run_prepared_suite", return_value=detail, create=True) as execute,
        ):
            actual = runner.run_suite(
                target_python="target", prepared_python="venv/bin/python",
                mode="enabled", output=Path("suite.json"), work_root=Path("work"),
                benchmarks="default", manifest=None, run_style="rigorous",
                affinity="0-31", timeout=300,
            )
        self.assertEqual(actual, detail)
        self.assertEqual(execute.call_args.kwargs["prepared_python"], "venv/bin/python")


if __name__ == "__main__":
    unittest.main()
