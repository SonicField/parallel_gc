# Exact-container traversal benchmarks

These project-owned pyperformance benchmarks isolate free-threaded parallel-GC traversal of exact built-in containers. They do not modify the upstream pyperformance submodule.

| Benchmark | Default graph | GC traversal edges |
|-----------|---------------|-------------------:|
| `parallel_gc_list_traversal` | 1,000 lists; each level repeats the preceding list | 499,500 |
| `parallel_gc_tuple_traversal` | 1,000 tracked tuples; each level repeats the preceding tuple and a tracked list anchor | 500,500 |
| `parallel_gc_dict_unicode_traversal` | 700 combined Unicode-key dictionaries with repeated values | 245,350 |
| `parallel_gc_dict_general_traversal` | 500 general-key dictionaries with tracked keys and repeated values | 250,500 |
| `parallel_gc_dict_split_traversal` | 20,000 split dictionaries with 16 shared-key values | 320,000 |

The benchmark process disables automatic collection, constructs and validates the graph, and performs one untimed collection immediately before every timed collection. The timed collection must report no collected objects. Metadata records the graph kind, container and auxiliary node counts, traversal-edge count, dimensions, and collections per loop. The outer runner rejects legs whose recorded work differs.

Run all five smoke checks against one interpreter:

```bash
.venvs/pyperformance-driver/bin/python \
    benchmarks/run_pyperformance.py single \
    --python build-pyperformance-ft/python \
    --manifest benchmarks/PARALLEL_GC_MANIFEST \
    --benchmarks default \
    --mode enabled \
    --run-style debug \
    --output /tmp/parallel-gc-container-smoke.json
```

Compare two matched optimized binaries with parallel GC enabled in both:

```bash
.venvs/pyperformance-driver/bin/python \
    benchmarks/run_pyperformance.py binary-abba \
    --baseline-python build-container-baseline-ft/python \
    --candidate-python build-container-candidate-ft/python \
    --mode enabled \
    --manifest benchmarks/PARALLEL_GC_MANIFEST \
    --benchmarks parallel_gc_list_traversal \
    --run-style rigorous \
    --output-dir benchmarks/results/pyperformance/list-binary-abba
```

Repeat the binary ABBA campaign with `--mode disabled`. This control must remain neutral because the specialized traversal path is inactive.
