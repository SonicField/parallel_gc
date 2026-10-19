"""Exercise Genshi AST construction and the original rendering workloads."""

import ast
import importlib.util
from pathlib import Path
import sys
import sysconfig
import unittest

from genshi.template import MarkupTemplate, NewTextTemplate
from genshi.template.astutil import ASTTransformer
from genshi.template.eval import Expression, Suite, _new


class GenshiCompatibilityTests(unittest.TestCase):
    def test_clone_preserves_fields_and_locations(self):
        for source, mode in (("value + 1", "eval"), ("value = 1", "exec")):
            with self.subTest(mode=mode):
                original = ast.parse(source, mode=mode)
                cloned = ASTTransformer().visit(original)
                self.assertIsNot(original, cloned)
                self.assertEqual(
                    ast.dump(original, include_attributes=True),
                    ast.dump(cloned, include_attributes=True),
                )
                self.assertIsNot(original.body, cloned.body)

    def test_expression_from_string_and_ast(self):
        for source in ("value + 1", ast.parse("value + 1", mode="eval").body):
            self.assertEqual(Expression(source).evaluate({"value": 41}), 42)

    def test_suite_from_string_and_ast(self):
        for source in ("result = value + 1", ast.parse("result = value + 1").body[0]):
            namespace = {"value": 41}
            Suite(source).execute(namespace)
            self.assertEqual(namespace["result"], 42)

    def test_new_accepts_required_keyword_fields(self):
        node = _new(ast.Name, id="value", ctx=ast.Load())
        self.assertEqual(node.id, "value")
        self.assertIsInstance(node.ctx, ast.Load)

    def test_new_retains_duplicate_field_error(self):
        with self.assertRaisesRegex(ValueError, "Field set both"):
            _new(ast.Name, "first", ast.Load(), id="second")

    def test_xml_and_text_output(self):
        self.assertEqual(
            MarkupTemplate("<p>${value}</p>").generate(value=42).render(),
            "<p>42</p>",
        )
        self.assertEqual(NewTextTemplate("${value}").generate(value=42).render(), "42")

    def test_original_benchmark_functions(self):
        benchmark_file = (
            Path(__file__).resolve().parents[2]
            / "pyperformance/pyperformance/data-files/benchmarks/bm_genshi/run_benchmark.py"
        )
        spec = importlib.util.spec_from_file_location("original_genshi_benchmark", benchmark_file)
        benchmark = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(benchmark)
        for kind, (template_class, template_source) in benchmark.BENCHMARKS.items():
            with self.subTest(kind=kind):
                self.assertGreater(benchmark.bench_genshi(1, template_class, template_source), 0)

    def test_free_threaded_runtime_remains_gil_disabled(self):
        if sysconfig.get_config_var("Py_GIL_DISABLED"):
            self.assertFalse(sys._is_gil_enabled())


if __name__ == "__main__":
    unittest.main()
