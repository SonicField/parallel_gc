#!/usr/bin/env bash
# Run from the parent root after starting the isolated four-build script.
set -euo pipefail
build_pid=${1:?build process PID required}
root=${2:?isolated build directory required}
project=${3:?parent repository directory required}
[[ $build_pid =~ ^[0-9]+$ ]]
test -d "$root"
test -d "$project/.git"
tail --pid="$build_pid" --sleep-interval=10 -f /dev/null
rg -q '^All four optimized builds checked;' "$root/builds-summary.log"
for mode in gil ft; do
    for revision in baseline candidate; do
        build="$root/$revision-$mode"
        source="$root/$revision-source"
        test -f "$build/profile-run-stamp"
        rg -q 'Running parallel GC profile task:' "$build/build.log"
        rg -q -- '-fprofile-use' "$build/build.log"
        rg -q -- '-flto' "$build/build.log"
        rg -q '^Result: SUCCESS$' "$build/focused-tests.log"
        git -C "$source" diff --quiet
        git -C "$source" diff --cached --quiet
        (cd "$build" && sha256sum --check binary.sha256)
        "$build/python" "$project/benchmarks/results/investigations/integration-validation-2026-10-16/check_benchmark_python.py" "$mode" > "$build/campaign-preflight.json"
    done
done
out="$root/results"
test ! -e "$out"
mkdir -p "$out/project" "$out/pyperformance"
cd "$project"
git rev-parse HEAD > "$out/parent-revision.txt"
git status --short > "$out/parent-status.txt"
git -C "$root/baseline-source" rev-parse HEAD > "$out/baseline-revision.txt"
git -C "$root/candidate-source" rev-parse HEAD > "$out/candidate-revision.txt"
git -C pyperformance rev-parse HEAD > "$out/pyperformance-revision.txt"
sha256sum benchmarks/gc_perf_benchmark.py benchmarks/run_pyperformance.py \
    benchmarks/results/investigations/integration-validation-2026-10-16/check_benchmark_python.py \
    > "$out/harness.sha256"
"$root/driver/bin/python" -m pip freeze > "$out/driver-packages.txt"
lscpu > "$out/host-cpu.txt"
numactl --hardware > "$out/host-numa.txt"
for mode in gil ft; do
    leg=0
    for revision in baseline candidate candidate baseline; do
        leg=$((leg + 1))
        result="$out/project/$mode-$leg-$revision"
        date -u '+%Y-%m-%dT%H:%M:%SZ'
        echo "Project suite: $mode leg $leg $revision"
        numactl --cpunodebind=0 --membind=0 taskset -c 0-31 \
            "$root/$revision-$mode/python" benchmarks/gc_perf_benchmark.py \
            --full --include-synthetic --json --output "$result.json" \
            > "$result.log" 2>&1
        python3 -m json.tool "$result.json" > /dev/null
        sha256sum --check "$out/harness.sha256"
    done
done
status=0
for mode in gil ft; do
    for policy in enabled disabled; do
        date -u '+%Y-%m-%dT%H:%M:%SZ'
        echo "pyperformance: $mode $policy binary ABBA"
        numactl --cpunodebind=0 --membind=0 taskset -c 0-31 \
            "$root/driver/bin/python" benchmarks/run_pyperformance.py binary-abba \
            --baseline-python "$root/baseline-$mode/python" \
            --baseline-source "$root/baseline-source" \
            --candidate-python "$root/candidate-$mode/python" \
            --candidate-source "$root/candidate-source" \
            --mode "$policy" --benchmarks default --run-style rigorous \
            --affinity 0-31 --work-root "$root/pyperformance-$mode" \
            --output-dir "$out/pyperformance/$mode-$policy" \
            > "$out/pyperformance/$mode-$policy.log" 2>&1 || status=1
        sha256sum --check "$out/harness.sha256"
    done
done
date -u '+%Y-%m-%dT%H:%M:%SZ'
echo "Measurements finished; pyperformance failure status=$status"
exit "$status"
