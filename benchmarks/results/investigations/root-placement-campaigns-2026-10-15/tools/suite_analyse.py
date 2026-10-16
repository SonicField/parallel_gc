"""Analyse project-suite ABBA: runs named <i>-<build>.json in DIR.
Compares candidate vs baseline per metric (parallel mode = the change; serial
mode = control, code identical), with a two-sided permutation test on means."""
import json, sys, glob, os, random, statistics as st
D, BASE, CAND = sys.argv[1], sys.argv[2], sys.argv[3]
runs = {BASE: [], CAND: []}
for p in sorted(glob.glob(os.path.join(D, '*.json'))):
    tag = os.path.basename(p)[:-5].split('-', 1)[1]
    if tag in runs: runs[tag].append(json.load(open(p)))
print(f"files: {BASE}={len(runs[BASE])} {CAND}={len(runs[CAND])}")
rng = random.Random(1)
def perm_p(a, b, n=20000):
    if len(a) < 2 or len(b) < 2: return float('nan')
    obs = abs(st.mean(a) - st.mean(b)); pool = a + b; k = len(a); hit = 0
    for _ in range(n):
        rng.shuffle(pool)
        if abs(st.mean(pool[:k]) - st.mean(pool[k:])) >= obs: hit += 1
    return (hit + 1) / (n + 1)
def row(name, a, b, better_lower):
    if not a or not b: print(f"  {name:44} n/a"); return
    ma, mb = st.mean(a), st.mean(b); ch = (mb / ma - 1) * 100 if ma else float('nan')
    p = perm_p(a, b); sig = '*' if p < 0.01 else ' '
    good = (ch < 0) == better_lower
    tag = '' if p >= 0.01 else ('BETTER' if good else 'WORSE')
    print(f"  {name:44} base={ma:12.3f} cand={mb:12.3f} {ch:+7.1f}% p={p:.4f}{sig} {tag}")
def per_run(build, getter):
    out = []
    for r in runs[build]:
        v = getter(r)
        if v is not None: out.extend(v)
    return out
def comp_metrics(label, getcomp):
    for mode in ('parallel', 'serial'):
        print(f"[{label}] mode={mode}{'  (CONTROL: identical code)' if mode == 'serial' else ''}")
        g = lambda key: (lambda r: [x[key] for x in getcomp(r)[mode]['runs']] if getcomp(r) else None)
        rk = runs[BASE][0] and getcomp(runs[BASE][0])
        if not rk: print("  missing"); continue
        keys = rk[mode]['runs'][0].keys()
        tkey = next((k for k in keys if 'throughput' in k), None)
        if tkey: row('throughput (/s)', per_run(BASE, g(tkey)), per_run(CAND, g(tkey)), False)
        row('collection latency mean (ms)', per_run(BASE, g('collection_latency_mean_ms')), per_run(CAND, g('collection_latency_mean_ms')), True)
        row('collection latency max (ms)', per_run(BASE, g('collection_latency_max_ms')), per_run(CAND, g('collection_latency_max_ms')), True)
        if 'collection_time_pct' in keys:
            row('time in GC callbacks (%)', per_run(BASE, g('collection_time_pct')), per_run(CAND, g('collection_time_pct')), True)
comp_metrics('mixed workload', lambda r: r.get('mixed_workload'))
heaps = sorted(runs[BASE][0].get('synthetic_by_heap', {}).keys()) if runs[BASE] else []
for h in heaps:
    comp_metrics(f'synthetic {h}', lambda r, h=h: r.get('synthetic_by_heap', {}).get(h))
print("[collection shapes] explicit gc.collect() time (ms), raw samples")
shapes = [c['heap_type'] for c in runs[BASE][0].get('collection_results', [])] if runs[BASE] else []
for s in shapes:
    for mode in ('parallel', 'serial'):
        f = lambda r, s=s, mode=mode: next(c[f'{mode}_samples_ms'] for c in r['collection_results'] if c['heap_type'] == s)
        row(f'{s} {mode}{" (control)" if mode == "serial" else ""}', per_run(BASE, f), per_run(CAND, f), True)
print("[within-build parallel/serial ratios, mean of runs]")
for b in (BASE, CAND):
    for r in runs[b]:
        m = r.get('mixed_workload') or {}
        print(f"  {b}: mixed throughput {m.get('throughput_change_pct', float('nan')):+.1f}%  latency {m.get('collection_latency_change_pct', float('nan')):+.1f}%  "
              f"collection geomean {r['summary']['collection_speedup_geomean']:.2f}x  synthetic thr {r['summary']['synthetic_throughput_geomean_pct']:+.1f}%  synthetic lat {r['summary']['synthetic_collection_latency_geomean_pct']:+.1f}%")
