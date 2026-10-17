#!/usr/bin/env bash
# Prepare every selected default dependency before any timing starts.
set -euo pipefail
project=/data/users/alexturner/parallel_gc
builds=/tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW
root=/tmp/parallel-gc-pyperformance-prepared-20261017-dBFKZD
export PATH=/tmp/parallel-gc-rust-toolchain-20261017-TtLNUp/bin:/tmp/parallel-gc-rust-toolchain-20261017-TtLNUp/prefix/usr/bin:$PATH
export CARGO_BUILD_JOBS=4
test -d "$root"
test ! -e "$root/gil/venv"
test ! -e "$root/ft/venv"
mkdir -p "$root/gil" "$root/ft"
cd "$project"
sha256sum benchmarks/gc_perf_benchmark.py benchmarks/run_pyperformance.py \
  benchmarks/pyperformance_support/parallel_gc_pyperformance/hook.py \
  > "$root/harness.sha256"
(
  cd "$root"
  "$builds/driver/bin/python" -m pyperformance list --benchmarks default
) > "$root/selected-workloads.txt"
for mode in gil ft; do
  for revision in baseline candidate; do
    label="$revision-$mode"
    date -u '+%Y-%m-%dT%H:%M:%SZ'
    echo "Preparing full default dependencies: $label"
    git -C "$builds/$revision-source" diff --quiet
    git -C "$builds/$revision-source" diff --cached --quiet
    (cd "$builds/$label" && sha256sum --check binary.sha256)
    (
      cd "$root/$mode"
      "$builds/driver/bin/python" -m pyperformance venv create \
        --python "$builds/$label/python" --benchmarks default \
        --inherit-environ=PARALLEL_GC_PYPERFORMANCE_MODE,PYPERFORMANCE_RUNID
    ) > "$root/$label-create.log" 2>&1
    "$builds/driver/bin/python" -c '
import sys
from pathlib import Path
from benchmarks.run_pyperformance import ensure_target_venv
python = ensure_target_venv(sys.argv[1], Path(sys.argv[2]), "default", None)
print("VERIFIED_PYTHON=" + str(python))
' "$builds/$label/python" "$root/$mode" \
      > "$root/$label-hook-setup.log" 2>&1
    benchmark_venv_python=$(sed -n 's/^VERIFIED_PYTHON=//p' "$root/$label-hook-setup.log")
    test -x "$benchmark_venv_python"
    "$benchmark_venv_python" \
      "$project/benchmarks/results/investigations/integration-validation-2026-10-16/pyperformance-preparation-evidence/native_probe.py" \
      > "$root/$label-native-probe.json"
    "$benchmark_venv_python" -m pip check > "$root/$label-pip-check.txt"
    "$benchmark_venv_python" -m pip freeze > "$root/$label-packages.txt"
    sha256sum --check "$root/harness.sha256"
    echo "Full default dependencies checked: $label"
  done
done
echo "All four full-default environments prepared; no timings started."
