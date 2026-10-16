#!/usr/bin/env bash
set -euo pipefail
root=/tmp/parallel-gc-integration-fKKFb7
run_config() {
    local config=$1
    cd "$root/$config"
    make Makefile > header-dependencies-config.log 2>&1
    local target=Python/gc_parallel.o
    [[ $config != ft-* ]] || target=Python/gc_free_threading_parallel.o
    make -W "$root/source/Include/internal/pycore_gc_random_walk.h" "$target" \
        CFLAGS_NODIST='-Werror=unused-function -Werror=unused-variable' \
        > header-dependencies-compile.log 2>&1
    make -j16 > header-dependencies-build.log 2>&1
    local suites=(test_gc test_gc_ft_parallel test_gc_ws_deque test_gc_parallel test_gc_parallel_fork test_gc_parallel_properties test_gc_parallel_mark_alive test_parallel_gc_profile test_capi.test_config test_embed)
    [[ $config != ft-* ]] || suites+=(test_free_threading.test_gc)
    timeout 1800 ./python -m test -j8 --timeout 300 "${suites[@]}" > header-dependencies-tests.log 2>&1
    echo "$config: dependency-driven object rebuild, link and tests passed"
    tail -n 14 header-dependencies-tests.log
}
pids=()
for config in gil-rel ft-rel gil-dbg ft-dbg; do
    run_config "$config" &
    pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
exit "$status"
