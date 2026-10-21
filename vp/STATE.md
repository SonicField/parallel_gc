# Current documentation and investigation state

Updated 21 October 2026. This is a reviewer navigation summary under the
level-D [documentation reconciliation](records/changes/DOC-000001/record.md),
not source correctness, performance acceptance or full VP conformance.

## What is complete and what remains

The integration project ABBA, focused/unchanged FT repeats, dependency repairs
and all sixteen rigorous source-comparison pyperformance suites are complete.
Individual negative measurements and their causal explanations remain open.
The latest four-block GIL follow-up did not reproduce the earlier large
BTree/NetworkX increases in its shared reconstructed runtime; that does not
prove source cleanup benign, explain the original difference or recover the
original runtime. [Investigation/choice register](REGISTRY.md).

Linux matrix/compiler/full-suite, Windows and macOS successes are reported
for the 19 October checkpoint. Exact job/source artifacts, counts and skips
have not been inspected in the current record. No live GitHub status is
inferred. [Reported CI evidence](../docs/ci-results-2026-10-19.md).

Two original GIL binaries and the new shared-runtime observations have scoped
same-host recovery evidence. Complete original runtime, all FT asset custody
and whole-host recovery remain unestablished. Source selection is always the
parent `cpython/` gitlink; measured baseline/integrated revisions stay fixed
in their reports, not relabelled as the selected current checkout.

## Documentation audit outcome

[A-000003](records/audits/A-000003/record.md), sealed 21 October 2026 at
16:32:59 UTC, independently closes all five A-000002 documentation findings
at input `eaa0b065922a08c6e51c79cc8856e82433fbcf48`: current-status routes,
GIL follow-up/register, historical access disposition, campaign-signal
qualifications, and nominal-path exceptions. W1–W4 dispositions are satisfied
within their stated scope. No new findings were raised. This is a bounded
documentation verdict, not whole-project VP conformance or technical acceptance.

All six [A-000001 historical findings](records/audits/A-000001/ACCESS.md)
remain open. Allocation/rollback/join and other [technical landing issues](../docs/OPEN_ISSUES.md)
are not documentation repairs and remain unchanged.

The documentation task is complete: current-view checks passed and the
handoff revision `da6a17c58a81f76e2648b6a41632d9cb2bea04c4` was recovered
and byte/mode-compared for all 31 changed tracked files. The tested same-host
bundle and restoration route are in DOC-000001. Reports, evidence and repairs
are locally committed; nothing was pushed by this task.

Next owner decision: Alex chooses exact hosted job/source verification, the
conditional independent-PGO-build stage, another unresolved investigation, or
reviewer handoff. New PGO builds, GC diagnostics or code changes are not
commissioned by this record. Alex retains remote pushes. No benchmark is running
for this documentation task.
