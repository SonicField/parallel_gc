import inspect
import unittest

from benchmarks import gc_perf_benchmark as benchmark
from benchmarks import test_gc_perf_benchmark as tests

original = benchmark.run_synthetic_benchmark
source = inspect.getsource(original)
head, marker, tail = source.partition('    def module_worker(worker_id: int):')
assert marker
needle = '                new_clusters = heap_generator(churn_per_thread, rng=rng)'
assert tail.count(needle) == 1
tail = tail.replace(needle, '                local_heap = _MODULE_ROOT["synthetic"][worker_id]\n' + needle)
try:
    exec(compile(head + marker + tail, '<planted-persistent-holder>', 'exec'), benchmark.__dict__)
    result = unittest.TestResult()
    tests.ModuleRootedSyntheticTests('test_module_rooted_heaps_have_no_persistent_holder_local').run(result)
    assert len(result.failures) == 1 and not result.errors, (result.failures, result.errors)
    assert 'local_heap' in result.failures[0][1]
finally:
    benchmark.run_synthetic_benchmark = original
print('Sustained persistent local_heap mutation: detected.')

original = benchmark.run_collection_benchmark
source = inspect.getsource(original)
needle = '                    _MODULE_ROOT["collection"] = keep_refs\n                    keep_refs = None'
assert source.count(needle) == 1
source = source.replace(needle, '                    _MODULE_ROOT["collection"] = keep_refs')
try:
    exec(compile(source, '<planted-collection-holder>', 'exec'), benchmark.__dict__)
    result = unittest.TestResult()
    tests.ModuleRootedCollectionTests('test_module_rooted_keep_set_has_no_frame_references').run(result)
    assert len(result.failures) == 1 and not result.errors, (result.failures, result.errors)
    assert 'keep_refs' in result.failures[0][1]
finally:
    benchmark.run_collection_benchmark = original
print('Controlled collection keep_refs mutation: detected. Original functions restored.')
