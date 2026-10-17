"""Reuse the full analysis arithmetic, with explicit focused-scope validation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import run_focused_collections as driver

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from analyse_project_abba import collection_rows, require

BASELINE = "c67363fa59543ef5d572383af927f1cff88514a1"
CURRENT = "388fd5bb46fdda6b464db566faf818505c3d6eef"
PARAMETERS = {"heap_size": 500000, "num_runs": 5, "seed": 42,
              "warmup_runs": 3, "creation_threads": 4, "survivor_ratio": 0.8}


def analyse(documents):
    try:
        require(len(documents) == 4, "four complete ABBA legs are required")
        expected_cases = [(rooting, shape) for rooting in ("frame", "module")
                          for shape in driver.HEAP_TYPES]
        reference_policy = documents[0]["system_metadata"]["numa_policy"]
        require(isinstance(reference_policy, str) and reference_policy,
                "recorded NUMA policy is required")
        adapted = []
        for index, (document, revision) in enumerate(zip(
            documents, (BASELINE, CURRENT, CURRENT, BASELINE)
        ), 1):
            require(document["scope"] == "focused-controlled-collections-not-full-suite",
                    f"leg {index}: wrong diagnostic scope")
            require(document["build_type"] == "free-threaded"
                    and document["runtime_gil_enabled_after"] is False,
                    f"leg {index}: wrong build/runtime mode")
            require(document["parameters"] == PARAMETERS,
                    f"leg {index}: changed collection parameters")
            metadata = document["system_metadata"]
            source = metadata["cpython_git"]
            require(source["revision"] == revision and source["dirty"] is False
                    and source["untracked_files"] == [],
                    f"leg {index}: wrong source order or unclean source")
            require(metadata["py_gil_disabled"] == 1
                    and metadata["py_parallel_gc"] == 1,
                    f"leg {index}: wrong compiled configuration")
            require(metadata["cpu_affinity"] == list(range(32))
                    and metadata["numa_policy"] == reference_policy,
                    f"leg {index}: changed affinity or NUMA policy")
            config = document["runtime_config"]
            final = document["config_after"]
            require(config["available"] is True and config["enabled"] is True
                    and config["num_workers"] == 16
                    and final["startup_failed"] is False
                    and final["enabled"] is True and final["pool_active"] is True,
                    f"leg {index}: wrong collector policy or pool startup failure")
            rows = document["collections"]
            require([(row["rooting"], row["heap_type"]) for row in rows] == expected_cases,
                    f"leg {index}: missing, duplicate or reordered case")
            for row in rows:
                driver.validate_result(row, row["heap_type"])
            adapted.append({
                "collection_results": [row for row in rows if row["rooting"] == "frame"],
                "collection_results_module": [row for row in rows if row["rooting"] == "module"],
            })
        return (list(collection_rows(adapted, "frame", "collection_results"))
                + list(collection_rows(adapted, "module", "collection_results_module")))
    except (KeyError, TypeError, OverflowError) as error:
        raise ValueError(f"invalid or incomplete focused evidence: {error}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legs", type=Path, nargs=4)
    args = parser.parse_args()
    try:
        originals = [path.read_bytes() for path in args.legs]
        rows = analyse([json.loads(original) for original in originals])
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({
        "scope": "focused-controlled-collections-not-full-suite",
        "input_files": [{"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}
                        for path, raw in zip(args.legs, originals)],
        "rows": rows,
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
