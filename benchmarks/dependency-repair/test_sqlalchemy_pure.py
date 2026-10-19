"""Require the approved SQLAlchemy implementation and original workloads."""

import importlib.util
from pathlib import Path
import sys
import sysconfig
import unittest

import sqlalchemy


class SQLAlchemyPureTests(unittest.TestCase):
    def test_original_version_and_no_native_modules(self):
        self.assertEqual(sqlalchemy.__version__, "1.4.19")
        for name in ("cprocessors", "cresultproxy", "cimmutabledict"):
            with self.subTest(module=name):
                self.assertIsNone(importlib.util.find_spec(f"sqlalchemy.{name}"))

    def test_original_workloads_and_row_counts(self):
        root = Path(__file__).resolve().parents[2] / "pyperformance/pyperformance/data-files/benchmarks"
        for kind in ("declarative", "imperative"):
            with self.subTest(kind=kind):
                path = root / f"bm_sqlalchemy_{kind}" / "run_benchmark.py"
                spec = importlib.util.spec_from_file_location(f"original_sqlalchemy_{kind}", path)
                benchmark = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(benchmark)
                try:
                    self.assertGreater(benchmark.bench_sqlalchemy(1, 100), 0)
                    if kind == "declarative":
                        self.assertEqual(benchmark.session.query(benchmark.Person).count(), 100)
                        self.assertEqual(benchmark.session.query(benchmark.Address).count(), 100)
                    else:
                        for table in (benchmark.Person, benchmark.Address):
                            count = sqlalchemy.select(sqlalchemy.func.count()).select_from(table)
                            self.assertEqual(benchmark.engine.execute(count).scalar(), 100)
                finally:
                    benchmark.session.close()
                    benchmark.engine.dispose()

    def test_free_threaded_runtime_remains_gil_disabled(self):
        if sysconfig.get_config_var("Py_GIL_DISABLED"):
            self.assertFalse(sys._is_gil_enabled())


if __name__ == "__main__":
    unittest.main()
