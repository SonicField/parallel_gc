"""Log busy % for cores 0-31 and 32-71 once a minute until killed."""
import time, sys
def snap():
    d = {}
    for line in open('/proc/stat'):
        if line.startswith('cpu') and line[3].isdigit():
            f = line.split(); n = int(f[0][3:]); v = list(map(int, f[1:]))
            d[n] = (sum(v) - v[3] - v[4], sum(v))
    return d
out = open(sys.argv[1], 'a'); prev = snap()
while True:
    time.sleep(60); cur = snap()
    def busy(lo, hi):
        b = sum(cur[c][0] - prev[c][0] for c in range(lo, hi + 1) if c in cur)
        t = sum(cur[c][1] - prev[c][1] for c in range(lo, hi + 1) if c in cur)
        return 100.0 * b / t if t else 0.0
    out.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} cores0-31={busy(0,31):5.1f}% cores32-71={busy(32,71):5.1f}%\n"); out.flush()
    prev = cur
