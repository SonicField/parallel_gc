"""Project-suite ABBA analysis with the pre-registered rules of
.vp/plans/bench-rooting-plan.md.

Files in DIR are named <i>-<build>.json, run in order A B B A. The two ABBA
halves are (1:A vs 2:B) and (4:A vs 3:B). For every workload and metric the
script reports the parallel-mode change (candidate vs baseline) overall and
in each half, next to the serial-mode change, which is a control because the
serial code is identical in both builds.

HB (benefit, module-rooted workloads only): latency improves >= 10% (or
throughput >= 5%), the improvement is > 2 x |control change|, and both halves
point the same way.
HN (no harm, all workloads): parallel-mode latency/throughput is not worse by
more than max(3%, 2 x |control change|).
"""
import glob
import json
import os
import statistics as st
import sys

D, BASE, CAND = sys.argv[1], sys.argv[2], sys.argv[3]
files = {}
for path in sorted(glob.glob(os.path.join(D, "*.json"))):
    index, build = os.path.basename(path)[:-5].split("-", 1)
    files[int(index)] = (build, json.load(open(path)))
order = [files[i][0] for i in sorted(files)]
assert order == [BASE, CAND, CAND, BASE], f"expected ABBA order, got {order}"
run = {i: files[i][1] for i in files}


def mean(values):
    values = [v for v in values if v is not None]
    return st.mean(values) if values else float("nan")


def pct(new, old):
    return (new / old - 1) * 100 if old else float("nan")


def comparison_metric(data, mode, key):
    """Mean over runs of one metric of one mode of a comparison dict."""
    if data is None:
        return None
    return mean(r[key] for r in data[mode]["runs"])


def evaluate(label, getter, lower_is_better, module_rooted):
    """getter(json, mode) -> value or None. Prints one row and returns flags."""
    p = {i: getter(run[i], "parallel") for i in run}
    s = {i: getter(run[i], "serial") for i in run}
    if any(v is None for v in p.values()):
        print(f"  {label:42} missing")
        return None
    overall = pct(mean([p[2], p[3]]), mean([p[1], p[4]]))
    half1, half2 = pct(p[2], p[1]), pct(p[3], p[4])
    control = pct(mean([s[2], s[3]]), mean([s[1], s[4]]))
    sign = -1 if lower_is_better else 1          # +ve = improvement
    improvement = sign * overall
    threshold = 10.0 if lower_is_better else 5.0
    hb = (module_rooted and improvement >= threshold
          and improvement > 2 * abs(control)
          and sign * half1 > 0 and sign * half2 > 0)
    harm_limit = max(3.0, 2 * abs(control))
    hn_fail = -improvement > harm_limit
    tag = ("HB-PASS" if hb else "") + (" HN-FAIL" if hn_fail else "")
    print(f"  {label:42} cand vs base {overall:+7.1f}%  halves "
          f"{half1:+7.1f}% {half2:+7.1f}%  control {control:+6.1f}%  {tag}")
    return hb, hn_fail


def comp_rows(name, key, module_rooted):
    getter_comp = lambda r: r.get(key) if not isinstance(key, tuple) else (
        r.get(key[0], {}) or {}).get(key[1])
    rows = [
        ("throughput", "throughput", False),
        ("latency mean", "collection_latency_mean_ms", True),
        ("latency max", "collection_latency_max_ms", True),
    ]
    results = []
    for metric_label, metric, lower in rows:
        results.append(evaluate(
            f"{name}: {metric_label}",
            lambda r, mode, metric=metric: comparison_metric(
                getter_comp(r), mode, metric),
            lower, module_rooted and metric_label != "latency max"))
    return results


def coll_rows(name, key, module_rooted):
    results = []
    shapes = [c["heap_type"] for c in run[1].get(key, [])]
    for shape in shapes:
        def getter(r, mode, shape=shape):
            for c in r.get(key, []):
                if c["heap_type"] == shape:
                    return mean(c[f"{mode}_samples_ms"])
            return None
        results.append(evaluate(f"{name} {shape}: collect time", getter,
                                True, module_rooted))
    return results


all_results = []
print("== existing workloads (frame-rooted) ==")
all_results += comp_rows("mixed", "mixed_workload", False)
for heap in sorted(run[1].get("synthetic_by_heap", {})):
    all_results += comp_rows(f"synthetic {heap}", ("synthetic_by_heap", heap),
                             False)
all_results += coll_rows("collection", "collection_results", False)
print("== module-rooted workloads ==")
all_results += comp_rows("mixed+module cache", "mixed_workload_module_cache",
                         True)
for heap in sorted(run[1].get("synthetic_by_heap_module", {}) or {}):
    all_results += comp_rows(f"synthetic {heap} (module)",
                             ("synthetic_by_heap_module", heap), True)
all_results += coll_rows("collection (module)", "collection_results_module",
                         True)

valid = [r for r in all_results if r is not None]
print(f"\nHB passes: {sum(r[0] for r in valid)}   HN failures: "
      f"{sum(r[1] for r in valid)}   (of {len(valid)} rows)")
print("\nwithin-build parallel vs serial (per file):")
for i in sorted(run):
    r = run[i]
    def ratio(key):
        c = r.get(key)
        if not c:
            return "n/a"
        return (f"thr {c['throughput_change_pct']:+.1f}% "
                f"lat {c['collection_latency_change_pct']:+.1f}%")
    print(f"  {i}-{files[i][0]}: mixed {ratio('mixed_workload')} | "
          f"mixed+cache {ratio('mixed_workload_module_cache')}")
