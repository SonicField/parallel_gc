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

## Documentation audit work in progress

[A-000002](records/audits/A-000002/record.md) has five open documentation
findings. Campaign-signal qualifications (F-004), nominal-path exceptions
(F-005), and historical access dispositions (F-003) are repaired locally,
pending independent successor review. Current-status reconciliation and the
new register's reviewer routes (F-001/F-002) are being completed. The worker's
four gaps are mapped to the same work in DOC-000001.

All six [A-000001 historical findings](records/audits/A-000001/ACCESS.md)
remain open. Allocation/rollback/join and other [technical landing issues](../docs/OPEN_ISSUES.md)
are not documentation repairs and remain unchanged.

Next: finish the explanatory status updates, verify links/factual support and
unchanged source/benchmark bytes, then commission a fresh successor audit at
the repaired revision. New PGO rebuilds, GC diagnostics or code changes are
not commissioned by this record. Alex retains technical decisions and remote
pushes. No benchmark is currently running for this documentation task.
