import gc
import unittest

from test.test_gc_ft_parallel import TestParallelMarking

assert hasattr(gc, '_test_set_parallel_mark_verify'), 'verifier must be present'


class MatrixResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.outcomes = {}

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes.setdefault(test._testMethodName, 'pass')

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.outcomes[test._testMethodName] = 'FAIL'

    def addError(self, test, error):
        super().addError(test, error)
        self.outcomes[test._testMethodName] = 'ERROR'

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes[test._testMethodName] = f'skip: {reason}'

    def addSubTest(self, test, subtest, error):
        super().addSubTest(test, subtest, error)
        if error is not None:
            self.outcomes[test._testMethodName] = 'FAIL'


result = MatrixResult()
unittest.defaultTestLoader.loadTestsFromTestCase(TestParallelMarking).run(result)
for name, outcome in sorted(result.outcomes.items()):
    print(f'{name}\t{outcome}')
for test, error in result.failures:
    print(test, error)
if result.errors:
    for test, error in result.errors:
        print(test, error)
    raise SystemExit(2)
