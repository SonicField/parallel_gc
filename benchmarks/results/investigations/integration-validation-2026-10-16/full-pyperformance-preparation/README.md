# Full-default preparation before fresh pyperformance

Prepared fresh environments under `/tmp/parallel-gc-pyperformance-prepared-20261017-dBFKZD`, separate from the earlier failed/partial attempt. No measurements were started by preparation. `prepare.sh` uses the four existing verified PGO+LTO binaries and the isolated Rust toolchain. It requests the pinned pyperformance default selection: exactly 100 selected programs, preserved in `selected-workloads.txt`. It does not exclude FastAPI or change benchmark dependency versions.

All four `venv create --benchmarks default` commands succeeded. Each target's editable parallel-GC hook installed, native FastAPI/pydantic request probe passed, and `pip check` reports no broken requirements. The four package lists are byte-identical between baseline and candidate within each build mode. Both FT native probes retain runtime GIL disabled. Source trees and executable hashes were checked, and all three current timed-harness/hook fingerprints pass. These establish preparation, not completion or neutrality of the promised sixteen suites.

Preserved complete create/setup logs, selected program inventory, package lists, four native JSON probes, dependency consistency outputs, fingerprints and preparation summary. The first preparation invocation failed before environment creation because executing `python -m pyperformance` from the parent checkout let its outer submodule directory shadow the installed package. The corrected script runs that command from the owned work directory. Both summaries are retained; no benchmark or pyperformance source code changed to fix the invocation directory.

## Fresh campaign launcher and refusal checks

The separate `../run_prepared_pyperformance.sh` runs only the remaining pyperformance comparisons. It does not repeat or merge project-suite data. It requires the successful four-target preparation summary, recorded 100-program selection, matching baseline/candidate package lists, clean CPython sources, matching binary/harness hashes, native/runtime probe results and dependency consistency checks before creating a result directory.

Syntax checking passes. Supplying an owned empty preparation root exits nonzero and creates no results. A second isolated fixture copied the real preparation records but changed candidate FT's runtime GIL flag to enabled; the launcher rejected that JSON before creating results or starting timing. Actual preparation records were not modified. These checks establish refusal of the two tested incomplete/mislabeled states, not every possible preparation defect.

Run from the parent repository:

```bash
bash \
  benchmarks/results/investigations/integration-validation-2026-10-16/run_prepared_pyperformance.sh \
  /tmp/parallel-gc-pyperformance-prepared-20261017-dBFKZD \
  /tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW \
  /data/users/alexturner/parallel_gc
```

The launcher requires an absent `results/` directory; do not use this command to overwrite an existing campaign. It runs enabled and disabled binary ABBAs for GIL, then FT, sequentially with the unchanged rigorous/default options and CPU affinity 0–31, NUMA node 0. It preserves command failures and checks fingerprints between campaigns. The source pair remains baseline `c67363fa59543ef5d572383af927f1cff88514a1`, candidate `388fd5bb46fdda6b464db566faf818505c3d6eef`.

Post-import runtime GIL metadata and collector activation remain checked by the timed worker's existing hook outside measured values. A successfully prepared native request is not a substitute for actual benchmark execution. Every requested suite, raw result, source/binary attestation, program coverage check and analysis still remains required.
