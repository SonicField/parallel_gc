import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


SUPPORT = Path(__file__).with_name("pyperformance_support")
sys.path.insert(0, str(SUPPORT))
MODE_PATH = SUPPORT / "parallel_gc_pyperformance" / "mode.py"
SPEC = importlib.util.spec_from_file_location("parallel_gc_mode_test", MODE_PATH)
mode = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mode)

RUNNER_PATH = Path(__file__).with_name("run_pyperformance.py")
RUNNER_SPEC = importlib.util.spec_from_file_location(
    "parallel_gc_pyperformance_runner_test", RUNNER_PATH
)
runner = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(runner)

from parallel_gc_pyperformance import hook as support_hook


class FakeGC:
    def __init__(self, *, available, enabled=False):
        self.available = available
        self.enabled = enabled
        self.enable_calls = 0
        self.disable_calls = 0

    def enable_parallel(self):
        self.enable_calls += 1
        if not self.available:
            raise RuntimeError("not available")
        self.enabled = True

    def disable_parallel(self):
        self.disable_calls += 1
        if not self.available:
            raise RuntimeError("not available")
        self.enabled = False

    def get_parallel_config(self):
        return {
            "available": self.available,
            "enabled": self.enabled,
            "num_workers": 16 if self.enabled else 0,
            **({"adaptive_workers": 4} if self.enabled else {}),
        }


class ApplyModeTests(unittest.TestCase):
    def test_enabled_mode_enables_and_verifies(self):
        fake = FakeGC(available=True)
        config = mode.apply_mode("enabled", fake)
        self.assertEqual(fake.enable_calls, 1)
        self.assertTrue(config["enabled"])
        self.assertEqual(config["adaptive_workers"], 4)

    def test_disabled_mode_disables_and_verifies(self):
        fake = FakeGC(available=True, enabled=True)
        config = mode.apply_mode("disabled", fake)
        self.assertEqual(fake.disable_calls, 1)
        self.assertFalse(config["enabled"])

    def test_feature_off_rejects_available_collector(self):
        fake = FakeGC(available=True)
        with self.assertRaisesRegex(RuntimeError, "feature-off"):
            mode.apply_mode("feature-off", fake)

    def test_feature_off_accepts_missing_api(self):
        config = mode.apply_mode("feature-off", object())
        self.assertEqual(
            config,
            {"available": False, "enabled": False, "num_workers": 0},
        )

    def test_enabled_mode_rejects_false_postcondition(self):
        fake = FakeGC(available=True)
        fake.enable_parallel = mock.Mock()
        with self.assertRaisesRegex(RuntimeError, "not available and enabled"):
            mode.apply_mode("enabled", fake)

    def test_unknown_mode_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "unknown"):
            mode.apply_mode("sixteen", FakeGC(available=True))


class ProcessBoundaryTests(unittest.TestCase):
    def benchmark_environment(self):
        environ = os.environ.copy()
        environ.update({
            mode.MODE_ENV: "enabled",
            mode.RUN_ID_ENV: "test-run",
            "PYTHONPATH": str(SUPPORT),
        })
        environ.pop(mode.VERIFIED_PID_ENV, None)
        return environ

    def test_arbitrary_worker_argument_does_not_activate_gc(self):
        code = (
            "import os; "
            f"print(os.environ.get({mode.VERIFIED_PID_ENV!r}))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code, "--worker"],
            env=self.benchmark_environment(),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "None")

    def test_forkserver_does_not_activate_from_inherited_environment(self):
        probe = """
import gc
import multiprocessing
import os

VERIFIED_PID_ENV = "PARALLEL_GC_PYPERFORMANCE_VERIFIED_PID"

def report(connection):
    get_config = getattr(gc, "get_parallel_config", None)
    config = get_config() if get_config is not None else {}
    connection.send({
        "enabled": config.get("enabled", False),
        "verified_pid": os.environ.get(VERIFIED_PID_ENV),
    })
    connection.close()

if __name__ == "__main__":
    get_config = getattr(gc, "get_parallel_config", None)
    config = get_config() if get_config is not None else {}
    context = multiprocessing.get_context("forkserver")
    parent, child = context.Pipe(False)
    process = context.Process(target=report, args=(child,))
    process.start()
    child.close()
    result = parent.recv()
    process.join()
    if process.exitcode != 0:
        raise SystemExit(process.exitcode)
    if config.get("enabled", False):
        raise SystemExit("parent collector was activated")
    if result["enabled"] or result["verified_pid"] is not None:
        raise SystemExit(f"forkserver child was activated: {result!r}")
"""
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "forkserver_probe.py"
            filename.write_text(probe)
            result = subprocess.run(
                [sys.executable, filename, "--worker"],
                env=self.benchmark_environment(),
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stderr)


class HookScopeTests(unittest.TestCase):
    def test_command_timer_hook_is_passive(self):
        environ = {mode.MODE_ENV: "enabled"}
        with mock.patch.dict(os.environ, environ, clear=True):
            with mock.patch.object(sys, "argv", ["/tmp/_process_time.py"]):
                with mock.patch.object(
                    support_hook, "apply_mode", create=True
                ) as apply:
                    hook = support_hook.ParallelGCHook()
                    metadata = {}
                    with hook:
                        pass
                    hook.teardown(metadata)
        self.assertFalse(hook.active)
        self.assertEqual(metadata, {})
        apply.assert_not_called()

    def test_benchmark_hook_applies_mode_and_records_pid(self):
        config = {"available": True, "enabled": True, "num_workers": 16}
        environ = {mode.MODE_ENV: "enabled"}
        with mock.patch.dict(os.environ, environ, clear=True):
            with mock.patch.object(sys, "argv", ["benchmark.py"]):
                with mock.patch.object(
                    support_hook,
                    "apply_mode",
                    return_value=config,
                    create=True,
                ) as apply:
                    with mock.patch.object(
                        support_hook, "verify_mode", return_value=config
                    ):
                        hook = support_hook.ParallelGCHook()
                        metadata = {}
                        with hook:
                            pass
                        hook.teardown(metadata)
                    apply.assert_called_once_with("enabled")
                    self.assertEqual(
                        os.environ[mode.VERIFIED_PID_ENV], str(os.getpid())
                    )
                    self.assertTrue(hook.active)
                    self.assertTrue(metadata["parallel_gc_enabled"])

    def test_stale_pid_attestation_is_replaced(self):
        config = {"available": True, "enabled": False, "num_workers": 0}
        environ = {
            mode.MODE_ENV: "disabled",
            mode.VERIFIED_PID_ENV: "1",
        }
        with mock.patch.dict(os.environ, environ, clear=True):
            with mock.patch.object(sys, "argv", ["benchmark.py"]):
                with mock.patch.object(
                    support_hook,
                    "apply_mode",
                    return_value=config,
                    create=True,
                ):
                    with mock.patch.object(
                        support_hook, "verify_mode", return_value=config
                    ):
                        support_hook.ParallelGCHook()
            self.assertEqual(
                os.environ[mode.VERIFIED_PID_ENV], str(os.getpid())
            )


class RunnerTests(unittest.TestCase):
    def test_abba_order(self):
        self.assertEqual(
            runner.ABBA_MODES,
            ("disabled", "enabled", "enabled", "disabled"),
        )

    def test_binary_abba_order(self):
        self.assertEqual(
            runner.BINARY_ABBA_LABELS,
            ("baseline", "candidate", "candidate", "baseline"),
        )

    def test_run_style_mapping(self):
        self.assertEqual(runner.RUN_STYLE_ARGS["fast"], "--fast")
        self.assertEqual(runner.RUN_STYLE_ARGS["rigorous"], "--rigorous")
        self.assertEqual(runner.RUN_STYLE_ARGS["debug"], "--debug-single-value")

    def test_worker_environment_includes_mode_and_run_id(self):
        self.assertEqual(
            set(runner.INHERITED_ENV.split(",")),
            {runner.MODE_ENV, runner.RUN_ID_ENV},
        )

    def test_command_record_converts_paths_for_json(self):
        command = runner.command_record(["python", Path("result.json")])
        self.assertEqual(command, ["python", "result.json"])

    def test_exclusion_only_benchmarks_stay_attached_to_option(self):
        self.assertEqual(
            runner.benchmarks_arg("-broken_one,-broken_two"),
            "--benchmarks=-broken_one,-broken_two",
        )

    def test_manifest_argument_is_absolute(self):
        argument = runner.manifest_arg(Path("benchmarks/MANIFEST"))
        self.assertEqual(
            argument,
            f"--manifest={Path('benchmarks/MANIFEST').resolve()}",
        )

    def test_matching_benchmarks_accepts_identical_order(self):
        runner.require_matching_benchmarks(
            ("one", "two"), ("one", "two"), Path("result.json")
        )

    def test_matching_benchmarks_rejects_different_results(self):
        with self.assertRaisesRegex(
            runner.CampaignError, "missing=\\['two'\\], extra=\\['three'\\]"
        ):
            runner.require_matching_benchmarks(
                ("one", "two"), ("one", "three"), Path("result.json")
            )

    def test_matching_work_rejects_different_graphs(self):
        with self.assertRaisesRegex(runner.CampaignError, "work differs"):
            runner.require_matching_work(
                (("list", 1000, 499500),),
                (("list", 1000, 499499),),
                Path("result.json"),
            )

    def test_binary_comparison_rejects_identical_executables(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline"
            candidate = Path(directory) / "candidate"
            baseline.write_bytes(b"same")
            candidate.write_bytes(b"same")
            with self.assertRaisesRegex(
                runner.CampaignError, "identical executable"
            ):
                runner.require_distinct_targets(baseline, candidate)

    def test_binary_comparison_accepts_distinct_executables(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = Path(directory) / "baseline"
            candidate = Path(directory) / "candidate"
            baseline.write_bytes(b"before")
            candidate.write_bytes(b"after")
            record = runner.require_distinct_targets(baseline, candidate)
        self.assertNotEqual(record["baseline"], record["candidate"])

    def test_parse_venv_path(self):
        output = (
            "Virtual environment path: /tmp/work/venv/cpython3.16 "
            "(already created)\n"
        )
        self.assertEqual(
            runner.parse_venv_path(output),
            Path("/tmp/work/venv/cpython3.16"),
        )

    def test_parse_venv_path_requires_marker(self):
        with self.assertRaisesRegex(runner.CampaignError, "did not report"):
            runner.parse_venv_path("no virtual environment here")

    def test_preflight_applies_mode_explicitly_without_worker_argument(self):
        completed = SimpleNamespace(stdout=(
            '{"available": true, "enabled": true, "num_workers": 16}\n'
        ))
        with mock.patch.object(
            runner, "run_command", return_value=completed
        ) as run:
            config = runner.preflight(
                Path("venv-python"), "enabled", Path("work")
            )
        command = run.call_args.args[0]
        self.assertEqual(command[:2], [Path("venv-python"), "-c"])
        self.assertIn("apply_mode", command[2])
        self.assertNotIn("--worker", command)
        self.assertTrue(config["enabled"])


if __name__ == "__main__":
    unittest.main()
