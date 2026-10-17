"""Validate focused evidence without inventing statistical acceptance."""
import copy
import unittest

import analyse_focused_collections as analysis
from test_run_focused_collections import valid_result


def documents():
    result = []
    for source in (analysis.BASELINE, analysis.CURRENT,
                   analysis.CURRENT, analysis.BASELINE):
        rows = []
        for rooting in ("frame", "module"):
            for shape in analysis.driver.HEAP_TYPES:
                row = valid_result()
                row.update(heap_type=shape, rooting=rooting)
                rows.append(row)
        result.append({
            "scope": "focused-controlled-collections-not-full-suite",
            "build_type": "free-threaded",
            "parameters": analysis.PARAMETERS.copy(),
            "runtime_gil_enabled_after": False,
            "runtime_config": {"available": True, "enabled": True,
                               "num_workers": 16},
            "config_after": {"startup_failed": False, "enabled": True,
                             "pool_active": True},
            "system_metadata": {
                "cpython_git": {"revision": source, "dirty": False,
                                "untracked_files": []},
                "py_gil_disabled": 1, "py_parallel_gc": 1,
                "cpu_affinity": list(range(32)), "numa_policy": "bind node 0",
            },
            "collections": rows,
        })
    return result


class AnalysisTests(unittest.TestCase):
    def test_complete_zero_change_returns_all_cases_and_raw_samples(self):
        rows = analysis.analyse(documents())
        self.assertEqual(len(rows), 16)
        for row in rows:
            self.assertEqual(row["parallel"]["change_pct"], 0)
            self.assertEqual(row["parallel"]["half_changes_pct"], [0, 0])
            self.assertEqual(row["parallel"]["legs"][0]["samples"], [8.0] * 5)

    def test_positive_duration_change_means_slower(self):
        data = documents()
        for index in (1, 2):
            for row in data[index]["collections"]:
                row["parallel_samples_ms"] = [10.0] * 5
                row["parallel_time_ms"] = 10.0
        rows = analysis.analyse(data)
        self.assertEqual(rows[0]["parallel"]["change_pct"], 25.0)
        self.assertEqual(rows[0]["parallel"]["half_changes_pct"], [25.0, 25.0])
        self.assertEqual(rows[0]["serial"]["change_pct"], 0)

    def test_incomplete_abba(self):
        with self.assertRaises(ValueError):
            analysis.analyse(documents()[:3])

    def test_wrong_source_or_dirty_source(self):
        for field, value in (("revision", analysis.BASELINE), ("dirty", True),
                             ("untracked_files", ["new.c"])):
            data = documents()
            data[1]["system_metadata"]["cpython_git"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                analysis.analyse(data)

    def test_missing_duplicate_or_reordered_case(self):
        for change in ("remove", "duplicate", "reorder"):
            data = documents()
            rows = data[0]["collections"]
            if change == "remove":
                rows.pop()
            elif change == "duplicate":
                rows[-1] = copy.deepcopy(rows[0])
            else:
                rows.reverse()
            with self.subTest(change=change), self.assertRaises(ValueError):
                analysis.analyse(data)

    def test_changed_count_across_legs(self):
        data = documents()
        for arm in ("serial", "parallel"):
            data[2]["collections"][0][f"{arm}_object_counts"] = [400000] * 5
        with self.assertRaises(ValueError):
            analysis.analyse(data)

    def test_wrong_scope_mode_or_runtime(self):
        for field, value in (("scope", "full-suite"), ("build_type", "gil"),
                             ("runtime_gil_enabled_after", True)):
            data = documents()
            data[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                analysis.analyse(data)

    def test_changed_configuration_placement_or_policy(self):
        for category, field, value in (
            ("parameters", "num_runs", 1),
            ("system_metadata", "cpu_affinity", [0]),
            ("system_metadata", "numa_policy", "another policy"),
            ("system_metadata", "py_gil_disabled", 0),
            ("runtime_config", "num_workers", 4),
            ("runtime_config", "enabled", False),
            ("config_after", "startup_failed", True),
            ("config_after", "pool_active", False),
            ("config_after", "enabled", False),
        ):
            data = documents()
            data[1][category][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                analysis.analyse(data)

    def test_missing_field_reports_invalid_evidence(self):
        data = documents()
        del data[0]["parameters"]
        with self.assertRaises(ValueError):
            analysis.analyse(data)


if __name__ == "__main__":
    unittest.main()
