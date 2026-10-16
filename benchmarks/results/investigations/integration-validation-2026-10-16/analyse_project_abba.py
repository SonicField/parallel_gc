"""Describe a complete project-suite source ABBA; do not assign acceptance.

Sustained samples are run-level measurements, not individual collections.
Variation within a leg and differences between ABBA halves are descriptive:
five runs in one time window are not five independent source experiments.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys


LABELS = ("baseline", "candidate", "candidate", "baseline")
COLLECTION_HEAPS = (
    "chain", "tree", "wide_tree", "graph", "layered", "independent",
    "ai_workload", "web_server",
)
SYNTHETIC_HEAPS = ("chain", "graph", "ai_workload")
STANDARD_CONFIGURATION = {
    "parallel_gc_available": True,
    "worker_ceiling": 16,
    "num_threads": 4,
    "duration_per_benchmark": 60.0,
    "num_runs": 5,
    "heap_size": 500_000,
    "random_seed": 42,
    "collection_warmup_runs": 3,
    "collection_survivor_ratio": 0.8,
    "collection_creation_threads": 4,
    "module_cache_size": 500_000,
}
RUN_METRICS = {
    "throughput": "higher",
    "collection_latency_mean_ms": "lower",
    "collection_latency_max_ms": "lower",
    "collection_time_ms": "lower",
    "collection_time_pct": "lower",
    "collections": None,
    "duration_sec": None,
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def numbers(values):
    require(isinstance(values, list) and len(values) == 5,
            "each arm must contain five samples")
    require(all(isinstance(x, (int, float)) and not isinstance(x, bool)
                and math.isfinite(x) and x >= 0 for x in values),
            "measurements must be finite, nonnegative numbers")
    return values


def sample_summary(samples):
    samples = numbers(samples)
    return {
        "samples": samples,
        "n": len(samples),
        "mean": statistics.mean(samples),
        "stdev": statistics.stdev(samples),
        "min": min(samples),
        "max": max(samples),
    }


def percent(new, old):
    return 100 * (new / old - 1) if old else None


def describe_arm(samples):
    legs = [sample_summary(sample) for sample in samples]
    baseline = statistics.mean([legs[0]["mean"], legs[3]["mean"]])
    candidate = statistics.mean([legs[1]["mean"], legs[2]["mean"]])
    return {
        "legs": legs,
        "baseline_mean": baseline,
        "candidate_mean": candidate,
        "change_pct": percent(candidate, baseline),
        "half_changes_pct": [percent(legs[1]["mean"], legs[0]["mean"]),
                             percent(legs[2]["mean"], legs[3]["mean"])],
    }


def metric_row(kind, rooting, workload, metric, samples, preferred_direction):
    arms = {arm: describe_arm(samples[arm]) for arm in ("serial", "parallel")}
    return {
        "kind": kind,
        "rooting": rooting,
        "workload": workload,
        "metric": metric,
        "preferred_direction": preferred_direction,
        **arms,
        "parallel_vs_serial_pct": [
            percent(arms["parallel"]["legs"][i]["mean"],
                    arms["serial"]["legs"][i]["mean"])
            for i in range(4)
        ],
    }


def validate_documents(documents, mode, baseline, candidate):
    require(len(documents) == 4, "a complete ABBA requires four documents")
    require(baseline != candidate, "source revisions must differ")
    reference_policy = documents[0]["system"]["numa_policy"]
    require(isinstance(reference_policy, str) and reference_policy,
            "recorded NUMA policy is required")
    for index, (document, label) in enumerate(zip(documents, LABELS), 1):
        config = document["configuration"]
        require(config["build_type"] == mode, f"leg {index}: wrong build mode")
        for key, value in STANDARD_CONFIGURATION.items():
            require(config[key] == value, f"leg {index}: changed {key}")
        system = document["system"]
        source = system["cpython_git"]
        require(source["revision"] == {"baseline": baseline, "candidate": candidate}[label],
                f"leg {index}: wrong source revision or order")
        require(source["dirty"] is False and not source.get("untracked_files", []),
                f"leg {index}: source tree is not clean")
        require(system["py_gil_disabled"] == int(mode == "ft")
                and system["py_parallel_gc"] == 1,
                f"leg {index}: wrong compiled configuration")
        require(system["cpu_affinity"] == list(range(32)),
                f"leg {index}: changed CPU affinity")
        require(system["numa_policy"] == reference_policy,
                f"leg {index}: changed NUMA policy")
        for key in ("synthetic_by_heap", "synthetic_by_heap_module"):
            require(set(document[key]) == set(SYNTHETIC_HEAPS),
                    f"leg {index}: missing or unexpected sustained workload in {key}")
        for key in ("collection_results", "collection_results_module"):
            heaps = [row["heap_type"] for row in document[key]]
            require(len(heaps) == len(COLLECTION_HEAPS)
                    and set(heaps) == set(COLLECTION_HEAPS),
                    f"leg {index}: missing or duplicate collection shape in {key}")


def sustained_rows(documents, rooting, mixed_key, synthetic_key):
    comparisons = [("mixed", [d[mixed_key] for d in documents])]
    comparisons.extend((heap, [d[synthetic_key][heap] for d in documents])
                       for heap in SYNTHETIC_HEAPS)
    for workload, comparisons_for_workload in comparisons:
        for metric, direction in RUN_METRICS.items():
            samples = {arm: [[run[metric] for run in comparison[arm]["runs"]]
                             for comparison in comparisons_for_workload]
                       for arm in ("serial", "parallel")}
            yield metric_row("sustained", rooting, workload, metric, samples, direction)


def collection_rows(documents, rooting, key):
    collections = [{row["heap_type"]: row for row in d[key]} for d in documents]
    for heap in COLLECTION_HEAPS:
        reference_counts = collections[0][heap]["serial_object_counts"]
        require(isinstance(reference_counts, list) and len(reference_counts) == 5
                and all(isinstance(n, int) and not isinstance(n, bool) and n > 0
                        for n in reference_counts),
                f"{rooting} {heap}: invalid actual object counts")
        samples = {}
        for arm in ("serial", "parallel"):
            for collection in collections:
                require(collection[heap][f"{arm}_object_counts"] == reference_counts,
                        f"{rooting} {heap}: actual object counts differ")
            samples[arm] = [collection[heap][f"{arm}_samples_ms"]
                            for collection in collections]
        row = metric_row("controlled_collection", rooting, heap, "collect_time_ms",
                         samples, "lower")
        row["object_counts"] = reference_counts
        yield row


def analyse_documents(documents, *, mode, baseline, candidate):
    try:
        require(mode in ("gil", "ft"), "mode must be gil or ft")
        validate_documents(documents, mode, baseline, candidate)
        rows = []
        for rooting, mixed, synthetic, collections in (
            ("frame", "mixed_workload", "synthetic_by_heap", "collection_results"),
            ("module", "mixed_workload_module_cache", "synthetic_by_heap_module",
             "collection_results_module"),
        ):
            rows.extend(sustained_rows(documents, rooting, mixed, synthetic))
            rows.extend(collection_rows(documents, rooting, collections))
    except (KeyError, TypeError, OverflowError) as error:
        raise ValueError(f"invalid or incomplete measurement document: {error}") from error
    return {
        "mode": mode,
        "baseline": baseline,
        "candidate": candidate,
        "order": list(LABELS),
        "change_definition": "100 * (candidate / baseline - 1); null ratio is 1",
        "sample_unit": "one sustained run or one controlled collection",
        "limitations": [
            "Run-level callback means are not weighted by collection count.",
            "Callback start-to-stop duration is not FT stopped-world duration.",
            "The maximum-duration metric is a mean of each run's maximum, not a percentile.",
            "Within-leg standard deviations and ABBA halves describe variation; no confidence or acceptance verdict is assigned.",
            "Collection count and measured duration have no preferred direction by themselves.",
            "Serial arms are controls, not a guarantee that binary layout or PGO effects are identical.",
        ],
        "leg_metadata": [{"timestamp": d.get("timestamp"), "system": d["system"]}
                         for d in documents],
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="corrected results/project directory")
    parser.add_argument("--mode", required=True, choices=("gil", "ft"))
    parser.add_argument("--baseline", default="c67363fa59543ef5d572383af927f1cff88514a1")
    parser.add_argument("--candidate", default="388fd5bb46fdda6b464db566faf818505c3d6eef")
    args = parser.parse_args()
    try:
        documents, inputs = [], []
        for index, label in enumerate(LABELS, 1):
            path = args.directory / f"{args.mode}-{index}-{label}.json"
            content = path.read_bytes()
            documents.append(json.loads(content))
            inputs.append({"path": str(path), "sha256": hashlib.sha256(content).hexdigest()})
        report = analyse_documents(documents, mode=args.mode,
                                   baseline=args.baseline, candidate=args.candidate)
        report["inputs"] = inputs
        json.dump(report, sys.stdout, indent=2, allow_nan=False)
        print()
    except (OSError, ValueError) as error:
        parser.exit(1, f"Analysis refused: {error}\n")


if __name__ == "__main__":
    main()
