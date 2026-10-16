> **Point-in-time external review.** Written by Claude (Opus 5.5) on
> 15 October 2026 at Alex Turner's request and added to the repository
> unchanged except for this note and the artifact paths, which now point to
> `benchmarks/results/investigations/claude-scaling-2026-10-15/`. File paths,
> line numbers and document names refer to the repository as it was then
> (parent `333f4dd`, CPython `c67363fa59`); several documents it mentions have
> since been removed (they remain in git history at `724b74b`). Its recommendation
> below to keep an `archive/` directory was not adopted: git history already
> preserves superseded documents.

# Parallel GC for CPython: frontier assessment and scaling findings

Date: 15 October 2026
Subject: `SonicField/parallel_gc` parent at `333f4dd` (working tree with
uncommitted CI changes), CPython fork at `c67363fa59`, based on upstream
`333071231d3a`.
Host: 72-core Neoverse-V2 (AArch64), single socket, Linux.

## How to read this document

Each claim carries one of these labels:

- **[Measured]**: I ran it; the raw data are in
  `benchmarks/results/investigations/claude-scaling-2026-10-15/`.
- **[Source]**: verified by reading or grepping the source at the stated revision.
- **[Repo]**: taken from the project's own documents or results; I did not
  reproduce it.
- **[Inference]**: follows from the evidence but has not been tested directly.
- **[Judgement]**: an assessment, not a fact.

Section 9 lists the corrections to things I said earlier in the conversation
that produced this document.

---

## 1. Summary

1. **[Judgement]** The work is not slop, and it is not at the frontier of
   engineering quality. It sits upper-middle. It is at the frontier of *how far
   an AI-driven project can be carried* under rigorous human direction, not of
   *how good the result can be*.
2. **[Measured]** The free-threaded (FT) collector's scaling is fragile. In
   root propagation (`mark_alive`), the phase that dominates live-heap
   collections, effective parallelism depends on timing and heap topology.
   With a 1M-object live random graph reachable from a module global and 16
   workers, one thread does about 99% of the work and the collection is
   **0.61–0.83x the speed of serial** across runs. The same graph held by a
   frame local scales to **3.39x**.
3. **[Measured]** Two implementation defects explain this. Neither is a design
   limit:
   - **D1:** an idle worker exits for good after `2 × num_workers` failed steal
     sweeps, with no termination protocol;
   - **D2:** discovered work sits in a 1,024-entry private buffer that other
     workers cannot steal from until it overflows.
4. **[Measured]** A roughly 40-line textbook patch removes the dependence on
   holder placement (graph held by a global: 0.61x → 3.08x) and exposed 4.0x
   on a binary tree. It also **regressed fine-grained heaps by 3–7x**. The
   unpatched collector shows the same regression whenever its own stealing is
   active (lists held by a local: 0.62x). So making this robust needs
   specialist technique, not just a bug fix.
5. **[Source]** The code carries measurable dead weight. A release build
   produces **12 GC-related compiler warnings**, all from project code: 8
   unused functions and 1 unused variable in the parallel files, plus 3 unused
   helpers the project added to `gc_free_threading.c`. Ten of those 11
   functions are referenced in no build at all; the eleventh is used only by
   a debug test hook. Of five FT steal routines,
   two are reachable only from dead functions and one only from a debug test
   hook.
6. **[Judgement]** Verifiable Practice (VP) produced unusually honest
   evidence: dated provenance, ABBA runs, regressions reported up front,
   hypotheses labelled as hypotheses. It did not catch the scaling defect
   because no falsification test targeted the claim "the FT collector
   parallelises root propagation". The data needed to falsify it were already
   being collected.
7. **[Judgement]** There is too much documentation for a reviewer to absorb.
   It runs to 7,065 lines across 22 design and process documents, plus 2,405
   lines across 20 benchmark-result documents, against 10.7k lines of
   implementation.

---

## 2. Scope and method

I examined:

- the repository layout and history: 72 parent commits from 6 February 2026,
  and 26 fork commits on top of upstream;
- the README, the PEP-style discussion draft, `REVIEW_HANDOFF.md`, the source
  audit (`AUTIT-TODO.md`), and the FT lazy-pool benchmark analysis;
- selected parts of `pycore_ws_deque.h`, `gc_parallel.c`,
  `gc_free_threading_parallel.c` and `gc_free_threading.c`, and the property
  tests;
- the project benchmark driver `benchmarks/gc_perf_benchmark.py`, to check
  how it holds live data.

I did not read all 19k lines, audit correctness, run sanitizers, or measure
the GIL collector. The user asked for an assessment, not an audit; the defects
in Section 6 surfaced only while testing a performance claim.

---

## 3. Scale of the work

All figures **[Source]**, from `git diff --shortstat` against upstream
`333071231d3a`:

| Area | Files | Lines added |
|---|---:|---:|
| Whole fork diff | 56 | 19,278 (48 deleted) |
| Core: `Python/`, `Include/`, `Objects/`, `gcmodule.c` | 25 | 10,725 |
| Tests: `Lib/test`, `_testinternalcapi` | 11 | 7,986 |
| CPython `Doc/` | 2 | 87 |

The largest new files are `gc_free_threading_parallel.c` (3,943 lines),
`gc_parallel.c` (2,727), `test_gc_ft_parallel.py` (2,390) and the C deque test
harness `test_ws_deque.c` (1,995).

The integration surface is broad: both GIL and FT builds; mimalloc
abandoned-page enumeration; configure, Windows (PCbuild) and argument clinic;
fork handling; lazy creation of the worker pool with rollback on failure; and
persistent worker pools with an adaptive random-walk worker controller.

**[Judgement]** Getting this to pass ASan, TSan, fork tests and PGO+LTO ABBA
campaigns is long-horizon work that no single model session can do. That is
the strongest evidence against "slop".

---

## 4. Verifiable Practice: what it achieved and what it missed

### What it achieved

- **Honest negative results [Repo].** The handoff and benchmark analyses state
  the regressions plainly:
  - FT `ai_workload` sustained throughput −9.9%, with mean callback interval
    +116%;
  - pyperformance `float` −10.5%;
  - the adaptive controller loses to fixed 16 workers in every tested phase;
  - GIL collection-shape geomean is only 1.08x.

  Slop overclaims; this project underclaims.
- **Provenance [Repo].** Results record the executable SHA-256, configure
  flags, PGO training content, CPU affinity and exact revisions, and keep
  dated evidence separate from checkout identity.
- **Measurement protocol [Repo].** Fresh-process ABBA ordering, alternating
  serial and parallel modes on the same binary, and exclusions listed with
  reasons.
- **Epistemic hygiene [Repo].** Explanations not yet confirmed (the FT
  finalizer/BRC theory, the `float` graph-distribution theory) are labelled as
  hypotheses, not causes.
- **Fault reproduction before repair [Repo].** The audit records reproducing
  failures before fixing them, for example the exact-list mutation-sensitivity
  finding in `FT_CONTAINER_TRAVERSAL_OPTIMIZATION_PLAN.md`.

### What it missed

- **The headline capability claim was never falsified [Measured].** The README
  states: "The free-threaded collector parallelises root propagation,
  `update_refs`, `mark_heap`, and `scan_heap`" (`README.md:75`, also
  `CORE_DEV_DECISIONS.md:91`). Root propagation does not run in parallel when
  live data are reachable from module state (Section 7). The per-phase
  timestamps in `gc.get_parallel_stats()['phase_timing']` already show it. One
  run comparing `mark_alive_ns` at 2 and 16 workers would have exposed it. A
  falsification test for "phase X is parallel" needs per-thread utilisation
  or phase-time-versus-workers evidence, and none was defined.
- **The benchmark design hid the failure [Source, Measured].** The project's
  collection benchmark keeps 80% of objects live
  (`COLLECTION_SURVIVOR_RATIO = 0.8`, `gc_perf_benchmark.py:75`). It holds
  them in a function local (`keep_refs` in `run_batch`), which happens to be
  the placement where the defect does not show (Section 7.4). The benchmarks
  were careful about *statistics* but did not vary *where live data are
  rooted*.
- **Freezing the design limited the search [Repo, Judgement].**
  `AUTIT-TODO.md:15` says the "performance design, phase structure, atomic
  ordering, barriers, work distribution, and adaptive controller must not be
  changed as incidental parts of these repairs". Item 2 of
  `PERFORMANCE_INVESTIGATION_PLAN.md:117` forbids changing them "as a
  performance shortcut". That is a defensible rule for a fidelity port, and
  the project was largely porting an earlier implementation (see
  `PORT_FIDELITY_LEDGER.md`). But it pointed the method at *preserving*
  behaviour rather than *questioning* it. VP verified what was there; it did
  not look for what was missing.
- **Compiler warnings were not treated as evidence [Source].** The 12
  unused-function and unused-variable warnings are machine-generated signs of
  abandoned alternatives. Requiring a warning-clean build is a cheap falsifier
  for "this code is all live", and it was not applied.

**[Judgement]** VP succeeded at what it is designed for: making claims
traceable and keeping negative results visible. Its limit here was choosing
*which* claims to falsify. The highest-value claims are the ones the design
depends on ("phase X is parallel", "parallel is never slower than serial on
large heaps"), and those were not on the falsification list.

---

## 5. Documentation volume

**[Source]**

| Corpus | Files | Lines |
|---|---:|---:|
| `docs/*.md`, `docs/*.rst`, `AUTIT-TODO.md` | 22 | 7,065 |
| `benchmarks/results/**/*.md` | 20 | 2,405 |
| Core implementation (for comparison) | 25 | 10,725 |

The 22 documents include several that are *process residue* rather than
reference material: `HANDOFF_RECONCILIATION_PLAN.md`,
`CORE_DEV_SPRINT_READINESS_PLAN.md`, `PORT_FIDELITY_LEDGER.md`,
`TEST_FIDELITY_LEDGER.md`, `GIL_PORT_CALLSITE_MAPPING.md`, `PATCH_SERIES.md`,
`LAZY_POOL_CREATION_PLAN.md` and `FT_CONTAINER_TRAVERSAL_OPTIMIZATION_PLAN.md`.
Overlapping explanations of the same design appear in `ARCHITECTURE.md`
(1,006 lines), `DESIGN_POST.md`, `FORK_ARCHITECTURE.md`, `REVIEW_HANDOFF.md`
and the PEP-style draft (926 lines).

**[Judgement]**

- The writing is careful and hedged, but its volume is a cost in its own
  right. A CPython core reviewer has to dig the design out of the
  surrounding process.
- The hedging is so thorough that the documents rarely make a falsifiable
  positive claim. Where they do (the README phase list), the claim turned out
  to be conditionally false.
- Suggested consolidation:
  - one design document (architecture plus rationale);
  - one evidence document (current results with links to raw data);
  - one open-issues list;
  - move plans, ledgers and reconciliation records to an `archive/`
    directory.

---

## 6. Code quality and deduplication

### 6.1 Dead and test-only code

A release build (`--disable-gil --with-parallel-gc`, GCC 11.5) emits these
warnings from project code. **[Source]**; upstream comparison checked with
`git show 333071231d3a:Python/gc_free_threading.c`.

| File:line | Symbol | Status |
|---|---|---|
| `gc_free_threading_parallel.c:1030` | `propagate_worker_run` | Never referenced in any build |
| `gc_free_threading_parallel.c:2910` | `mark_heap_worker` | Never referenced in any build |
| `gc_free_threading_parallel.c:2716` | `update_refs_worker` | Never referenced in any build |
| `gc_free_threading_parallel.c:3048` | `par_disable_deferred_refcounting` | Never referenced in any build |
| `gc_free_threading_parallel.c:1095` | `clear_alive_bits_all_buckets` | Used only by a `Py_DEBUG` test hook |
| `gc_free_threading_parallel.c:439` | `pages_enumerated` | Unused variable |
| `gc_parallel.c:1854/1871/1885` | `_PyGCWorker_{Take,Drop}Coordinator`, `_PyGCWorker_CoordinateStealing` | Declared and defined, never called in any build |
| `gc_free_threading.c:136/178/377` | `worklist_clear`, `worklist_to_array`, `disable_deferred_refcounting_on_worklist` | Added by the project; absent upstream; never referenced in any build |

### 6.2 Parallel implementations of the same mechanism (FT)

**[Source]**

| Routine | Lines | Reached from |
|---|---:|---|
| `try_steal_work` (688) | 21 | `parallel_worker_run` → `_PyGC_ParallelMarkAlive` → only `_PyGC_TestParallelMark` (`Py_DEBUG` test hook, 1256–1368) |
| `propagate_try_steal` (1016) | 11 | only the dead `propagate_worker_run` |
| `mark_try_steal_work` (2893) | 14 | only the dead `mark_heap_worker` |
| `steal_batch_from_worker` (1412) | wrapper | **production** `propagate_pool_work` |
| inline loop in `mark_heap_pool_work` (1707) | — | **production** `MARK_HEAP` |

There is also a complete second non-pool marking implementation
(`_PyGC_ParallelMarkAlive`, 100 lines, plus `parallel_worker_run` and the
`_PyGCFTParState` machinery) that tests exercise but production never uses.
`test_gc_ft_parallel.py:338` says the test "exercises the actual
`_PyGC_ParallelMarkAlive()` code path". That is true, but production
correctness depends on a different code path.

The two production work-stealing loops use **different termination policies**:

- `propagate_pool_work` gives up after `2 × num_workers` failed sweeps
  (`MAX_STEAL_ATTEMPTS`, line 1430);
- `mark_heap_pool_work` gives up after three idle rounds (`MAX_IDLE_ROUNDS`,
  line 1691).

Both are heuristics; neither is a termination protocol. The `propagate` loop
also iterates over `pool->num_workers` (all 16) rather than the active count
when choosing victims.

### 6.3 Recommended deduplication

1. Delete the dead functions in 6.1 and require a warning-clean build in CI
   with `-Werror=unused-function`, applied to the GC files only.
2. Delete the non-pool `_PyGCFTParState` marking path. Re-point its tests at
   the pool path, which is what production runs.
3. Factor one work-stealing driver: local buffer, deque, steal, termination.
   Pass it a per-phase "visit object" callback or an inlined macro. Use it
   for both PROPAGATE and MARK_HEAP, with one termination protocol (Section
   8.1).
4. Share the deque and local-buffer helpers between GIL and FT. They already
   live in `pycore_ws_deque.h`. The thin wrappers in
   `gc_free_threading_parallel.c:1398–1415` add nothing.

### 6.4 Signs of model-written code

**[Source]** These are presented as indicators, not defects:

- asserts carrying string messages throughout (111 `assert` calls in the FT
  parallel file);
- performance claims in comments without measurement, for example "Relaxed
  load is ~10x cheaper than atomic RMW" in `gc_parallel.c`;
- leftover TODOs on key parameters ("TODO: Needs tuning based on production
  workload profiling", for the 2 MB-per-worker deque);
- a hard-coded 64-byte cache line (`_Py_CACHELINE_SIZE`); Apple M-series uses
  128.

**[Judgement]** The code has accreted rather than been designed: alternatives
were added and never removed. That is the typical result of model-generated
code that has never been through a demanding human reviewer.

---

## 7. Performance analysis

### 7.1 Setup

- **[Measured]** Workload: `scale.py` builds a live heap of about 1M objects
  of one of four shapes:
  - `graph`: random graph, out-degree 3;
  - `tree`: balanced binary tree held by its root;
  - `lists`: 250k × `[(i, i+1), [i], {'k': i}]`;
  - `chain`: linked list held by its head.
- Each run: a fresh process; the worker count re-pinned before every
  collection with the private hook
  `_testinternalcapi.parallel_gc_set_adaptive_workers`; median of 9
  collections; processes pinned to cores 0–31.
- Builds:
  - **baseline**: release build of fork `c67363fa59`;
  - **patch**: the same source with the changes in Section 8;
  - the PGO+LTO build `build-overnight-20261007-ft` was used to confirm the
    defect is not an artefact of building without PGO.

### 7.2 Phase breakdown: where the time goes

**[Measured]** Baseline, live 1M graph held by a global:

| Workers | Wall | `mark_alive` | `update_refs` + `mark_heap` + `scan_heap` |
|---:|---:|---:|---:|
| 2 | 162.0 ms | 153.5 ms | 8.5 ms |
| 4 | 134.3 ms | 129.6 ms | 4.6 ms |
| 8 | 117.5 ms | 115.2 ms | 2.3 ms |
| 16 | 147.5 ms | 146.0 ms | 1.4 ms |

- The three heap phases scale about 6x from 2 to 16 workers.
- `mark_alive` is 94–99% of the collection and does not scale.

### 7.3 Per-thread CPU: is `mark_alive` actually parallel?

**[Measured]** Per-thread CPU time from `/proc/self/task/*/schedstat` across
one `gc.collect()`, graph held by a global, 16 workers:

| Build | Busiest thread | Each other worker | Total CPU / wall |
|---|---:|---:|---:|
| PGO+LTO, unpatched | 147.1 ms | 1.3 ms | 1.13 |
| Release, unpatched | 167.4 ms | 1.3 ms | 1.11 |
| Release, patch v1 | 23.1 ms | 22.7 ms | 15.81 |

In the unpatched build, root propagation runs on one thread. (Total CPU / wall
for the patch includes idle workers spinning; wall time is the number that
matters.)

### 7.4 Mechanism, and why the project's benchmarks did not see it

**[Source]**

- FT root propagation starts from a very small root set. `sysdict`, extra
  roots and thread stacks are enqueued (`gc_free_threading.c:1482`), and the
  roots are handed out round-robin to worker deques
  (`gc_free_threading_parallel.c:2515`).
- Each worker then runs `propagate_pool_work`:
  1. drain its private `_PyGCLocalBuffer` (1,024 entries), which other workers
     cannot see;
  2. refill from its own deque;
  3. try to steal from other deques;
  4. after `2 × num_workers` consecutive empty sweeps, **exit for good**.
- New work reaches the stealable deque only when the private buffer
  overflows (`_PyGC_OverflowFlush`, which moves 512 entries).

**[Measured]** Holder placement decides the outcome (16 workers, 1M objects):

| Shape | Holder | Baseline speedup | Baseline `mark_alive` | Patch v2 speedup |
|---|---|---:|---:|---:|
| graph | module global | **0.61x** | 123.3 ms | 3.08x |
| graph | frame local | **3.39x** | 20.6 ms | 2.97x |
| tree | global | 1.22x | 21.4 ms | 1.25x |
| tree | local | 1.22x | 21.1 ms | 1.21x |
| lists | global | 1.11x | 13.9 ms | 0.32x |
| lists | local | **0.62x** | 24.5 ms | 0.31x |

**[Inference]** The explanation consistent with all rows:

- **D1, give-up termination.** With a frame-local holder, the worker holding
  the 1M-element list fills its buffer within microseconds. Overflow reaches
  its deque while the helpers are still within their steal attempts, so
  stealing happens (graph local, 3.39x). With a global holder, that worker
  first walks `sysdict → modules → __main__ → keep` and many module objects.
  By the time stealable work appears, every helper has already quit (graph
  global, 0.61x). The patch makes the two placements equivalent (3.08x vs
  2.97x), which supports this explanation.
- **D2, unstealable private buffer.** A binary-tree DFS never accumulates
  1,024 private entries, so nothing ever becomes stealable, whatever the
  holder (1.22x both ways). Patch v1, which proactively shares half the
  buffer when the deque is empty, exposed **4.00x** on the tree (Section 8).
- **D3, per-object stealing on fine-grained heaps.** When stealing *does*
  happen on `lists` (baseline with a local holder, or either patch), the
  collection slows down. Every object is a separate CAS steal, the work per
  object is tiny, and objects allocated next to each other get marked by
  different threads. The global-holder baseline looks fine (1.11x) only
  because stealing never happens. **[Inference]** The likely costs are
  contention on the victim deque's `top` and false sharing on GC bits in
  adjacent objects. I have not profiled to separate the two.
- **Single-worker parallel is slower than serial.** For the graph held by a
  global, the parallel path does the same traversal on one thread but takes
  123 ms against about 76 ms serial. **[Source]** The serial path prefetches
  when `long_lived_total > 200000` (`gc_free_threading.c`, `use_prefetch`).
  The FT parallel marking path does no object prefetch, and it marks with
  atomic read-modify-write. **[Inference]** These two account for the
  difference. Not yet separated by experiment.

**[Source, Inference]** Why the project's headline numbers look better: its
collection benchmark holds live data in a function local (`keep_refs`), the
favourable placement for D1. In real applications, large long-lived data
(caches, registries, ORM identity maps, loaded models) is typically reachable
from module state, which is the unfavourable placement. **[Judgement]**
Workloads like these are therefore under-represented in the project's
evidence.

### 7.5 What does not scale whatever the implementation

**[Measured]** `chain` is 0.88–0.91x at 16 workers in every build and holder
combination: a linked list has no parallelism. Serial finalization and
deallocation are outside this analysis, because these heaps are live.

---

## 8. Experimental patch

**[Measured]** The patch was applied to a throwaway copy of `c67363fa59`
(`patch-v1.diff`, `patch-v2.diff`). The FT GC suites pass on the patched build
with 197 tests run and 62 skipped: `test_gc_ft_parallel`,
`test_gc_parallel_properties`, `test_gc_parallel_fork`, `test_gc` and
`test_free_threading.test_gc`. No sanitizer or fork-stress testing was done.
**This is a demonstration, not a proposal.**

**v1:**

- counter-based termination: `propagate_active` starts at the participant
  count; a worker decrements it when it holds no work, and *re-increments it
  before stealing*, so zero means no worker holds or can create work;
- proactive sharing: every 32 objects, if the worker's own deque is empty and
  its private buffer holds at least 16 entries, push half the buffer to the
  deque;
- idle wait uses `_Py_yield()`.

**v2:** v1 plus coarser sharing (every 128 objects, at least 64 entries);
only steal from a victim whose deque holds at least 32 entries; exponential
`cpu_relax` backoff, then yield.

Speedup over the same build's serial collector at 16 workers, global holder,
with 2–16 worker curves in `results-v1.jsonl` and `results-v2.jsonl`:

| Shape | Baseline | Patch v1 | Patch v2 |
|---|---:|---:|---:|
| graph | 0.61–0.83x | **2.98x** | **2.96x** |
| tree | 1.22–1.27x | **4.00x** | 1.25x |
| lists | 1.10–1.11x | **0.15x** | 0.31x |
| chain | 0.88–0.91x | 0.89x | 0.89x |

Interpretation:

- **[Measured]** The scaling ceiling on graph and tree is in the
  implementation, not the design.
- **[Measured]** Patch v1 regresses fine-grained heaps. v2's tuning halved
  that regression but threw away the tree gain. Simple threshold tuning
  cannot get every shape right at once.
- **[Judgement]** About 3x on 16 workers (roughly 19% efficiency) on a random
  graph is still modest. Going further needs the techniques in 8.1, not more
  tuning of the same mechanism.

### 8.1 Optimisation approaches, in priority order

Unless noted, these are **[Judgement]**: standard techniques from parallel
GC practice (HotSpot Parallel/G1, Go, OCaml 5), not yet tested here.

1. **A real termination protocol** for every work-stealing phase. Use a
   shared active counter with re-registration before stealing, as in the
   patch, or the classic Flood/Detlefs termination barrier. *Removes D1
   (demonstrated).*
2. **Sharing driven by demand, not thresholds.** Publish work to the deque
   only when an idle worker exists: an "idle workers" counter, or a "steal
   requested" flag per victim. Busy workers then pay nothing on fine-grained
   heaps, and idle workers still find work on deep, narrow ones. *Addresses
   D2 without D3's cost.*
3. **Split large containers into range tasks.** Push `(container, start,
   end)` tasks instead of each element of a large list, tuple or dict, as
   HotSpot does with chunked object arrays. A thief takes a contiguous range,
   which preserves locality, reduces steals by orders of magnitude, and gives
   instant parallelism at the first large container. The existing exact
   list/tuple/dict fast paths are the natural place to add this. *Addresses
   D3 and the root fan-out problem.*
4. **Steal in batches by moving ranges, not by repeated per-object CAS.**
   `_PyGC_BatchSteal` performs up to 512 single CAS steals. Range tasks (3)
   largely remove the need.
5. **Expand roots further before dispatch.** Expand the root set breadth-first
   on the collecting thread until the frontier holds at least k × workers
   items (for example k = 64), instead of round-robining a handful of roots.
   The GIL pre-mark already expands one level; FT does not expand at all.
6. **Start serially and switch to parallel when the frontier grows.** Begin
   `mark_alive` on the collecting thread with the serial prefetching
   traversal, and wake helpers only when the frontier exceeds a threshold.
   This removes the case where parallel is slower than serial.
7. **Prefetch in the parallel traversal**, as the serial path already does
   above 200k long-lived objects. Measure separately how much of the
   single-thread gap (123 ms vs 76 ms) comes from prefetch and how much from
   atomic marking.
8. **Avoid false sharing in mark bits.** With range tasks (3), adjacent
   objects are mostly marked by the same worker. Measure with `perf c2c`
   before and after.
9. **Apply the same review to the GIL collector [not measured].** Its
   pre-mark and mark phases "do not steal between workers"
   (`ARCHITECTURE.md:208`, `:269`), the same class of risk. The GIL path was
   not measured here.

### 8.2 Measurement changes

- Expose per-worker objects marked, stolen, and busy time per phase in FT
  `get_parallel_stats()`. Today FT returns no `workers` list, and
  `mark_heap` resets the counters `propagate` uses.
- Add a standing falsification test: "for a live heap of at least 1M
  objects, `mark_alive` time at 16 workers is at most X% of the time at 2
  workers". Run it for both holder placements.
- Vary *where live data are rooted* (module global, frame local, class
  attribute, C extension global) in the project benchmark, alongside heap
  shape and survivor ratio.
- Add a "parallel is never slower than serial beyond threshold N" regression
  gate for live heaps.

---

## 9. Corrections to earlier statements in this conversation

1. *"Four near-duplicate steal routines and two separate `mark_heap`
   workers."* The more precise account: five FT steal routines, of which two
   are reachable only from dead code, one only from a debug test hook, and
   two are production. Of the two `mark_heap` workers, one is dead
   (`mark_heap_worker`). See 6.2.
2. *"Your 1.24x headline likely comes from garbage-heavy collections."*
   **Wrong.** The benchmark keeps 80% of objects live. The real reason it
   avoids the defect is that it holds live data in a function local
   (Section 7.4).
3. *"Root propagation is effectively single-threaded."* **Too broad.** It is
   single-threaded when live data are reachable from module state (D1), or
   when the private buffer never overflows (D2). With a frame-local holder
   on a wide graph, the unpatched build reaches 3.39x.
4. *"A strong human GC engineer would get better scaling."* **Refined.**
   Better scaling is achievable in this design: up to 3–4x on graph and tree
   with a 40-line change, against 0.6–1.3x today. But a naive fix trades one
   shape for another. A robust result needs the techniques in 8.1, which is
   specialist knowledge. **[Judgement]** The gap is judgement about *what to
   measure* and *which established technique applies*, rather than the
   ability to write the code. A model found the defect within about 30
   minutes once the question was asked; the project's process never asked
   it.

---

## 10. Revised frontier assessment

**[Judgement]**

| Dimension | Position |
|---|---|
| Scope and persistence | At the frontier. Long-horizon integration across two build modes and three platforms, with sanitizer and fork evidence. |
| Process rigour and honesty | Above typical human projects. Strong provenance and reporting of negative results. |
| Algorithmic novelty | Low. Textbook Chase-Lev, atomic mark bits, page partitioning, hill-climbing worker control. Provenance relative to earlier CPython parallel-GC work is listed as an open question by the project itself. |
| Code craft | Below a strong human reviewer's standard. Dead alternatives, duplicated mechanisms, heuristic termination, compiler warnings left in. |
| Performance engineering | The weakest dimension. Instrumentation existed but was not used to test the central claim. Regressions remain hypotheses. The scaling result depends on holder placement. |

Overall: a model under disciplined human direction can now *build and
evidence* something of this size. What it doesn't yet do unprompted is
*interrogate its own central performance claims* and *apply specialist design
knowledge* to robustness problems. That is where an expert reviewer, human or
model, still adds the most value.

---

## 11. Limitations and reproducibility

- One machine (72-core Neoverse-V2), synthetic heaps, medians of 9
  collections over 1–2 fresh processes per cell. No confidence intervals or
  significance tests. Baseline speedups vary between runs (graph held by a
  global: 0.61–0.83x); the direction never changed.
- The A/B builds are release builds without PGO. The single-thread
  `mark_alive` behaviour also reproduces on the project's PGO+LTO build
  (Section 7.3).
- The patch passed the five GC test suites only: no ASan, TSan or fork
  stress.
- Not measured: the GIL collector, mixed workloads, finalization or
  deallocation, other hardware.

Artifacts are in [`benchmarks/results/investigations/claude-scaling-2026-10-15/`](../../benchmarks/results/investigations/claude-scaling-2026-10-15/):

| File | Content |
|---|---|
| `scale.py` | Heap builder and timing. The current version takes a `global`/`local` holder argument; `results-v1/v2.jsonl` were produced by an earlier version with the same behaviour as `global`. |
| `cpu.py` | Per-thread CPU across one collection. |
| `run.sh`, `summarise.py` | Alternating baseline/patch matrix driver and summary. |
| `results-v1.jsonl`, `results-v2.jsonl` | 4 shapes × 5 modes × 2 repetitions × 2 builds, global holder. |
| `holder.jsonl` | Global vs local holder, 3 shapes, both builds. |
| `patch-v1.diff` | v1 change to `gc_free_threading_parallel.c`. The `propagate_active` header field is shown in `patch-v2.diff`. |
| `patch-v2.diff` | Full v2 diff, including the header. |

To reproduce:

```bash
git -C cpython archive c67363fa59 | tar -x -C src
# configure --disable-gil --with-parallel-gc
# apply patch-v2.diff to a second copy and build it as well
taskset -c 0-31 ./python -I scale.py graph 1000000 16 global
```


---

## Addendum, 15 October 2026 (later the same day): what the full suite showed

The micro-benchmark claims above did not carry over to the project's
realistic ABBA suite. Corrections, in the order the evidence arrived:

1. **Full project suite (PGO+LTO, ABBA, frame-rooted workloads):** the
   candidate fix (C1+C3+C2) was neutral on throughput and mean latency
   relative to a serial control. Under the pre-registered no-harm rule it
   showed two **regression signals**: mixed-workload maximum latency
   +50% (noisy), and sustained `ai_workload` throughput −4.0%.
2. **The existing collection benchmark had a bug** (since fixed): creation-pool
   threads kept every generated cluster reachable, so collection-shape
   results before the fix timed fully live heaps with no garbage.
3. **Module-rooted workloads added to the suite:** on the baseline, they do
   reproduce the root-propagation defect (§7.4), partially. A first quick
   ABBA showed no visible benefit for the realistic module-cache workload,
   possible gains on module-rooted collection shapes, and the
   `ai_workload` regression signal again. A full campaign is pending.

**Revised assessment.** The phase-level defect is real and fixable, but no
material application-level benefit has been shown. The existing design
already delivers about +25% throughput and −27% latency on the mixed
workload. The statements in §1 and §9 that a specialist "would get better
scaling numbers", and that the scaling limit is "in the implementation,
not the design", rest on micro-benchmarks and are **not supported** by the
realistic suite so far. Judgements about the quality of the algorithms
should be read with that in mind.
