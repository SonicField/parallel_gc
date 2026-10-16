#!/usr/bin/env bash
set -euo pipefail
root=/tmp/parallel-gc-integration-fKKFb7
run_sanitizer() {
    local config=$1
    mkdir -p "$root/$config"
    cd "$root/$config"
    local options=(--with-pydebug --with-parallel-gc)
    [[ $config != ft-* ]] || options+=(--disable-gil)
    if [[ $config == *-tsan ]]; then
        options+=(--with-thread-sanitizer)
        export LDFLAGS="-L$root/tsan-runtime/usr/lib64 -Wl,-rpath,$root/tsan-runtime/usr/lib64"
        export TSAN_OPTIONS="halt_on_error=1 die_after_fork=0 suppressions=$root/source/Tools/tsan/suppressions.txt handle_segv=0"
    else
        options+=(--with-address-sanitizer)
        export ASAN_OPTIONS=detect_leaks=0
    fi
    "$root/source/configure" "${options[@]}" > configure.log 2>&1
    make -j16 > build.log 2>&1
    local suites=(test_gc test_gc_ft_parallel test_gc_ws_deque test_gc_parallel test_gc_parallel_fork test_gc_parallel_properties test_gc_parallel_mark_alive test_parallel_gc_profile test_capi.test_config test_embed)
    [[ $config != ft-* ]] || suites+=(test_free_threading.test_gc)
    if [[ $config == *-tsan ]]; then
        suites=(test_gc_ft_parallel test_gc_parallel_fork test_gc_ws_deque)
        if [[ $config == ft-* ]]; then
            suites+=(test_free_threading.test_gc)
        else
            suites+=(test_gc test_gc_parallel_mark_alive)
        fi
    fi
    timeout 1800 ./python -m test -j4 --timeout 300 "${suites[@]}" > tests.log 2>&1
    echo "$config tests exit=0"
    tail -n 16 tests.log
}
pids=()
for config in gil-asan ft-asan gil-tsan ft-tsan; do
    run_sanitizer "$config" &
    pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
exit "$status"
