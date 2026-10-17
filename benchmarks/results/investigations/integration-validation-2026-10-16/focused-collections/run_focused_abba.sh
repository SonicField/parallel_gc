#!/usr/bin/env bash
# An explicit diagnostic subset; the complete project suite is already recorded.
set -euo pipefail
build_root=${1:?existing optimized four-build root required}
out=${2:?existing empty owned output directory required}
project=${3:?parent repository directory required}
test -d "$out"
test -z "$(ls -A "$out")"
test -d "$project/.git"
tools_dir="$project/benchmarks/results/investigations/integration-validation-2026-10-16"
focus="$tools_dir/focused-collections"
test "$(git -C "$build_root/baseline-source" rev-parse HEAD)" = \
    c67363fa59543ef5d572383af927f1cff88514a1
test "$(git -C "$build_root/candidate-source" rev-parse HEAD)" = \
    388fd5bb46fdda6b464db566faf818505c3d6eef
for revision in baseline candidate; do
    git -C "$build_root/$revision-source" diff --quiet
    git -C "$build_root/$revision-source" diff --cached --quiet
    (cd "$build_root/$revision-ft" && sha256sum --check binary.sha256)
    "$build_root/$revision-ft/python" "$tools_dir/check_benchmark_python.py" ft \
        > "$out/$revision-preflight.json"
done
sha256sum "$project/benchmarks/gc_perf_benchmark.py" \
    "$focus/run_focused_collections.py" "$focus/run_focused_abba.sh" \
    "$focus/analyse_focused_collections.py" > "$out/fingerprints.sha256"
git -C "$project" rev-parse HEAD > "$out/parent-revision.txt"
git -C "$project" status --short > "$out/parent-status.txt"
lscpu > "$out/host-cpu.txt"
numactl --hardware > "$out/host-numa.txt"
leg=0
for revision in baseline candidate candidate baseline; do
    leg=$((leg + 1))
    date -u '+%Y-%m-%dT%H:%M:%SZ'
    echo "FOCUSED_FT_LEG=$leg $revision"
    numactl --cpunodebind=0 --membind=0 taskset -c 0-31 \
        "$build_root/$revision-ft/python" "$focus/run_focused_collections.py" \
        > "$out/ft-$leg-$revision.json" 2> "$out/ft-$leg-$revision.log"
    python3 -m json.tool "$out/ft-$leg-$revision.json" > /dev/null
    sha256sum --check "$out/fingerprints.sha256"
    (cd "$build_root/$revision-ft" && sha256sum --check binary.sha256)
    git -C "$build_root/$revision-source" diff --quiet
    git -C "$build_root/$revision-source" diff --cached --quiet
done
python3 "$focus/analyse_focused_collections.py" \
    "$out/ft-1-baseline.json" "$out/ft-2-candidate.json" \
    "$out/ft-3-candidate.json" "$out/ft-4-baseline.json" \
    > "$out/analysis.json"
date -u '+%Y-%m-%dT%H:%M:%SZ'
echo "FOCUSED_FT_COMPLETE=1"
