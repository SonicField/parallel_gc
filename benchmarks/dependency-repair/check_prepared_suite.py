"""Run original default workloads in an explicitly prepared environment.

Readiness only: one diagnostic value, not a performance comparison. Dependency
installation is deliberately separate because upstream's installer restores
the original incompatible pins. Workload execution uses upstream Benchmark.run.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import traceback

import pyperf
import pyperformance
from pyperformance._manifest import load_manifest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("parallel_gc_runner", ROOT / "benchmarks/run_pyperformance.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def selected_benchmarks():
    return sorted(load_manifest(None).resolve_group("default"))


def readiness_options(affinity, timeout):
    return [
        "--debug-single-value",
        f"--affinity={affinity}",
        f"--timeout={timeout}",
        f"--inherit-environ={runner.INHERITED_ENV}",
        "--hook=parallel_gc",
    ]


def check_environment(python):
    subprocess.run([python, "-m", "pip", "check"], check=True)
    directory = Path(__file__).parent
    for script in ("test_cloudpickle_316.py", "test_genshi_316.py", "test_sqlalchemy_pure.py"):
        subprocess.run([python, directory / script], check=True)
    for dependency in ("coverage", "markupsafe", "greenlet", "dulwich"):
        subprocess.run([python, directory / "test_native_dependencies.py", dependency], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--mode", choices=("disabled", "enabled"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--affinity", default="0-31")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    if not args.python.is_file() or args.timeout <= 0:
        parser.error("target Python must exist and timeout must be positive")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    python = str(args.python.absolute())  # Keep the venv path, not its resolved symlink.
    check_environment(python)
    runner.preflight(python, args.mode, ROOT)
    os.environ[runner.MODE_ENV] = args.mode
    benchmarks = selected_benchmarks()
    inventory = ROOT / "benchmarks/results/investigations/integration-validation-2026-10-16/full-pyperformance-preparation/selected-workloads.txt"
    reference = [line[2:] for line in inventory.read_text().splitlines() if line.startswith("- ")]
    if len(reference) != 100 or [bench.name for bench in benchmarks] != reference:
        raise RuntimeError("default program selection differs from the preserved 100-program inventory")
    failures = []
    combined = None
    for index, bench in enumerate(benchmarks, 1):
        print(f"[{index}/{len(benchmarks)}] {bench.name}", flush=True)
        try:
            result = bench.run(python, pyperf_opts=readiness_options(args.affinity, args.timeout), verbose=True)
            suite = result if isinstance(result, pyperf.BenchmarkSuite) else pyperf.BenchmarkSuite([result])
            for measurement in suite:
                measurement.update_metadata({"performance_version": pyperformance.__version__, "tags": bench.tags})
            filename = output / f"{index:03d}-{bench.name}.json"
            suite.dump(str(filename))
            runner.validate_result(filename, args.mode)
            if combined is None:
                combined = suite
            else:
                for measurement in suite:
                    combined.add_benchmark(measurement)
        except Exception as error:
            traceback.print_exc()
            failures.append({"program": bench.name, "error": str(error)})
    if combined is not None:
        combined.dump(str(output / "suite.json"))
    record = {
        "scope": "diagnostic readiness, not performance",
        "python": python,
        "mode": args.mode,
        "programs": [bench.name for bench in benchmarks],
        "failures": failures,
        "named_results": len(combined) if combined else 0,
    }
    (output / "summary.json").write_text(json.dumps(record, indent=2) + "\n")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
