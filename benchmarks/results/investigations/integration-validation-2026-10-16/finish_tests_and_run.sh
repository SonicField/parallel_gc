#!/usr/bin/env bash
# Finish supplementary tests before allowing the unchanged measurement launcher.
set -euo pipefail
build_pid=${1:?build process PID required}
root=${2:?isolated build directory required}
project=${3:?parent repository directory required}
[[ $build_pid =~ ^[0-9]+$ ]]
test -d "$root"
test -d "$project/.git"
test ! -e "$root/results"
tail --pid="$build_pid" --sleep-interval=10 -f /dev/null
rg -q '^All four optimized builds checked;' "$root/builds-summary.log"
cd "$project"
for revision in baseline candidate; do
    gil="$root/$revision-gil"
    rg -q '^Result: SUCCESS$' "$gil/collector-regression.log"
    rg -q '^OK$' "$gil/parent-regression-with-pyperf.log"
    build="$root/$revision-ft"
    venv="$root/test-env-$revision-ft"
    test ! -e "$venv"
    "$build/python" -m venv --without-pip "$venv"
    "$venv/bin/python" -m ensurepip --upgrade > "$build/parent-ensurepip.log" 2>&1
    "$venv/bin/python" -m pip install --no-deps pyperf==2.10.0 \
        > "$build/parent-dependencies-native-pip.log" 2>&1
    "$build/python" -m test -j4 --timeout 600 \
        test_gc test_gc_ft_parallel test_gc_ws_deque \
        test_gc_parallel test_gc_parallel_fork test_gc_parallel_properties \
        test_parallel_gc_profile test_free_threading.test_gc \
        test_capi.test_config test_capi.test_misc test_embed \
        > "$build/collector-regression.log" 2>&1
    "$venv/bin/python" -m unittest -v \
        benchmarks.test_container_traversal_benchmark \
        benchmarks.test_gc_adaptive_benchmark \
        benchmarks.test_gc_perf_benchmark \
        benchmarks.test_pyperformance_support \
        > "$build/parent-regression-with-pyperf.log" 2>&1
    (cd "$build" && sha256sum --check binary.sha256)
    echo "$revision FT supplemental collector and parent tests passed"
done
exec bash "$project/benchmarks/results/investigations/integration-validation-2026-10-16/run_campaign.sh" \
    "$build_pid" "$root" "$project"
