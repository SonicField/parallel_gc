#!/bin/bash
# Project suite ABBA: baseline, candidate, candidate, baseline. Cores 0-31 only.
set -u
OUT=$1; A=$2; B=$3        # build dirs
BENCH_DIR=${BENCH_DIR:-$HOME/local/parallel_gc_claude-wt/parent-bench}
SUITE_FLAGS=${SUITE_FLAGS:---full --include-synthetic}
mkdir -p "$OUT"; cd "$BENCH_DIR"
echo "bench_dir=$BENCH_DIR rev=$(git rev-parse --short HEAD) flags=$SUITE_FLAGS" >> "$OUT/runs.log"
python3 ~/local/parallel_gc_claude/.vp/tools/cpu_monitor.py "$OUT/cpu.log" & MON=$!
i=0
for b in "$A" "$B" "$B" "$A"; do
  i=$((i+1)); tag="$i-$(basename $b)"
  echo "$(date -Is) start $tag sha=$(sha256sum $b/python | cut -c1-16)" >> "$OUT/runs.log"
  taskset -c 0-31 "$b/python" benchmarks/gc_perf_benchmark.py $SUITE_FLAGS \
      --json -o "$OUT/$tag.json" > "$OUT/$tag.stdout" 2> "$OUT/$tag.stderr"
  echo "$(date -Is) end $tag exit=$?" >> "$OUT/runs.log"
done
kill $MON
