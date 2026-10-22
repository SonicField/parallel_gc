# Verifiable Practice: documentation and investigation records

Start with [current state](STATE.md), then the [investigation and choice
register](REGISTRY.md). The register links existing records where they live;
it does not duplicate their raw evidence or replace their original protocols.

The completed documentation reconciliation is recorded under
[DOC-000001](records/changes/DOC-000001/record.md), authorised by Alex Turner.
Its explanatory repairs use level D of [VP standard 1.1](https://github.com/SonicField/verifiable-practice/blob/c100fbd7f7a735e8216156223c59aa97f9ad8fa6/standards/project-records.md).
That level describes this task, not the risk of collector implementation or
performance experiments. No whole-project record-conformance adoption,
all-source lifecycle coverage or release acceptance is claimed.

The current [records reform](records/changes/REC-000001/record.md), authorised
22 October, applies [VP standard 1.2 §6.1](https://github.com/SonicField/verifiable-practice/blob/b068e9cbe245bcdc039993020befb594a795bff3/standards/project-records.md)
prospectively to this bounded record scope. It does not recertify earlier audits
against a different standard. The pin was read locally; its hosted availability
was not checked. Changed retention controls use level C and require the declared
fresh Project Audit; explanatory navigation remains D.

## What must be kept

| Role | Examples | Requirement |
|---|---|---|
| Required experiment records | Source/patches, toolchain/dependency specifications, commands, configurations, workload inputs, raw measurements and failures, analysis and environment limits | Preserve what permits examination and supports repeating the experiment; disclose missing support. Binary-format measurements are still records. |
| Provenance-only identities | Executable digests and build IDs | Identify what ran. An identifier alone creates no duty to keep the executable. |
| Working resources | Builds, installed tools, virtual environments, caches and containers | Normally disposable after ownership/active-consumer and required-record checks. This reform authorises no deletion. |

A genuine exact-byte duty needs a stated purpose, consumer and retention period,
such as release delivery or forensic replay. There is no default duty to archive
a machine, compiler, container or binary. Mixed archives must retain their unique
records before build products can be discarded. Missing raw data is not excused
by this distinction. The reform record gives the family-level dispositions and
unresolved custody limits; it does not inventory every temporary file.

Recorded recipes, tested reconstruction, repeated experiments and byte recovery
are separate claims. Keeping an executable does not reconstruct its environment
or reproduce its result. The GIL record's dated successor applies this distinction
to its earlier blanket retention rule without rewriting the original entries.

## Reading the trace

Each register entry identifies the question, retained/rejected choice or
unresolved outcome, and its supporting record. Those records identify source,
commands, measurements, failures and limits. Original authority sometimes
survives only as attributed prose; a new index does not authenticate it.
Use the record's immutable commit/path when reviewing an earlier conclusion,
not the current branch tip as a substitute for its measured revision.

[A-000002](records/audits/A-000002/record.md) is the initial fresh-context
documentation assessment. [A-000003](records/audits/A-000003/record.md) is
the distinct fresh-context successor: it independently closes all five
documentation findings at `eaa0b065922a08c6e51c79cc8856e82433fbcf48` and
confirms W1–W4's bounded dispositions. No new finding was raised. Its verdict
does not close the underlying technical/historical limitations.
[A-000001](records/audits/A-000001/record.md) is the older, inconclusive project
audit. Read its [access/disposition companion](records/audits/A-000001/ACCESS.md)
before following links into its untracked local legacy packet. All six old
findings remain open; this documentation work does not reconstruct missing
history or close technical landing gates.

[A-000004](records/audits/A-000004/record.md) is the fresh VP 1.2 records-reform
assessment at `7a9ebfb247d3709d4b59e45b4a341c850f54748c`: conformant within
that changed-control scope, no new mandatory findings. It supersedes only the
prospective blanket binary/environment-retention implications of A-000001/F-004
and F-005. Their genuine access/custody conditions and the other four findings
remain open. Alex retains C-stage acceptance; this is not whole-project conformance.

## Custody and change limits

Authoritative records are preserved in parent Git history. The documentation
audit candidate has a tested same-host bundle, identified in DOC-000001 and
A-000002. The GIL follow-up separately identifies recovered-binary and runtime
stores, historical manifests and tested archive recovery. These are scoped
recovery checks, not portable rebuilds or whole-host protection.

The repaired handoff revision `da6a17c58a81f76e2648b6a41632d9cb2bea04c4`
has a new tested documentation bundle; DOC-000001 identifies its digest,
restoration route and complete changed-file comparison. No original packet,
failed run or workspace is pruned here. Changed
evidence, document meaning, owner authority or custody triggers review; D
documentation does not acquire a calendar expiry or renew underlying C
experimental conclusions. Source/benchmark changes and new measurements need
their own authority and verification, not permission inferred from this index.
