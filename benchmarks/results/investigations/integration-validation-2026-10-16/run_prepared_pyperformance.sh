#!/usr/bin/env bash
# Restart only pyperformance after complete native/default preparation.
set -euo pipefail
root=${1:?prepared environment root required}
builds=${2:?verified optimized-build root required}
project=${3:?parallel_gc parent root required}
test -d "$root"
test -d "$builds"
test -d "$project/.git"
rg -q '^All four full-default environments prepared; no timings started\.$' \
  "$root/preparation-summary-v2.log"
rg -q '^Total: 100 benchmarks$' "$root/selected-workloads.txt"
test ! -e "$root/results"
cd "$project"
sha256sum --check "$root/harness.sha256"
for mode in gil ft; do
  cmp "$root/baseline-$mode-packages.txt" "$root/candidate-$mode-packages.txt"
  for revision in baseline candidate; do
    label="$revision-$mode"
    rg -q '^No broken requirements found\.$' "$root/$label-pip-check.txt"
    git -C "$builds/$revision-source" diff --quiet
    git -C "$builds/$revision-source" diff --cached --quiet
    (cd "$builds/$label" && sha256sum --check binary.sha256)
    "$builds/$label/python" \
      "$project/benchmarks/results/investigations/integration-validation-2026-10-16/check_benchmark_python.py" \
      "$mode" > "$root/$label-restart-preflight.json"
  done
done
"$builds/driver/bin/python" -c '
import json
from pathlib import Path
import sys
root = Path(sys.argv[1])
for mode in ("gil", "ft"):
    for revision in ("baseline", "candidate"):
        path = root / f"{revision}-{mode}-native-probe.json"
        record = json.loads(path.read_text())
        if (record["native"] is not True
                or record["gil_enabled"] is not (mode == "gil")
                or record["response"] != {"value": 42}
                or record["pydantic_core"] != "2.50.1"):
            raise SystemExit(f"Native/runtime preparation failed: {path}")
' "$root"
mkdir "$root/results"
git rev-parse HEAD > "$root/results/parent-revision.txt"
status=0
for mode in gil ft; do
  for policy in enabled disabled; do
    date -u '+%Y-%m-%dT%H:%M:%SZ'
    echo "Prepared pyperformance: $mode $policy binary ABBA"
    sha256sum --check "$root/harness.sha256"
    numactl --cpunodebind=0 --membind=0 taskset -c 0-31 \
      "$builds/driver/bin/python" benchmarks/run_pyperformance.py binary-abba \
      --baseline-python "$builds/baseline-$mode/python" \
      --baseline-source "$builds/baseline-source" \
      --candidate-python "$builds/candidate-$mode/python" \
      --candidate-source "$builds/candidate-source" \
      --mode "$policy" --benchmarks default --run-style rigorous \
      --affinity 0-31 --work-root "$root/$mode" \
      --output-dir "$root/results/$mode-$policy" \
      > "$root/results/$mode-$policy.log" 2>&1 || status=1
    sha256sum --check "$root/harness.sha256"
  done
done
date -u '+%Y-%m-%dT%H:%M:%SZ'
echo "Prepared pyperformance campaigns finished; failure status=$status"
exit "$status"
