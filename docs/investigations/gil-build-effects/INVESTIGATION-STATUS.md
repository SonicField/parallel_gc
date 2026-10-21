# Investigation: GIL build effects after unused-code cleanup

Status: owner approved comparison of recovered executables in a shared current runtime; preparing and verifying that runtime before the focused measurements.

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
