import gc, sys, os, random, time, _testinternalcapi as t
n = int(sys.argv[1]); w = int(sys.argv[2])
random.seed(1)
class N:
    __slots__ = ('a', 'b', 'c')
xs = [N() for _ in range(n)]
for x in xs:
    x.a, x.b, x.c = random.choice(xs), random.choice(xs), random.choice(xs)
gc.disable(); gc.enable_parallel(); gc.collect()
def cpu():
    r = {}
    for tid in os.listdir('/proc/self/task'):
        with open(f'/proc/self/task/{tid}/schedstat') as f:
            r[tid] = int(f.read().split()[0])
    return r
for _ in range(2):
    t.parallel_gc_set_adaptive_workers(w); gc.collect()
t.parallel_gc_set_adaptive_workers(w)
a = cpu(); t0 = time.perf_counter_ns(); gc.collect(); t1 = time.perf_counter_ns(); b = cpu()
pt = gc.get_parallel_stats()['phase_timing']
d = sorted((b[k] - a.get(k, 0) for k in b), reverse=True)
wall = t1 - t0
print(f"workers={w} wall={wall/1e6:.1f}ms mark_alive={pt['mark_alive_ns']/1e6:.1f}ms "
      f"heap_phases={(pt['update_refs_ns']+pt['mark_heap_ns']+pt['scan_heap_ns'])/1e6:.1f}ms "
      f"sum_cpu/wall={sum(d)/wall:.2f} top_threads_ms={[round(x/1e6,1) for x in d[:5]]}")
