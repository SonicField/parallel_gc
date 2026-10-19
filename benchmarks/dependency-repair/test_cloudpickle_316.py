"""Dependency correctness tests; not timed benchmark workloads."""

import dis
import importlib
import sys
import sysconfig
import unittest


class CloudpickleCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cloudpickle = importlib.import_module("cloudpickle")

    def roundtrip(self, value):
        return self.cloudpickle.loads(self.cloudpickle.dumps(value))

    def test_global_load_store_and_delete(self):
        namespace = {"__name__": "dependency_roundtrip", "value": 42}
        exec(
            "def load():\n    return value\n"
            "def store(new):\n    global value\n    value = new\n"
            "def delete():\n    global value\n    del value\n",
            namespace,
        )
        load, store, delete = self.roundtrip(
            (namespace["load"], namespace["store"], namespace["delete"])
        )
        self.assertEqual(load(), 42)
        store(99)
        self.assertEqual(load(), 99)
        delete()
        with self.assertRaises(NameError):
            load()
        self.assertEqual(namespace["value"], 42)

    def test_nested_global_discovery(self):
        namespace = {"__name__": "dependency_roundtrip", "value": 42}
        exec("def outer():\n    return lambda: value\n", namespace)
        self.assertEqual(self.roundtrip(namespace["outer"])()(), 42)

    def test_closure_and_comprehension(self):
        offset = 7

        def calculate(values):
            return [value + offset for value in values]

        self.assertEqual(self.roundtrip(calculate)([0, 1, 2]), [7, 8, 9])

    def test_discovers_every_present_global_opcode(self):
        namespace = {"__name__": "dependency_roundtrip", "value": 42}
        exec("def delete():\n    global value\n    del value\n", namespace)
        implementation = importlib.import_module("cloudpickle.cloudpickle")
        expected = {
            instruction.argval
            for instruction in dis.get_instructions(namespace["delete"])
            if instruction.opname in ("STORE_GLOBAL", "DELETE_GLOBAL", "LOAD_GLOBAL")
        }
        self.assertEqual(
            set(implementation._walk_global_ops(namespace["delete"].__code__)),
            expected,
        )
        self.assertIn("value", expected)

    def test_free_threaded_runtime_remains_gil_disabled(self):
        if sysconfig.get_config_var("Py_GIL_DISABLED"):
            self.assertFalse(sys._is_gil_enabled())


if __name__ == "__main__":
    unittest.main()
