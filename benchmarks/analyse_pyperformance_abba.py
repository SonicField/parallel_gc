"""Describe complete rigorous source ABBA without assigning acceptance.

Use leg means equally; pyperf worker values in one leg are not independent
source comparisons. Positive execution-time changes denote slower execution.
"""

import argparse
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys

import pyperf


SPEC = importlib.util.spec_from_file_location(
    "pyperformance_runner", Path(__file__).with_name("run_pyperformance.py")
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verified_file(path, digest):
    require(path.is_file(), f"missing result: {path}")
    require(runner.sha256_file(path) == digest, f"recorded digest differs: {path}")


def leg_summary(benchmark):
    values = benchmark.get_values()
    require(values and all(math.isfinite(value) and value > 0 for value in values),
            f"{benchmark.get_name()}: execution times must be finite and positive")
    require(benchmark.get_unit() == "second", f"{benchmark.get_name()}: expected seconds")
    processes = sum(bool(run.values) for run in benchmark.get_runs())
    require(processes >= 2, f"{benchmark.get_name()}: insufficient measured processes")
    return {
        "mean_seconds": statistics.mean(values),
        "stdev_seconds": statistics.stdev(values) if len(values) > 1 else None,
        "values": len(values), "measured_processes": processes,
    }


def analyse_campaign(directory, *, expected_programs=100, expected_results=127):
    directory = Path(directory)
    record_path = directory / "campaign.json"
    require(record_path.is_file(), f"missing completed campaign record: {record_path}")
    record = json.loads(record_path.read_text())
    require(record["schema"] == 2 and record["comparison"] == "baseline-candidate",
            "expected source ABBA campaign")
    require(record["order"] == list(runner.BINARY_ABBA_LABELS), "wrong source ABBA order")
    require(record["run_style"] == "rigorous", "only rigorous campaigns may be compared")
    require(record["benchmarks"] == "default", "expected complete original default selection")
    require(len(record["runs"]) == 4, "a complete comparison requires four source legs")
    mode = record["mode"]
    require(mode in ("enabled", "disabled"), "expected enabled or disabled runtime mode")
    suites = []
    reference_names = None
    reference_work = None
    reference_programs = None
    for index, (run, label) in enumerate(zip(record["runs"], runner.BINARY_ABBA_LABELS), 1):
        name = f"{index:02d}-{label}.json"
        require(run["sequence"] == index and run["target"] == label
                and run["mode"] == mode and run["result"] == name,
                f"leg {index}: recorded input/order differs")
        require(len(run["programs"]) == expected_programs,
                f"leg {index}: expected {expected_programs} original programs")
        programs = tuple(item["program"] for item in run["programs"])
        require(len(set(programs)) == expected_programs, f"leg {index}: duplicate programs")
        if reference_programs is None:
            reference_programs = programs
        require(programs == reference_programs, f"leg {index}: original program set differs")
        filename = directory / name
        verified_file(filename, record["results"][name])
        for program in run["programs"]:
            verified_file(filename.with_suffix(".programs") / program["result"], program["sha256"])
        suite = pyperf.BenchmarkSuite.load(str(filename))
        compiled = suite.get_benchmarks()[0].get_runs()[0].get_metadata().get(
            "parallel_gc_build_gil_disabled"
        )
        require(type(compiled) is bool, f"leg {index}: compiled GIL mode is missing")
        names = runner.validate_prepared_result(filename, mode, compiled)
        require(len(names) == expected_results, f"leg {index}: expected {expected_results} named results")
        work = runner.result_work_signature(filename)
        if reference_names is None:
            reference_names, reference_work, reference_compiled = names, work, compiled
        require(names == reference_names and work == reference_work,
                f"leg {index}: named results or recorded work differ")
        require(compiled is reference_compiled, f"leg {index}: compiled GIL mode differs")
        suites.append(suite)

    rows = []
    for name in reference_names:
        legs = [leg_summary(suite.get_benchmark(name)) for suite in suites]
        means = [leg["mean_seconds"] for leg in legs]
        baseline = statistics.mean([means[0], means[3]])
        candidate = statistics.mean([means[1], means[2]])
        halves = [100 * (means[1] / means[0] - 1), 100 * (means[2] / means[3] - 1)]
        rows.append({
            "benchmark": name, "legs": legs,
            "baseline_mean_seconds": baseline, "candidate_mean_seconds": candidate,
            "time_ratio": candidate / baseline,
            "time_change_pct": 100 * (candidate / baseline - 1),
            "half_time_changes_pct": halves,
            "half_direction": "differs" if halves[0] * halves[1] < 0 else "agrees",
        })
    return {
        "campaign": str(record_path), "campaign_sha256": runner.sha256_file(record_path),
        "targets": record["targets"], "build_mode": "ft" if reference_compiled else "gil",
        "runtime_mode": mode, "program_count": expected_programs, "result_count": len(rows),
        "geomean_time_change_pct": 100 * (statistics.geometric_mean(
            row["time_ratio"] for row in rows
        ) - 1),
        "rows": rows,
        "interpretation": "Descriptive leg means and half-comparisons; no acceptance or causal verdict.",
    }


def markdown(report):
    lines = [
        f"# {report['build_mode'].upper()} / {report['runtime_mode']}: source ABBA",
        "", "Positive time change means slower execution; null is 0%. Each source mean weights its two legs equally.",
        "", f"Original programs: {report['program_count']}; named results: {report['result_count']}.",
        f"Geometric mean time change: {report['geomean_time_change_pct']:+.2f}% (summary only).",
        "", "Per-leg variation and process/value counts are retained in the adjacent JSON. Retain the original upstream comparison and stability warnings with this report. Opposing half-directions are not evidence of a stable effect. Agreement alone does not establish statistical significance or causation.",
        "", "| Benchmark | B1 ms | C2 ms | C3 ms | B4 ms | Time change | Half 1 | Half 2 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["rows"]:
        means = " | ".join(f"{1000 * leg['mean_seconds']:.4f}" for leg in row["legs"])
        first, second = row["half_time_changes_pct"]
        lines.append(f"| {row['benchmark']} | {means} | {row['time_change_pct']:+.2f}% | {first:+.2f}% | {second:+.2f}% |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign_directory", type=Path)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    outputs = [args.output_prefix.with_suffix(suffix) for suffix in (".json", ".md")]
    require(not any(path.exists() for path in outputs), "analysis output already exists")
    report = analyse_campaign(args.campaign_directory)
    outputs[0].write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    outputs[1].write_text(markdown(report))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError) as exc:
        print(f"Invalid or incomplete campaign: {exc}", file=sys.stderr)
        raise SystemExit(2)
