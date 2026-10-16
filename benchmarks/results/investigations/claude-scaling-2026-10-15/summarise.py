import json, sys, statistics as st
from collections import defaultdict
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
d = defaultdict(list)
for r in rows:
    d[(r['shape'], r['build'], r['mode'])].append(r)
modes = ['serial', '2', '4', '8', '16']
for shape in ['graph', 'tree', 'lists', 'chain']:
    print(f"\n{shape}: median wall ms (speedup vs same-build serial) | mark_alive ms")
    for b in ['base', 'patch']:
        ser = st.median(r['wall_ms'] for r in d[(shape, b, 'serial')])
        cells = []
        for m in modes:
            rs = d[(shape, b, m)]
            if not rs: cells.append('-'); continue
            w = st.median(r['wall_ms'] for r in rs)
            ma = st.median(r.get('mark_alive_ms', float('nan')) for r in rs)
            cells.append(f"{m}:{w:7.1f} ({ser/w:4.2f}x) ma={ma:6.1f}" if m != 'serial' else f"serial:{w:7.1f}")
        print(f"  {b:5s} " + " | ".join(cells))
