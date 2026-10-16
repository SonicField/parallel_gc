import gc
import unittest

from benchmarks import test_gc_perf_benchmark

total = 0
for enabled in (False, True):
    if enabled:
        gc.enable_parallel()
    else:
        gc.disable_parallel()
    for repeat in range(10):
        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromModule(
            test_gc_perf_benchmark).run(result)
        if not result.wasSuccessful():
            for test, error in result.failures + result.errors:
                print(test, error)
            raise SystemExit(1)
        total += result.testsRun
    print(f"policy={'armed' if enabled else 'off'}: 10 suites passed", flush=True)
gc.disable_parallel()
print(f"Total: {total} tests, no failures/errors")
