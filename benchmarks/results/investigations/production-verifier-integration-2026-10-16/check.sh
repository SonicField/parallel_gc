#!/usr/bin/env bash
set -euo pipefail
root=/tmp/parallel-gc-integration-fKKFb7
phase=${1:?baseline or cleanup}
case "$phase" in baseline|cleanup|production-tests|verified-production-tests|final-production-tests) ;; *) exit 2 ;; esac
run_config() {
    local config=$1
    local build="$root/$config"
    mkdir -p "$build"
    cd "$build"
    local options=(--with-parallel-gc)
    [[ $config != ft-* ]] || options+=(--disable-gil)
    [[ $config != *-dbg ]] || options+=(--with-pydebug)
    if [[ ! -f Makefile ]]; then
        "$root/source/configure" "${options[@]}" > configure.log 2>&1
    fi
    local gate_status=0
    if [[ ! -f $phase-gate.log ]]; then
        make -k -j4 Python/gc.o Python/gc_free_threading.o Python/gc_parallel.o Python/gc_free_threading_parallel.o \
            CFLAGS_NODIST='-Werror=unused-function -Werror=unused-variable' > "$phase-gate.log" 2>&1 || gate_status=$?
        echo "$phase $config warning-gate exit=$gate_status errors=$(rg -c 'error:' "$phase-gate.log" || true)"
    fi
    if [[ $phase != baseline && $gate_status != 0 ]]; then return "$gate_status"; fi
    make -j16 > "$phase-build.log" 2>&1
    nm -g --defined-only Python/gc.o Python/gc_free_threading.o Python/gc_parallel.o Python/gc_free_threading_parallel.o \
        | awk 'NF == 3 && $2 ~ /^[TDBR]$/ {print $2, $3}' | sort > "$phase-symbols.txt"
    local suites=(test_gc test_gc_ft_parallel test_gc_ws_deque test_gc_parallel test_gc_parallel_fork test_gc_parallel_properties test_gc_parallel_mark_alive test_parallel_gc_profile test_capi.test_config test_embed)
    [[ $config != ft-* ]] || suites+=(test_free_threading.test_gc)
    timeout 1800 ./python -m test -j8 --timeout 300 "${suites[@]}" > "$phase-tests.log" 2>&1
    echo "$phase $config tests exit=0"
    tail -n 14 "$phase-tests.log"
    if [[ $phase == cleanup ]]; then
        diff -u baseline-symbols.txt cleanup-symbols.txt
        echo "$phase $config exported-symbols unchanged"
    fi
}
pids=()
for config in gil-rel ft-rel gil-dbg ft-dbg; do
    run_config "$config" &
    pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
exit "$status"
