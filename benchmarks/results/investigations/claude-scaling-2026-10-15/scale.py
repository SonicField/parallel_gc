import gc, sys, time, random, statistics, json
shape, n, mode = sys.argv[1], int(sys.argv[2]), sys.argv[3]
holder = sys.argv[4] if len(sys.argv) > 4 else 'global'
random.seed(1)
class N:
    __slots__ = ('a', 'b', 'c', '__weakref__')
def build(shape):
    if shape == 'graph':          # live random graph, out-degree 3
        xs = [N() for _ in range(n)]
        for x in xs:
            x.a, x.b, x.c = random.choice(xs), random.choice(xs), random.choice(xs)
        return xs
    if shape == 'chain':          # live singly linked chain held by its head only
        head = N(); cur = head
        for _ in range(n - 1):
            nxt = N(); cur.a = nxt; cur = nxt
        return [head]
    if shape == 'tree':           # live balanced binary tree held by root only
        nodes = [N() for _ in range(n)]
        for i in range(n):
            l, r = 2*i+1, 2*i+2
            nodes[i].a = nodes[l] if l < n else None
            nodes[i].b = nodes[r] if r < n else None
        root = nodes[0]; del nodes[:]
        return [root]
    if shape == 'lists':          # live: many small lists of ints/tuples
        return [[(i, i+1), [i], {'k': i}] for i in range(n // 4)]
    raise SystemExit(shape)

def measure():
    gc.disable()
    if mode != 'serial':
        gc.enable_parallel()
        import _testinternalcapi as t
        gc.collect()                     # lazy pool creation
        t.parallel_gc_set_adaptive_workers(int(mode))
        gc.collect(); gc.collect()       # warm
    samples, phases = [], []
    for _ in range(9):
        if mode != 'serial':
            t.parallel_gc_set_adaptive_workers(int(mode))
        t0 = time.perf_counter_ns(); gc.collect(); t1 = time.perf_counter_ns()
        samples.append(t1 - t0)
        if mode != 'serial':
            phases.append(gc.get_parallel_stats()['phase_timing'])
    out = {'shape': shape, 'mode': mode, 'holder': holder,
           'wall_ms': statistics.median(samples) / 1e6}
    if phases:
        for k in ('mark_alive_ns', 'update_refs_ns', 'mark_heap_ns', 'scan_heap_ns', 'total_ns'):
            out[k[:-3] + '_ms'] = statistics.median(p[k] for p in phases) / 1e6
    print(json.dumps(out))

if holder == 'global':            # reachable from sys.modules['__main__']
    keep = build(shape)
    measure()
else:                             # reachable only from a frame local
    def run():
        keep = build(shape)
        measure()
        return keep
    run()
