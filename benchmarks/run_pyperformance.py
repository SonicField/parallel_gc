#!/usr/bin/env python3
"""Run verified pyperformance comparisons for parallel GC."""

import argparse
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYPERFORMANCE_ROOT = PROJECT_ROOT / "pyperformance"
SUPPORT_ROOT = PROJECT_ROOT / "benchmarks" / "pyperformance_support"
DEFAULT_WORK_ROOT = PROJECT_ROOT / ".pyperformance"
MODE_ENV = "PARALLEL_GC_PYPERFORMANCE_MODE"
RUN_ID_ENV = "PYPERFORMANCE_RUNID"
HOOK_NAME = "parallel_gc"
ABBA_MODES = ("disabled", "enabled", "enabled", "disabled")
INHERITED_ENV = f"{MODE_ENV},{RUN_ID_ENV}"
RUN_STYLE_ARGS = {
    None: None,
    "fast": "--fast",
    "rigorous": "--rigorous",
    "debug": "--debug-single-value",
}


class CampaignError(RuntimeError):
    pass


def run_command(argv, *, cwd=None, env=None, capture=False):
    print("+", " ".join(map(str, argv)), flush=True)
    return subprocess.run(
        command_record(argv),
        cwd=cwd,
        env=env,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def command_record(argv):
    """Return the executed command in JSON-serializable form."""
    return [str(arg) for arg in argv]


def driver_command(*args):
    return [sys.executable, "-m", "pyperformance", *args]


def parse_venv_path(output):
    prefix = "Virtual environment path: "
    for line in output.splitlines():
        if line.startswith(prefix):
            value = line[len(prefix):]
            return Path(value.partition(" (")[0])
    raise CampaignError("pyperformance did not report its virtual environment")


def target_venv_python(venv_root):
    if os.name == "nt":
        return venv_root / "Scripts" / "python.exe"
    return venv_root / "bin" / "python"


def benchmarks_arg(benchmarks):
    """Keep exclusion-only selections attached to their option name."""
    return f"--benchmarks={benchmarks}"


def require_driver():
    try:
        import pyperf  # noqa: F401
        import pyperformance  # noqa: F401
    except ImportError as exc:
        raise CampaignError(
            "the driver environment lacks pyperformance; follow the setup "
            "commands in docs/BENCHMARKING.md"
        ) from exc

    hooks = {
        entry.name
        for entry in importlib.metadata.entry_points().select(group="pyperf.hook")
    }
    if HOOK_NAME not in hooks:
        raise CampaignError(
            "the driver environment lacks the parallel_gc pyperf hook; "
            "install benchmarks/pyperformance_support"
        )


def require_checkout():
    if not (PYPERFORMANCE_ROOT / "pyproject.toml").is_file():
        raise CampaignError(
            "pyperformance submodule is missing; run "
            "git submodule update --init pyperformance"
        )


def show_target_venv(target_python, work_root):
    result = run_command(
        driver_command("venv", "show", "--python", target_python),
        cwd=work_root,
        capture=True,
    )
    return parse_venv_path(result.stdout)


def ensure_target_venv(target_python, work_root, benchmarks):
    require_target_module(target_python, "zlib")
    venv_root = show_target_venv(target_python, work_root)
    venv_python = target_venv_python(venv_root)
    if not venv_python.is_file():
        run_command(
            driver_command(
                "venv",
                "create",
                "--python",
                target_python,
                benchmarks_arg(benchmarks),
                f"--inherit-environ={INHERITED_ENV}",
            ),
            cwd=work_root,
        )
    if not venv_python.is_file():
        raise CampaignError(f"target virtual environment was not created: {venv_root}")

    run_command(
        [
            venv_python,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--editable",
            SUPPORT_ROOT,
        ],
        cwd=work_root,
    )
    return venv_python


def require_target_module(target_python, module):
    result = subprocess.run(
        [target_python, "-c", f"import {module}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise CampaignError(
            f"target Python cannot import {module!r}; pyperformance cannot "
            "create its benchmark environment. Rebuild CPython after "
            f"installing the {module} development dependency."
        )


def preflight(venv_python, mode, work_root):
    code = (
        "import json, os; "
        "from parallel_gc_pyperformance.mode import apply_mode; "
        f"config = apply_mode(os.environ[{MODE_ENV!r}]); "
        "print(json.dumps(config, sort_keys=True))"
    )
    env = os.environ.copy()
    env[MODE_ENV] = mode
    env[RUN_ID_ENV] = "parallel-gc-preflight"
    result = run_command(
        [venv_python, "-c", code],
        cwd=work_root,
        env=env,
        capture=True,
    )
    try:
        config = json.loads(result.stdout.strip())
    except json.JSONDecodeError as exc:
        raise CampaignError(
            f"activation preflight returned invalid JSON: {result.stdout!r}"
        ) from exc

    expected = {
        "enabled": (True, True),
        "disabled": (True, False),
        "feature-off": (False, False),
    }[mode]
    observed = (config.get("available") is True, config.get("enabled") is True)
    if observed != expected:
        raise CampaignError(
            f"activation preflight for {mode!r} returned {config!r}"
        )
    return config


def run_suite(
    *,
    target_python,
    mode,
    output,
    work_root,
    benchmarks,
    run_style,
    affinity,
    timeout,
    append=False,
):
    venv_python = ensure_target_venv(target_python, work_root, benchmarks)
    config = preflight(venv_python, mode, work_root)

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    command = driver_command(
        "run",
        "--python",
        target_python,
        benchmarks_arg(benchmarks),
        f"--inherit-environ={INHERITED_ENV}",
        "--hook",
        HOOK_NAME,
    )
    if append:
        command.extend(("--append", output))
    else:
        command.extend(("--output", output))
    run_style_arg = RUN_STYLE_ARGS[run_style]
    if run_style_arg:
        command.append(run_style_arg)
    if affinity:
        command.extend(("--affinity", affinity))
    if timeout:
        command.extend(("--timeout", str(timeout)))

    env = os.environ.copy()
    env[MODE_ENV] = mode
    run_command(command, cwd=work_root, env=env)
    validate_result(output, mode)
    return {"command": command_record(command), "preflight": config}


def validate_result(filename, mode):
    import pyperf

    suite = pyperf.BenchmarkSuite.load(str(filename))
    names = []
    for benchmark in suite:
        names.append(benchmark.get_name())
        metadata = benchmark.get_metadata()
        if metadata.get("parallel_gc_mode") != mode:
            raise CampaignError(
                f"{benchmark.get_name()} lacks verified {mode!r} metadata: "
                f"{metadata!r}"
            )
        expected_enabled = mode == "enabled"
        if bool(metadata.get("parallel_gc_enabled")) != expected_enabled:
            raise CampaignError(
                f"{benchmark.get_name()} recorded the wrong enabled state"
            )
    if not names:
        raise CampaignError(f"result contains no benchmarks: {filename}")
    return tuple(names)


def require_matching_benchmarks(reference, observed, filename):
    if observed != reference:
        missing = sorted(set(reference) - set(observed))
        extra = sorted(set(observed) - set(reference))
        raise CampaignError(
            f"benchmark set differs in {filename}: "
            f"missing={missing!r}, extra={extra!r}"
        )


def combine_results(inputs, output):
    import pyperf

    if output.exists():
        output.unlink()
    for filename in inputs:
        pyperf.add_runs(str(output), pyperf.BenchmarkSuite.load(str(filename)))


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_record(path):
    revision = run_command(
        ["git", "-C", path, "rev-parse", "HEAD"], capture=True
    ).stdout.strip()
    status = run_command(
        ["git", "-C", path, "status", "--short"], capture=True
    ).stdout.splitlines()
    return {"revision": revision, "dirty": bool(status), "status": status}


def target_record(target_python):
    code = """
import gc, json, sys, sysconfig
print(json.dumps({
    "version": sys.version,
    "git": sys._git,
    "gil_enabled": sys._is_gil_enabled(),
    "config_args": sysconfig.get_config_var("CONFIG_ARGS"),
    "parallel_config": gc.get_parallel_config(),
}, sort_keys=True))
"""
    result = run_command(
        [target_python, "-c", code], capture=True
    )
    return json.loads(result.stdout)


def write_campaign_record(output_dir, args, runs, result_files):
    record = {
        "schema": 1,
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "host": {
            "node": platform.node(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "order": list(ABBA_MODES),
        "resumed": args.resume,
        "benchmarks": args.benchmarks,
        "run_style": args.run_style,
        "affinity": args.affinity,
        "target_python": str(Path(args.python).resolve()),
        "target": target_record(args.python),
        "parallel_gc_repository": git_record(PROJECT_ROOT),
        "cpython_repository": git_record(PROJECT_ROOT / "cpython"),
        "pyperformance_repository": git_record(PYPERFORMANCE_ROOT),
        "runs": runs,
        "results": {
            path.name: sha256_file(path)
            for path in result_files
        },
    }
    destination = output_dir / "campaign.json"
    destination.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return destination


def compare_results(disabled, enabled, output, work_root):
    result = run_command(
        driver_command(
            "compare",
            "--output_style",
            "table",
            disabled,
            enabled,
        ),
        cwd=work_root,
        capture=True,
    )
    output.write_text(result.stdout)


def run_abba(args):
    output_dir = Path(args.output_dir).resolve()
    if (
        output_dir.exists()
        and any(output_dir.iterdir())
        and not args.resume
    ):
        raise CampaignError(f"output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    work_root = Path(args.work_root).resolve()
    work_root.mkdir(parents=True, exist_ok=True)

    run_files = []
    runs = []
    reference_benchmarks = None
    for index, mode in enumerate(ABBA_MODES, 1):
        filename = output_dir / f"{index:02d}-{mode}.json"
        if args.resume and filename.is_file():
            detail = {"resumed": True}
        else:
            detail = run_suite(
                target_python=args.python,
                mode=mode,
                output=filename,
                work_root=work_root,
                benchmarks=args.benchmarks,
                run_style=args.run_style,
                affinity=args.affinity,
                timeout=args.timeout,
            )
            detail["resumed"] = False
        observed_benchmarks = validate_result(filename, mode)
        if reference_benchmarks is None:
            reference_benchmarks = observed_benchmarks
        else:
            require_matching_benchmarks(
                reference_benchmarks, observed_benchmarks, filename
            )
        detail.update({"sequence": index, "mode": mode, "result": filename.name})
        runs.append(detail)
        run_files.append(filename)

    disabled = output_dir / "disabled-combined.json"
    enabled = output_dir / "enabled-combined.json"
    combine_results((run_files[0], run_files[3]), disabled)
    combine_results((run_files[1], run_files[2]), enabled)
    validate_result(disabled, "disabled")
    validate_result(enabled, "enabled")

    comparison = output_dir / "comparison.txt"
    compare_results(disabled, enabled, comparison, work_root)
    results = [*run_files, disabled, enabled, comparison]
    record = write_campaign_record(output_dir, args, runs, results)
    print(f"ABBA campaign complete: {record}")


def run_single(args):
    work_root = Path(args.work_root).resolve()
    work_root.mkdir(parents=True, exist_ok=True)
    run_suite(
        target_python=args.python,
        mode=args.mode,
        output=Path(args.output),
        work_root=work_root,
        benchmarks=args.benchmarks,
        run_style=args.run_style,
        affinity=args.affinity,
        timeout=args.timeout,
    )


def add_common_args(parser):
    parser.add_argument("--python", required=True, help="optimized target Python")
    parser.add_argument("--benchmarks", default="default")
    parser.add_argument(
        "--run-style",
        choices=("fast", "rigorous", "debug"),
        default=None,
    )
    parser.add_argument("--affinity")
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--work-root", default=DEFAULT_WORK_ROOT)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("single", help="run one verified suite")
    add_common_args(single)
    single.add_argument("--mode", required=True, choices=(
        "enabled", "disabled", "feature-off"
    ))
    single.add_argument("--output", required=True)
    single.set_defaults(func=run_single)

    abba = subparsers.add_parser(
        "abba", help="run disabled/enabled/enabled/disabled campaign"
    )
    add_common_args(abba)
    abba.add_argument("--output-dir", required=True)
    abba.add_argument(
        "--resume",
        action="store_true",
        help="reuse validated raw legs already present in the output directory",
    )
    abba.set_defaults(func=run_abba)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    require_checkout()
    require_driver()
    target = Path(args.python).resolve()
    if not target.is_file():
        raise CampaignError(f"target Python does not exist: {target}")
    args.python = str(target)
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except (CampaignError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
