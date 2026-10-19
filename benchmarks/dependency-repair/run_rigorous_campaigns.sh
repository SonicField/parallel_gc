#!/usr/bin/env bash
# Execute four full source-ABBA campaigns against frozen, prepared inputs.
set -euo pipefail
if [[ $# != 4 ]]; then
    echo "usage: $0 PROJECT BUILD_ROOT PREPARED_ROOT NEW_OUTPUT_ROOT" >&2
    exit 2
fi
project=$1
build_root=$2
prepared_root=$3
output_root=$4
cd "$project"
mkdir "$output_root"
exec > >(tee "$output_root/controller.log") 2>&1

fingerprint() {
    sha256sum benchmarks/run_pyperformance.py \
        benchmarks/pyperformance_support/parallel_gc_pyperformance/*.py
    git -C pyperformance rev-parse HEAD
    (cd pyperformance && git ls-files -z | xargs -0 sha256sum)
    for source in baseline candidate; do
        git -C "$build_root/$source-source" rev-parse HEAD
        git -C "$build_root/$source-source" diff --exit-code HEAD
        for mode in gil ft; do
            (cd "$build_root/$source-$mode" && sha256sum -c binary.sha256)
            sha256sum "$build_root/$source-$mode/python"
        done
    done
}

fingerprint > "$output_root/inputs-before.txt"
git rev-parse HEAD > "$output_root/parent-revision.txt"
date -u
uname -a
lscpu
ps -eo pid,psr,pcpu,etime,comm --sort=-pcpu | head -20 || true
for mode in gil ft; do
    for source in baseline candidate; do
        prepared_python=$(sed -n '1p' "$prepared_root/$source-$mode-python.txt")
        "$prepared_python" -m pip check
        "$prepared_python" -m pip freeze --all > "$output_root/$source-$mode-freeze.txt"
    done
    cmp "$output_root/baseline-$mode-freeze.txt" "$output_root/candidate-$mode-freeze.txt"
done

# Revalidate the complete prior readiness results with the stricter validator.
"$build_root/driver/bin/python" -c '
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("runner", "benchmarks/run_pyperformance.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
root = pathlib.Path(sys.argv[1]) / "readiness"
reference = None
for source in ("baseline", "candidate"):
    for mode in ("gil", "ft"):
        for policy in ("disabled", "enabled"):
            context = root / f"{source}-{mode}-{policy}"
            assert len(list(context.glob("[0-9][0-9][0-9]-*.json"))) == 100
            names = runner.validate_prepared_result(context / "suite.json", policy, mode == "ft")
            assert len(names) == 127
            if reference is None:
                reference = names
            assert names == reference
            print(f"Readiness metadata revalidated: {context.name}, 100 programs / 127 results")
' "$prepared_root"

for mode in gil ft; do
    baseline_env=$(sed -n '1p' "$prepared_root/baseline-$mode-python.txt")
    candidate_env=$(sed -n '1p' "$prepared_root/candidate-$mode-python.txt")
    for policy in disabled enabled; do
        fingerprint > "$output_root/inputs-$mode-$policy-before.txt"
        cmp "$output_root/inputs-before.txt" "$output_root/inputs-$mode-$policy-before.txt"
        echo "START $mode $policy: $(date -u +%FT%TZ)"
        numactl --cpunodebind=0 --membind=0 taskset --cpu-list 0-31 \
            "$build_root/driver/bin/python" benchmarks/run_pyperformance.py binary-abba \
            --baseline-python "$build_root/baseline-$mode/python" \
            --candidate-python "$build_root/candidate-$mode/python" \
            --baseline-source "$build_root/baseline-source" \
            --candidate-source "$build_root/candidate-source" \
            --baseline-prepared-python "$baseline_env" \
            --candidate-prepared-python "$candidate_env" \
            --mode "$policy" --benchmarks default --run-style rigorous \
            --affinity 0-31 --timeout 300 \
            --work-root "$output_root/work" \
            --output-dir "$output_root/$mode-$policy" \
            > "$output_root/$mode-$policy.log" 2>&1
        fingerprint > "$output_root/inputs-$mode-$policy-after.txt"
        cmp "$output_root/inputs-before.txt" "$output_root/inputs-$mode-$policy-after.txt"
        echo "COMPLETE $mode $policy: $(date -u +%FT%TZ)"
    done
done
echo "ALL FOUR CAMPAIGNS COMPLETE: $(date -u +%FT%TZ)"
