#!/usr/bin/env bash
set -euo pipefail
root=/tmp/parallel-gc-integration-fKKFb7
run_control() {
    local config=$1
    mkdir -p "$root/$config"
    cd "$root/$config"
    local options=(--with-pydebug)
    [[ $config != ft-off ]] || options+=(--disable-gil)
    "$root/source/configure" "${options[@]}" > configure.log 2>&1
    make -j16 > build.log 2>&1
    local suites=(test_gc test_gc_ft_parallel test_gc_ws_deque test_gc_parallel test_gc_parallel_fork test_gc_parallel_properties test_gc_parallel_mark_alive test_parallel_gc_profile test_capi.test_config test_embed)
    [[ $config != ft-off ]] || suites+=(test_free_threading.test_gc)
    timeout 1800 ./python -m test -j8 --timeout 300 "${suites[@]}" > tests.log 2>&1
    echo "$config tests exit=0"
    tail -n 16 tests.log
}
run_control gil-off &
gil_pid=$!
run_control ft-off &
ft_pid=$!
status=0
wait "$gil_pid" || status=1
wait "$ft_pid" || status=1
exit "$status"
