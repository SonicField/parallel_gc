"""HV (benchmark validity): on the BASELINE build, do the suite's module-rooted
collection heaps reproduce the PROPAGATE defect while frame-rooted twins do not?
Builds the suite's own heaps (same generators, seeds, survivor selection and
rooting code paths), then times gc.collect() at fixed worker counts 2 and 16
via the private hook, recording phase_timing.mark_alive_ns and total_ns."""
import gc, json, random, statistics, sys
sys.path.insert(0, sys.argv[1])               # parent-benchdev checkout
from benchmarks import gc_perf_benchmark as b
import _testinternalcapi as t
heap_type, rooting = sys.argv[2], sys.argv[3]
def main():
    # Everything runs inside a function so that rooting='frame' really is a
    # frame local (script top-level names are module globals of __main__).
    pool = b.get_creation_pool(b.COLLECTION_CREATION_THREADS)
    gc.disable(); gc.enable_parallel(); gc.collect()
    out = {"heap_type": heap_type, "rooting": rooting}
    for workers in (2, 16):
        ma, tot = [], []
        for rep in range(5):
            clusters = pool.create_objects(heap_type, 500_000)
            rng = random.Random(b.BENCHMARK_SEED); rng.shuffle(clusters)
            keep = clusters[:int(len(clusters) * b.COLLECTION_SURVIVOR_RATIO)]
            clusters = None
            if rooting == "module":
                b._MODULE_ROOT["collection"] = keep; keep = None
            t.parallel_gc_set_adaptive_workers(workers); gc.collect()
            pt = gc.get_parallel_stats()["phase_timing"]
            ma.append(pt["mark_alive_ns"] / 1e6); tot.append(pt["total_ns"] / 1e6)
            keep = None; b._MODULE_ROOT.pop("collection", None); gc.collect()
        out[f"w{workers}"] = {"mark_alive_ms": statistics.median(ma), "total_ms": statistics.median(tot)}
    pool.shutdown()
    print(json.dumps(out))


main()
