# Investigation: GIL build effects after unused-code cleanup

Status: all four focused ABBA blocks completed and verified. The original large enabled increases did not recur. Cause remains unresolved; no collector change or new build experiment is justified by this result alone.

Records clarification, 22 October: the [dated retention successor](#22-october-2026--evidence-roles-and-retention-successor)
separates required experiment support from executable identities and working
runtimes under VP 1.2. Historical recovery checks below prove byte recovery,
not reconstruction of the original environment. The four new blocks repeat a
measurement with a different shared runtime, not an independently rebuilt pair.

## Latest findings — 21 October 2026

The original executable bytes were measured with the same reconstructed runtime, unchanged benchmark programs and rigorous parameters. Each row compares integrated versus baseline **with the same GC policy**, not parallel versus serial. Positive percentages mean more execution time.

| Policy / repetition | `btree_gc_only` time change | BTree halves | `connected_components` time change | NetworkX halves |
|---|---:|---|---:|---|
| Disabled / first | +9.24% | +16.77%, +0.91% | +0.09% | −0.39%, +0.60% |
| Enabled / first | +0.88% | +5.75%, −3.89% | −1.77% | −1.83%, −1.71% |
| Enabled / second | +2.41% | −0.68%, +5.59% | −2.05% | −5.19%, +1.33% |
| Disabled / second | −1.82% | −1.35%, −2.28% | −2.37% | −4.03%, −0.67% |

The earlier enabled increases (+12.70% BTree and +6.48% NetworkX) did not reproduce in either new block. BTree's two enabled block averages are still positive; all four enabled halves must remain visible because their directions oppose within each block. The disabled BTree control also reverses direction across repetitions. These results do not establish equivalence, a stable smaller regression, or a speedup attributable to cleanup.

The strong interpretation that this pair has a consistently large enabled penalty under the declared shared runtime is not supported. Run conditions, adaptive trajectories or runtime context remain plausible explanations for the earlier observation. This experiment cannot distinguish them, or exclude PGO/build differences and runtime–binary interactions. The original runtime was not recovered; the changed runtime is therefore a limit on generalisation, not proof that it caused the original result. No timed-GC attribution is made for NetworkX.

Next owner decision: whether this bounded non-reproduction warrants further investigation. Independent PGO rebuilds or instrumented GC diagnostics require the stage-3 protocol/budget gate below; neither was run. No implementation fix is proposed. Historical results and all original warnings remain retained.

Evidence and restoration locators are in the final completion entry. Earlier entries below preserve the observations and gates at their stated stages; statements about pending work there are historical, not current status.

Author/operator: Codex, root session `01a0d2dd-cae0-7453-8afb-9a483d2d280a`.
Created: 2026-10-21T13:30:57Z.
Owner: Alex Turner. Goal: explain the GIL `btree_gc_only` and `connected_components` execution-time increases without changing collector behaviour.

## Authority and assurance

Alex's instruction in the current conversation: “Got you - so yes - the performance hit we are seeing in the GIL could be a build change. I would like to see you using the full version of verifiable-practice here and move very carefully.” This is an attributed transcription captured when this record was written; the original message timestamp is unavailable here.

Method: VP Project Records Standard 1.1, at `SonicField/verifiable-practice` commit `eae88cffddf53cb3a5f32eb7c2b371447d5f725d`, `standards/project-records.md`, with its project-records and investigation playbooks. This is a bounded investigation, not a declaration that the whole parallel_gc project conforms. The existing A-000001 audit remains inconclusive and its six findings remain open. Its original standard and snapshot are not replaced by this plan.

Consequence level C: a wrong attribution can cause significant rebuild/rework or motivate a harmful collector change. This combined record holds rationale, protocol and later identified outcomes; the current standard does not require separate hypothesis/build/run files at C. No implementation, change to workloads, collector design, atomics, barriers, adaptive policy or thresholds is authorised by this plan. Remote writes remain Alex's responsibility. Commit this plan locally before experimental work.

Alex confirms the hypotheses and first measurement stage before execution. A fresh independent Project Audit is required before claiming conformance for an adopted project scope; self-checks do not close A-000001. This investigation makes no release, conformance or performance-acceptance decision. Any proposed collector repair is a separate owner decision.

Review by 2026-10-28T13:30:57Z, or earlier on changed source/toolchain/dependencies, contradictory results, lost evidence, interference or owner direction. This short horizon reflects provisional performance attribution and the existing custody loss, not expiry of historical measured values. Codex maintains the record; Alex controls continued scope and acceptance.

## Observations and limits

Historical parent result revision: `695070d`, `benchmarks/results/pyperformance/repaired-source-abba-2026-10-19/`; root summary at `f8261bc:README.md`. CPython baseline is `c67363fa59543ef5d572383af927f1cff88514a1`; integrated source is `388fd5bb46fdda6b464db566faf818505c3d6eef`. These are not the current checkout `b91445e0b95454e32b982770f6e3c864beb5a528`.

| Result | GIL enabled source time change | Halves | GIL disabled source time change |
|---|---:|---|---:|
| `btree_gc_only` | +12.70% | +17.25%, +8.16% | −5.12% |
| `connected_components` | +6.48% | +8.49%, +4.46% | −3.00% |

These are two source builds with the same runtime policy in each campaign. Enabled and disabled campaigns ran sequentially; subtracting their percentages does not identify activation cost. Two halves from one binary pair do not measure rebuild variation.

The exact source diff has seven paths. GIL `Python/gc_parallel.c` loses three uncalled coordinator helpers; symbol searches at the baseline find only declarations and definitions. `Python/gc.c`, the GIL parallel/deque/random-walk headers and list/dict/tuple implementation files are unchanged. Modules/gcmodule.c verifier changes are conditional on FT, parallel GC and debug. Most cleanup is FT-only. Makefile adds header dependencies. These observations do not establish identical generated machine code.

`btree_gc_only` builds a tree outside the returned timer and explicitly times `gc.collect()` with records/tree still reachable. It has 200,000 records, lists, tuples and user instances; it is not a timer for reclaiming an entirely dead tree. `connected_components` loads a module-global NetworkX graph before timing and measures `number_connected_components()`. NetworkX 3.4.2 performs BFS using adjacency dictionaries, visited sets and frontier lists. The commonality is a substantial live object graph, not identical containers, rooting, allocation or timed work. Automatic GC inside the NetworkX timed section has not been demonstrated.

The hook records collector configuration at teardown, not per-collection worker use. Saved enabled `btree_gc_only` runs have varying adaptive endpoints; `connected_components` endpoints are all four. This cannot show which workers ran during a sample or that its algorithm adapts incorrectly. No hypothesis is accepted from those endpoints alone.

The original build/driver directory is missing. Historical fingerprints and raw outputs survive; A-000001's packet reportedly retained the four executables. Recovery and current executable identity have not been tested. No regenerated binary can be called the original binary. The published NetworkX 3.4.2 wheel was read from pip's cache for source inspection, not installed into benchmark environments; equivalence to every original installed byte is not established.

## Hypotheses and refuting observations

1. **The increase follows a source-dependent generated-code difference.** Prediction: independent matched build pairs reproduce the enabled increases, beyond differences between builds of the same source. A result where the direction changes across build pairs or matched-source differences account for it contradicts the strong source-attribution claim. Unchanged active C logic does not exclude this hypothesis.
2. **The original pair differs because of PGO-training/build variation.** Prediction: independently trained builds of the same source produce relevant timing or generated-code differences. Consistently negligible matched-source differences combined with reproducible source-associated increases argues against this explanation for the observed magnitude. Code-size/profile changes alone do not establish timing causation.
3. **Run conditions or adaptive trajectories explain the original observation.** Prediction: repeated measurements of the recovered unchanged binary pair vary substantially in size or direction. Stable repetition weakens a transient-run explanation but does not distinguish a source effect from a persistent property of those binaries. Teardown worker endpoints are not evidence of a causal trajectory.
4. **A shared live-heap GC path accounts for both increases.** Prediction: a separately commissioned diagnostic records GC activity and attributes extra elapsed work to a shared collector phase in both. If NetworkX's timed interval has no GC activity, that refutes a direct timed-collection explanation, though earlier thread creation or other persistent runtime effects remain possible. Do not assume this hypothesis merely because the benchmarks contain graphs.

These hypotheses are not exhaustive or mutually exclusive. The first stage informs which discriminator is justified, not which collector feature to remove.

## Staged protocol and gates

### 1. Establish recoverable inputs — read-only first

Locate original binaries, build/configuration/training logs and dependency identities via the existing manifests and Git objects. Verify any recovered binary against its recorded hash. Restore outside the project search tree, preserving the originals; name the recovery scope and missing files. Do not copy old audit packets/source into the working tree. Define a separate recovery replica and actually test restoration before relying on future sole-copy evidence. No pruning or deletion.

Budget: one bounded inventory/recovery pass, at most two hours of active work. If binaries, original dependency context or usable configuration cannot be recovered, stop the historical-repeat stage and report exactly what is missing. A fresh-build experiment then requires a new labelled baseline, not substitution for the original.

Exit: identified recoverable inputs, explicit losses and a reproducible command plan. Alex confirms the first execution stage and its hypotheses. No benchmark starts before this gate.

### 2. Repeat only the two affected benchmarks

If stage 1 succeeds, use the recovered original GIL binaries with the original supported dependency implementations and upstream rigorous parameters. Select `btree_gc_only` and `networkx_connected_components`; retain result label `connected_components`. Do not shorten loops, calibration, warmups, values or minimum time. Keep the original benchmark programs/data unchanged.

Proposed bounded batch: two complete source ABBA blocks per runtime policy, enabled and disabled, each with baseline/integrated/integrated/baseline order. Alternate which policy runs first between blocks. This is sixteen focused suite invocations, not sixteen full-default suites. Declare exact commands, output paths and starting environment before the first invocation. Analysis must support this explicitly focused selection; the existing full-100-program reader must not be weakened to accept partial campaigns.

Retain every original program result, warning, execution record and failed attempt. Record source/binary hashes, compiler/configuration, dependencies, actual GIL/collector state, time, affinity/NUMA binding and competing load. Analyse each named result and each block/half separately, equal-weighting source legs. Null time ratio is 1. No arbitrary universal noise floor, post-result exclusion, pooled-worker claim of independent source replication, or neutrality claim from an aggregate.

Budget ceiling: sixteen invocations and eight hours elapsed after preflight; stop earlier on failed state/identity checks, dependency mutation, invalid selection or significant interference. Preserve output and label the outcome incomplete/inconclusive rather than rerunning until it looks consistent. Exact resource availability and evidence-store location must be fixed at the execution gate.

Exit: report whether the increases recur for this unchanged binary pair, with all blocks/halves and uncertainty. This stage cannot establish whether source cleanup caused them.

### 3. Discriminate build from source — conditional, not yet commissioned

If repetition justifies it, propose independent PGO+LTO rebuilds: two builds per source, identical declared compiler/configuration/training recipe, separate clean build/profile directories. Compare within-source build variation as well as source pairs. Do not reuse stale profile files or treat a second invocation of one executable as a second build. Separate build-failure/retry identities and preserve profile-use warnings.

Before executing, fix the build/run budget, pair/order selection, generated-code comparison units, analysis and refuting criteria in a dated amendment approved by Alex. Sharing profiles across changed source needs a demonstrated valid mechanism; it is not assumed. ASM/perf diagnostics follow reproduced effects and an explicit diagnostic protocol. Neither rebuilding nor profiling authorises code changes.

Exit: evidence that distinguishes the proposed causes, or an explicit inconclusive result. Report what the tests cannot distinguish. Any repair needs a separate plan, tests, authority and atomic commit.

## Attempt log and current verdict

Pre-plan inspection only: exact Git diffs/reference searches, benchmark scripts, archived leg arithmetic and runtime metadata were read. No new benchmarks, builds or collector changes ran. The original installed NetworkX path was absent; a raw GitHub source fetch returned HTTP 403. A cached published 3.4.2 wheel was then inspected without installation. These source-retrieval attempts are not measurements or proof of original environment recovery.

Current verdict: **inconclusive** about the cause. There is a shared live-heap characteristic, but no established shared timed collector phase or source-versus-build attribution.

Next action: bounded input-recovery inspection; then return the proposed first measurement command and recovered identities to Alex for confirmation. On interruption, no benchmark process from this investigation needs termination. Preserve this plan's committed version and append later outcomes rather than rewriting prospective criteria.

### 2026-10-21T13:32:24Z — recovery inventory check

Plan baseline: parent commit `cbf5880`. Read-only check used `/usr/local/bin/python3` to load `vp/artefacts/A-000001/input/inventory.json`, select entries whose original path is below `/tmp/parallel-gc-benchmarks-complete-20261016-ntQPAW` and ends in `/python`, then compare SHA-256 of each retained file against the inventory. Files were read directly; no binary was executed or restored.

Attempt 1 printed four matching hashes, then exited 1 with `KeyError: 'original_path'` on a different inventory entry. Its unconditional dictionary lookup was wrong. Attempt 2 used `get('original_path', '')`, asserted exactly four selected entries, checked all four digests and exited 0. The correction changed only this read-only selection check, not evidence or benchmark inputs.

Retained directory: `vp/artefacts/A-000001/input/external/parallel-gc-benchmarks-complete-20261016-ntQPAW/`.

| File below retained directory | Recorded and observed SHA-256 |
|---|---|
| `baseline-gil/python` | `cc88a007f907335d9e480a8d3b926788216dfcfc3cf4d371638bb86f1e538b0b` |
| `candidate-gil/python` | `2df758725bac29198fa0341fe9a60594814dcd59acd24e9e6af2bfd9a6d230f9` |
| `baseline-ft/python` | `ee7c932bfdf6e76e8c5d18a2331a0a473a130a6c9500c24f0700c10c471f35d5` |
| `candidate-ft/python` | `c51db4dee5757e789cc208162bc32d70e9d8e79834a07cc0eed63888cecd19c1` |

Observation: the binaries are present and identifiable, despite loss of their original temporary directory. This does not establish a usable restored Python prefix, dependency environment, independent replica or full historical build recovery. A-000001/F-005 is not closed. Next: check retained configuration/stdlib/native-module/environment inputs before proposing any benchmark command. The cause of the performance increases remains inconclusive.

### 2026-10-21T13:41:15Z — runtime recovery limits and verified replica

Authority: current instruction to follow this investigation and report findings. Prior goal-turn work was progress: committed protocol and verified original binary identities. This stage is new recovery evidence, not a repeated status report or a benchmark execution.

The two original GIL virtual environments still have directories, but both have lost `bin/python`, `pyvenv.cfg` and `lib/python3.16/site-packages/networkx`. Some repaired packages remain. The original native build/dependency prefix and detached source worktree paths are absent. Git worktree registrations report those original source locations as prunable; nothing was pruned. Exact source Git objects remain accessible, including each revision's `Lib/os.py`; recovering source is not recovering compiled native modules.

Inspection of the retained inventory found 90 entries from the original complete-build root, including executables, configuration/build/preflight logs and `builds.sh`, but zero `.so` files and no original virtual-environment files. The build preflight identifies native `_decimal` under the missing prefix and libmpdec 2.5.1. `readelf -d` on the preserved baseline GIL executable identifies libc/libm and the original private-library RPATH; it is a read-only ELF check, not a successful runtime preflight. Raw original program results identify the now-incomplete virtual environment as the executable for both affected benchmarks.

Checks: direct `ls` of named original paths failed as missing; inventory JSON selection completed; `git cat-file -e` for both source locators passed. The checks establish absence from these named paths/retained packet scope, not absence of every possible host backup. No exhaustive host search or remote query was performed.

Created recovery storage outside the project tree: `/home/alexturner/local/parallel-gc-gil-recovery.iJz6nj/`. It contains the two original GIL executables and, for each, `Makefile`, `binary.sha256`, `build.log`, `configure.log`, `preflight.json` and `pyconfig.h`, plus ownership/custody README and SHA-256 manifest. Original audit inputs are unchanged. The original project/audit tree was not recursively copied or added to Git.

Replica commit: `091100291cfb7ff83f48ba52c8e01f8e7d0d2818`. Self-contained `RECOVERY.bundle` SHA-256: `1bf4cead53632bb6209063cc8960309fa86d4b98ea4ba48976542548fe156d9f`. `git bundle verify` passed; a fresh `git clone RECOVERY.bundle restored` checked out that commit. Clone printed `error: bundle-uri operation not supported by protocol`, but completed; the actual restored revision, clean tracked state and content checks subsequently passed. This diagnostic is retained rather than hidden.

In `restored/`, `sha256sum -c SHA256SUMS` passed for all 15 covered files. All fourteen restored original-input files were also compared byte for byte with their retained audit originals using `cmp`, with no differences. This tests actual recovery of the declared selection, not merely presence of hashes. No recovered Python was executed. All copy, commit, bundle, clone and verification steps completed in this bounded recovery pass; there is no live benchmark process to wait for.

This is a same-host recovery replica: it protects the selected binaries/provenance against project working-tree loss, not whole-host loss. It does not preserve missing native extensions, a usable standard-library prefix, all dependencies or an independently authenticated historical environment. It is not independent assessor closure of A-000001/F-005 or project conformance.

**Stage 1 finding:** executable bytes are recoverable, but a complete original runtime environment is not established. Stage 2's unchanged-environment gate is not satisfied. Reinstalling or recompiling missing inputs must be called reconstruction, not an original-environment repeat. No historical comparison, fresh PGO build, native-module rebuild or benchmark was started.

**Next owner decision:** approve a separately labelled matched-runtime reconstruction around the recovered executables, or approve fresh controlled builds with new identities and an explicit within-source build-variation comparison. Either requires a dated protocol amendment with actual inputs/resource budget before execution. Neither permits changing collector behaviour. The existing slowdown observations remain valid for their recorded pair; their cause remains **inconclusive**.

### 21 October — prospective shared-runtime protocol amendment

Alex changed the recovery requirement: “An alternative is to use the recovered binaries in the new runtime. If they show a performance difference we know the runtime is not the issue. We do not require the previous runtime.” He then explicitly authorised execution: “please go ahead with this experiement - tracking using vp”. These are current-conversation transcriptions; their original UTC message timestamps are unavailable. This supersedes the requirement to recover the old installed runtime, not the evidence/provenance requirements or the prohibition on collector changes.

Interpretation fixed before execution: recurrence under a shared current runtime shows that the old runtime is not necessary to reproduce the difference. It does not exclude a runtime–binary interaction or distinguish original PGO variation from source-dependent generated code. No such stronger conclusion will be reported.

New owned workspace: `/home/alexturner/local/parallel-gc-gil-shared-runtime.x3qHNE/`. Keep both recovered executable hashes unchanged. Standard-library input is `SonicField/cpython` commit `b91445e0b95454e32b982770f6e3c864beb5a528`, subtree `Lib`, exported outside the project. Native extension input is this project's existing GIL release runtime at `build-upstream-gil-release/build/lib.linux-aarch64-3.16`, with `Py_DEBUG` and `Py_GIL_DISABLED` undefined and parallel-GC support compiled in. Its historical module-build provenance is incomplete; record current module bytes rather than claim they are the original modules. The same module directory and stdlib bytes serve both executables. Fingerprint all relied-on inputs before and after measurements.

Create isolated baseline/candidate installed-layout prefixes using the recovered executables, each pointing to the shared stdlib; then isolated virtual environments. Install the same `pyperf==2.10.0`, `networkx==3.4.2`, `psutil==7.2.2` and current project hook package into both. The NetworkX wheel/program/data are unmodified. Dependency installation is preparation only; no installer runs during measurement. Verify native imports, actual runtime GIL/collector modes, positive and negative hook controls, package inventories, executable hashes and the exact two-program selection before the first timed campaign. Failure of any preflight stops measurements; retain failed attempts. This does not rebuild either collector binary or modify existing runtimes.

Execution retains stage 2's two ABBA blocks per policy: block 1 disabled then enabled; block 2 enabled then disabled. Each source ABBA is baseline/integrated/integrated/baseline. Run sequentially with original upstream rigorous options, timeout 300, affinity 0–31 and NUMA node 0. Exactly two original programs are selected; no full-default neutrality claim is made. Sixteen focused suite invocations maximum, eight-hour measurement ceiling, and at most two hours of active preparation before escalation. Readiness probes are execution checks, not performance samples. Analysis/recording work runs on CPUs 64–71 while measurements use 0–31.

Freeze preparation/controller commands and actual fingerprints before launch. Use the existing prepared runner unchanged. A separately scoped analysis invocation must verify two programs/two named results explicitly; do not relax the full-default reader's defaults or mix this data with historical measurements. Preserve all four raw legs per block, per-program files, hook state, absolute means, both halves, warnings, package/input identities and labelled failed attempts. No causal/neutrality verdict follows from a geometric mean.

### Shared-runtime preparation attempts 01–03

Preparation 01 exited 126 because the preserved audit captures lack executable permission. Only the new working executable copies were given user-execute permission; their bytes remain unchanged. Preparation 02 exited 1 on missing `math`: copying the native build directory with preserved relative symlinks left those links pointing outside the new prefix. Preparation 03 preserved that directory and copied dereferenced module contents; math then imported, but zlib was absent from the selected older release runtime. A separate inspection command used the wrong log working directory once; the correct absolute log was then read. All logs and failed preparation directories remain in the owned workspace; no timed sample ran.

Prospective correction before attempt 04: use the complete native-module directory from this project's `build-pyperformance-gil/build/lib.linux-aarch64-3.16` for both recovered executables instead of the older release directory. It contains zlib; retain/fingerprint its actual bytes and configuration, with the same incomplete historical-provenance limitation. This changes shared-runtime preparation, not either executable, benchmark code, rigorous parameters or a post-measurement selection. Check the new runtime fully before measuring.

Preparation 04 started both binaries successfully and installed matching required versions. It nevertheless failed the clean-startup requirement: pip's build from the live support directory included an obsolete `sitecustomize.py` from ignored build output. That file imports an absent legacy function and produced startup warnings. A zero installer exit is not a passing readiness result. Before preparation 05, preserve that failed file and reinstall the support package from a clean Git export of the four tracked source files; no tracked package code is changed. Both target environments and the new driver use that same exported input. Reject any remaining sitecustomize import/warning before measurement. Existing ignored build files are not removed or modified.

Preparation 05 removed the obsolete installed startup file in the baseline environment using the clean package, then failed the required NetworkX import because the donor runtime lacks `_bz2`. NetworkX imports bz2 during module initialization even though the benchmark data is gzip. No programs or dependencies are omitted to accommodate this failure. Before attempt 06, build only the shared `_bz2` support extension from the unchanged CPython `_bz2module.c` and current headers, using the recovered GIL configuration header, GCC and the host libbz2 1.0.8. Obtain the matching development header into the owned workspace through the configured package repository, without installing system packages. Record source/header/library/compiler/extension identities and exact commands. This support-module preparation does not rebuild or alter either recovered interpreter or collector. Both executables must pass compression round trips and the original NetworkX import after the same extension is installed.

### Shared-runtime readiness and frozen launch

Preparation 06 compiled the shared native bz2 extension, passed compression/import checks and matched package inventories for both recovered binaries. Its final driver-creation command failed because `python3.12` was not on PATH. Attempt 07 created the isolated driver using `/usr/local/bin/python3` (3.12.15+meta) and completed installation. The native extension SHA-256 is `3aea7ef25336f37a14920172c69babb56e2a4981f893f028078e3ad58be62522`; header/RPM/library/source/config hashes and exact compile command are in `native-bz2/inputs.sha256`, `prepare-06.sh` and `preparation-06.log`. System packages were not installed. The original recovered executable hashes still match.

`readiness.sh` completed all four baseline/candidate × disabled/enabled execution contexts with the two original programs and unchanged graph sizes. These debug-style execution probes are not performance evidence. Strict per-run Boolean GC/GIL/hook and BTree workload checks pass. The prepared-runner tests pass 12/12, including a zero-hook negative control. Both recovered GIL binaries pass 36 hook/support tests with one FT-only skip each. Readiness logs contain no startup-error/traceback patterns. Installed versions match: NetworkX 3.4.2, pyperf 2.10.0, psutil 7.2.2, pip 26.2.1 and the clean-export project hook 0.1.0.

Focused analysis tests were written before the new helper: the first run failed because the helper did not exist, then all ten tests passed, including null/opposing-half arithmetic, wrong mode/GIL/Boolean/workload, missing hook and corrupted digest. The helper requires exactly two programs/two results, all four source legs, original binary hashes, unchanged rigorous options, all raw/combined/program digests and per-run state. It does not change the existing full-default analysis reader.

The first source-fingerprint check failed on Git's CRLF export of `Lib/ctypes/macholib/fetch_macholib.bat`. The successor check verifies the explicit `eol=crlf` Git attribute and canonical blob, while retaining actual exported-byte hashes; no file bytes were rewritten. Installed package-byte comparison found only generated pip/pyperf wheel RECORD differences caused by prefix-specific console-script shebang hashes. Both complete inventories are retained; equivalence excludes only those RECORD files and pyc/cache files, not package source or native bytes. All other non-cache installed package bytes match. The frozen prelaunch fingerprint (`inputs-prelaunch-02.json`) SHA-256 is `0f3ba80243520ad5c44da914fabada1ca184244df041f32cd8a7a7b27a33d7c1`; source, native and package identities are separately enumerated.

Actual command: `timeout --signal=TERM --kill-after=30s 8h taskset --cpu-list 64-71 bash controller.sh`, from `/home/alexturner/local/parallel-gc-gil-shared-runtime.x3qHNE`, logging to `controller.log`. Controller SHA-256: `8c0ce1c59aab47157dec6625eea1ed023e0a81f649ba02f3aece8c266ce91646`. It runs the unchanged parent prepared runner sequentially, with source ABBA order and policies disabled/enabled/enabled/disabled. Each block uses `--benchmarks btree_gc_only,networkx_connected_components --run-style rigorous --affinity 0-31 --timeout 300`, NUMA CPU/memory node 0 and the two prepared virtual environments. The controller refuses changed before/after fingerprints. Analysis runs outside measurement affinity. Existing source checkout metadata in campaign records describes the current checkout, not the recovered executable's source; original binary hashes and version stamps identify the measured pair. Sysconfig comes from the shared runtime donor, so original PGO build provenance remains the earlier immutable records, not an assertion that donor metadata identifies recompilation.

Background service activity is captured before/after each block; exclusive ownership or an independently verified quiet host is not claimed. No other user's process is stopped. Timeout, dependency/state failure, input mutation or interrupted blocks remain incomplete/inconclusive and preserve all available outputs. No timed result is available at this prospective launch entry.

### 2026-10-21T14:11:22Z — first disabled block complete

Controller PID 2633521 advances under timeout PID 2633520 and terminal session 74149; completion monitor cell 1135 waits on that same session. The first complete block ran 13:55:58–14:11:22 UTC. All seven result/comparison digests, eight original-program files, four execution/package records, per-run state and before/after input fingerprints pass. BTree retains two measured run records/six values per leg; NetworkX forty/120, respectively, matching the original rigorous defaults.

The disabled source-control time changes are `btree_gc_only` +9.24% (halves +16.77%, +0.91%) and `connected_components` +0.09% (halves −0.39%, +0.60%). The BTree first candidate leg has substantial original pyperf variation warnings; no value or run was removed. This control result differs from the earlier campaign and does not establish a reproducible source effect. The enabled blocks and second disabled block are still required; no complete investigation verdict follows.

Raw campaign: owned workspace `results/01-disabled`; analysis `analysis-01-disabled.json`, SHA-256 `785211ed61129653658ac289d5fb08ddb747874770f0dde27b53b7589acc8b9e`. Campaign record SHA-256 `29cdd6d652d5c236a066f52e949da8255ed359b97faf0c51f09aba34135a1952`. First enabled block started immediately after verification. No source, runtime or workload change occurred between blocks.

### 2026-10-21T14:26:39Z — first enabled block complete

The first enabled block ran 14:11:22–14:26:39 UTC. Complete-program/leg/digest, explicit runtime state, package inventory, original-binary identity and before/after fingerprint checks pass. The saved rigorous run/value counts match the preceding block. Raw campaign `results/02-enabled`, campaign record SHA-256 `441c0b3af68b96db99c577e200ae3f87e3d0fc75ca48a18e926b40add9ae847a`, and `analysis-02-enabled.json` remain in the owned workspace.

Time changes: `btree_gc_only` +0.88% (halves +5.75%, −3.89%); `connected_components` −1.77% (−1.83%, −1.71%). This block does not reproduce the earlier +12.70%/+6.48% increases. BTree half-directions oppose; no stable effect or cause is established. The second enabled and second disabled blocks are still required. They follow unchanged inputs; the next enabled block started at this timestamp. No values were discarded.

### 2026-10-21T14:41:58Z — second enabled block complete

The second enabled block ran 14:26:39–14:41:58 UTC. The same strict state, selection, digest and package checks passed, and its before/after fingerprints match. Campaign record SHA-256: `a6ac9a51a50122b7008b815438944a3645f2ad5f128fcb8b88030d636d131840`; raw campaign `results/03-enabled` and readable `analysis-03-enabled.json` remain in the owned workspace.

Time changes: `btree_gc_only` +2.41% (halves −0.68%, +5.59%); `connected_components` −2.05% (−5.19%, +1.33%). Neither enabled block reproduces the original magnitudes. Both BTree blocks have opposing half-directions, so their positive block averages do not establish a stable regression. NetworkX has lower block averages in both repetitions, but its second block also has opposing half-directions. These are descriptive observations, not equivalence or a causal attribution. The final disabled control started immediately; no inputs or samples changed.

### 2026-10-21T14:59:12Z — final control, checks and evidence custody complete

The final disabled block ran 14:41:58–14:57:20 UTC. Controller session 74149 completed with exit 0; all four blocks passed their declared checks. Measurement elapsed time was 61 minutes 23 seconds, within the eight-hour ceiling. All sixteen focused suite invocations completed; no full-default sweep, fresh interpreter build or collector edit ran.

Final disabled time changes: `btree_gc_only` −1.82% (halves −1.35%, −2.28%); `connected_components` −2.37% (−4.03%, −0.67%). Campaign SHA-256 `fd08978916df2175471030abcd8274df022d4a9aa94b4fbe9caa7a557bec8f5b`; final readable analysis SHA-256 `fb814e50536a1ecf61cb33b6af3351d3be7d20401adf017e90684a223e8ac39c`.

The strict focused reader was rerun against every completed campaign and its output compared byte for byte with every saved analysis. All checks pass, including raw/program digests, actual policy/GIL/hook state, packages and selection. All four before/after fingerprints match the frozen starting inputs. Its ten tests pass again. A separately written `crosscheck.py` reads raw JSON without importing that reader and recomputes every leg mean, block ratio and both halves; all eight named-result rows agree. It also records absolute sample standard deviations and counts. These are operator self-checks, not an independent assessor audit or independent build replication. Arithmetic output SHA-256: `8635449f67d4f7bbaadee317f0651007be1e33e52a8ed018b244df8c1c2ce488`.

Equal-weight leg means determine the block ratio: `(candidate leg 2 + candidate leg 3) / (baseline leg 1 + baseline leg 4)`. No samples or warnings were removed. BTree has six measured values from two run records per leg; NetworkX has 120 from forty. The first disabled BTree candidate leg has mean 92.50 ms and sample standard deviation 23.79 ms. The original rigorous defaults remain intact; these small BTree sample counts and observed variation constrain inference. Sample deviations are descriptive, not confidence intervals or independent-build variation. Captured host-load snapshots do not establish exclusive host ownership.

**External evidence store:** `/home/alexturner/local/parallel-gc-gil-evidence.2Cwhq4`, Git revision `c5987dd1cbcd6175e1b0d6ef12d4530f619df4bd`. `observations.tar.gz` contains all raw campaigns/per-program outputs, failed preparation logs, readiness, exact commands, fingerprints, analyses and test captures. SHA-256: `d8798ced8b8fdaac9b82fdfaf6e128c88e102e45344fa2d6a2ddeb6a22b3df9f`. `runtime.tar.gz` preserves the actual reconstructed runtime/native and installed package inputs, excluding pyc/cache files; SHA-256 `a364f9dea117245a1be7ab3da11506464db5b849f1835a8ab88c4e2458714fb4`. Its manifest declares intentional identical executable copies in separate working/virtual-environment prefixes. No product source or old audit packet was copied into the project worktree.

**Verified recovery replica:** `/home/alexturner/local/parallel-gc-gil-evidence-20261021-v2.bundle`, SHA-256 `6e8f58355b0cb542f6d7691f04c48b421d83153fad0a76ba6cab592e4a4a33bc`. Actual fresh clone into `parallel-gc-gil-evidence-restored-20261021-v2` completed at the exact revision; all four tracked evidence files were byte-compared with the store, and `sha256sum -c SHA256SUMS` passed in the restored checkout. Git printed `bundle-uri operation not supported by protocol`, but completed the clone and the subsequent checks passed. Initial replica revision `3d9f6cbe12ba8f68e9a13ab0791f5d1021871bbd` and its first bundle are retained; the successor corrects the README's initially inaccurate recovery filename and updates its digest. It does not alter either evidence archive.

This verifies recovery of archive bytes, not executing a portable restored runtime, authenticating action timestamps or surviving whole-host loss. The driver base interpreter and system libraries remain external dependencies. Original executable/build-record custody has its separately verified replica above. Retain the owned evidence for project life plus one year after retirement; no workspace, original input or old evidence was deleted. The final local project-record commit will also be bundled and byte-checked before handoff; its exact revision and check are reported with the handoff, avoiding a self-referential commit hash in this file.

**Scoped outcome:** the authorised recovered-binary/shared-runtime experiment is complete. Cause remains inconclusive. No project-conformance claim, closure of A-000001, source-repair acceptance, universal noise threshold or performance-neutrality claim follows. Stage 3 remains conditional and uncommissioned; Alex retains the next investigation decision. Existing review date and change/custody triggers remain in force. No benchmark is left running and no remote write was made.

## 22 October 2026 — evidence roles and retention successor

Authority: Alex instructed execution of [REC-000001](../../../vp/records/changes/REC-000001/record.md),
including correction of prior AI-written retention defaults. This current
level-C successor applies VP 1.2 §6.1 at
`b068e9cbe245bcdc039993020befb594a795bff3`. It does not rewrite the earlier
protocol, outcome, archive manifests or audit verdicts, and authorises no deletion.

Required records remain protected for project life plus one year after retirement:
original and new raw measurements, failed attempts, preparation/controller/
analysis scripts, source and dependency/toolchain specifications, build/run
commands, workload controls, configuration/fingerprint inventories, analyses
and environmental limitations. Alex is custodian and decision owner; experiment
reviewers and repeaters are the consumers. Source/build commands and native-decimal
preparation are linked from [build evidence](../../../benchmarks/results/investigations/integration-validation-2026-10-16/build-evidence/README.md);
dependency versions, patches and engine constraints are in the [repair plan](../../../benchmarks/dependency-repair/PLAN.md)
and [readiness records](../../../benchmarks/dependency-repair/full-readiness-evidence/README.md).
The frozen run protocol and preparation failures remain above, with the captured
scripts, inventories and raw outputs in the named observation store.

The blanket period no longer applies to recovered executables, installed
runtimes, compiled support modules, package caches or virtual environments merely
because they were used. Their hashes are provenance identifiers. They were
temporary resources for the completed diagnostic; no release, forensic,
exact-byte replay or external retention requirement was identified. This
supersedes that scope of the historical `README.md` defaults in
`/home/alexturner/local/parallel-gc-gil-recovery.iJz6nj` at
`091100291cfb7ff83f48ba52c8e01f8e7d0d2818` and
`/home/alexturner/local/parallel-gc-gil-evidence.2Cwhq4` at
`c5987dd1cbcd6175e1b0d6ef12d4530f619df4bd`, and the blanket wording in the
21 October completion entry. Those revisions remain preserved. Actual external
obligations discovered later require an explicit purpose, consumer and period;
this successor does not waive them.

The existing observation archive is a **mixed container**: index inspection
found raw JSON/logs and scripts alongside a bz2 RPM, extension, header and
documentation. It stays intact here. Future separately authorised cleanup must
first retain its required records and any unique configuration support in a
recoverable location; the build products need not remain their permanent carrier.
The runtime archive contains installed environments and possible configuration
support. Header/index inspection, without extraction, cannot prove that all
required configuration has independent custody. Ownership, active consumers and
those record dependencies must be resolved before later resource disposal.

Reproduction status is specific: recipes and executed identities are recorded;
the original complete environment was unavailable; preparation of the different
shared runtime and its four measurement blocks actually ran on 21 October;
reconstruction from retained records on a clean environment is **untested**.
Selected archive/executable byte recovery was tested on this host. Neither that
check nor retained runtime bytes establish clean reconstruction, repetition of
the original result or host-loss protection. Base interpreter/system-library
dependencies and unverified off-host record recovery remain explicit limits.
No compiler, container or complete-machine archive is required by default.

This successor changes records, not the result or causal interpretation. The
original investigation's review date and stage-3 gate still apply. The changed
retention control requires REC-000001's independent audit before acceptance.
