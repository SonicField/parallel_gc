# Discovery Report: Parallel GC for CPython

**Date**: 2026-02-06
**Terminal Goal (Reconstructed)**: Merged PR to upstream CPython for parallel garbage collection, with publications on performance benefits and a PEP processed in parallel.

---

## Artefacts Found

| Location | Files | Status |
|----------|-------|--------|
| `~/local/parallel_gc/` | README.md, PORTABILITY_*.md, benchmark_analysis.py, perf_test.py, 09-01-2025-ftp-thread-pool-refactor-plan.md | Explored |
| `~/local/parallel_gc/cpython/` | PARALLEL_GC_BENCHMARK_PLAN.md, PARALLEL_DEDUCE_UNREACHABLE_DESIGN.md, PARALLEL_GC_BENCHMARK_RESULTS.md, 16-01-2026-async-cleanup-plan.md, test_atomic_patterns.py, arm_atomic_results.txt, x86_atomic_results.txt | Explored |
| `~/local/parallel_gc/cpython/docs/` | DEVLOG.md, STATUS.md, NEXT_SESSION.md, WORKSPACE.md | Explored - STALE |
| `~/local/parallel_gc/cpython/Doc/parallel-gc/` | DESIGN_POST.md, KNOWLEDGE_MANIFOLD.md, WORKPLACE_POST.md | Explored |
| `~/local/parallel_gc/cpython/Doc/` | parallel_gc_fixes.md, unified_phase_design.md | Explored |
| `~/local/parallel_gc/cpython/Lib/test/` | gc_perf_benchmark.py, gc_locality_benchmark.py, gc_creation_analysis.py, gc_production_experiment.py, test_gc_parallel.py, test_gc_ft_parallel.py, test_gc_parallel_mark_alive.py, test_gc_ws_deque.py, 19-01-2026-*.md, 20-01-2026-*.md | Explored |
| `~/local/parallel_gc/cpython/Python/` | gc_parallel.c, gc_free_threading_parallel.c | Not directly read - core implementation |
| `~/local/parallel_gc/cpython/Include/internal/` | pycore_gc_parallel.h, pycore_gc_ft_parallel.h | Not directly read - headers |

---

## Triage Summary

| Artefact | Purpose | Verdict | Rationale |
|----------|---------|---------|-----------|
| gc_parallel.c, gc_free_threading_parallel.c | Core GIL/FTP implementation | **Keep** | Core value - months of work |
| Benchmark scripts (gc_perf_benchmark.py, etc.) | Sophisticated benchmarking | **Keep** | Publication support, rigorous methodology |
| Test files (test_gc_*.py) | Test suite | **Keep** | Verification, 8 heap shapes covered |
| DESIGN_POST.md | Blog post draft | **Keep** | HIGH readiness, near-publishable |
| WORKPLACE_POST.md | Internal announcement | **Keep** | HIGH readiness, ready to post |
| KNOWLEDGE_MANIFOLD.md | Experimental evidence | **Keep** | Epistemic foundation - derives 500K threshold |
| unified_phase_design.md | Phase abstraction design | **Keep** | Internal reference, enables unified benchmarks |
| parallel_gc_fixes.md | Bug fix notes | **Keep** | Knowledge transfer, ob_tid lessons |
| PARALLEL_GC_BENCHMARK_RESULTS.md | Benchmark results | **Keep** | Evidence - 3.35x max speedup documented |
| PARALLEL_DEDUCE_UNREACHABLE_DESIGN.md | Design rationale | **Keep** | Documents phase parallelisation choices |
| README.md | Project overview | **Keep** | Onboarding, API documentation |
| PORTABILITY_*.md | Portability analysis | **Keep** | Documents PyThread_* solution |
| cpython/docs/ (DEVLOG, STATUS, etc.) | Historical context | **Archive** | STALE but DEVLOG has unique atomic mapping table |
| 19-01-2026 / 20-01-2026 plans | Investigation records | **Keep** | Documents dead ends, prevents re-exploration |
| BRC sharding code (if present) | Abandoned optimisation | **Remove** | Per 20-01-2026-cleanup-plan.md |
| Cleanup workers code (if present) | Abandoned optimisation | **Remove** | Per 20-01-2026-cleanup-plan.md |
| Fast decref code (if present) | Abandoned optimisation | **Remove** | Per 20-01-2026-cleanup-plan.md |

---

## Valuable Outcomes Identified

### 1. Working Implementation
- **GIL parallel GC**: gc_parallel.c with 5 phases (update_refs, mark_alive, subtract_refs, mark, cleanup)
- **FTP parallel GC**: gc_free_threading_parallel.c with 3 phases (update_refs, mark_heap, cleanup)
- **Performance**: 3.35x max speedup, 1.90x mean with all phases parallel
- **Evidence**: PARALLEL_GC_BENCHMARK_RESULTS.md

### 2. Sophisticated Benchmark Suite
- 8 heap shapes: chain, tree, wide_tree, graph, layered, independent, ai_workload, web_server
- FTP vs GIL handling via sys._is_gil_enabled()
- Thread subtleties: abandoned pool vs live heap, keep_threads_alive parameter
- Measures both throughput and pause time
- **Evidence**: gc_perf_benchmark.py (1789 lines), gc_creation_analysis.py (646 lines)

### 3. Publication Drafts
- DESIGN_POST.md: HIGH readiness for external blog
- WORKPLACE_POST.md: HIGH readiness for internal Workplace
- KNOWLEDGE_MANIFOLD.md: Epistemic foundation with 5 controlled experiments
- **Evidence**: Worker Group 3 analysis

### 4. Design Rationale Documentation
- 500K object threshold: empirically derived crossover point
- Static slicing over round-robin: cache locality
- Thread-local 2MB pools: eliminate allocator contention
- Check-first marking: skip atomic RMW for already-marked
- Batched local buffer (1024 items): 1000x fence reduction
- **Evidence**: KNOWLEDGE_MANIFOLD.md, PARALLEL_GC_BENCHMARK_PLAN.md

### 5. Portability Solution
- FTP was POSIX-centric, solved via CPython's PyThread_* abstractions
- Effort reduced from 4-6.5 days to ~10 hours
- **Evidence**: PORTABILITY_PLAN_REVISED.md

---

## Dead Ends Documented

| Dead End | Root Cause | Evidence |
|----------|------------|----------|
| Multi-threaded delete phase (FTP) | Mimalloc inter-thread communication cost too high | Human context |
| Work stealing for 'from roots' (GIL) | Queue-based approach more efficient | Human context |
| Reference counting / biased RC internals (FTP) | Did not yield improvements | Human context |
| Parallel cleanup workers (cw1+) | BRC bucket mutex contention on cross-thread decrefs | 19-01-2026-parallel-cleanup-investigation-progress.md |
| BRC sharding | No measurable benefit in realistic benchmarks | 20-01-2026-cleanup-plan.md |
| Fast decref via atomic ADD | Cache-line contention on ob_ref_shared remains | 20-01-2026-cleanup-plan.md |

### Key Insight (Not a Dead End)
- ARM memory barriers: Added for performance not correctness. Lazy read/idempotent model caused excessive work duplication without barriers.

---

## Gap Analysis

### Instrumental Goals Summary

| Goal | Why Needed | Dependencies |
|------|------------|--------------|
| 1. Apply NBS framework to project | Restore epistemic control, prevent goal drift | None |
| 2. Verify/remove abandoned code | Clean codebase for PR | NBS framework applied |
| 3. Verify CPython style compliance | PR acceptance requirement | Codebase clean |
| 4. Verify engineering standards compliance | Quality requirement per ~/local/soma/docs/concepts/engineering-standards.md | Codebase clean |
| 5. Apply NBS framework to existing benchmarks | Publication-ready evidence | NBS framework applied |
| 6. Run rigorous benchmarks on ARM Linux | Publication requirement | Benchmarks ready |
| 7. Run rigorous benchmarks on Intel Linux | Publication requirement | Benchmarks ready |
| 8. Verify builds/works on Mac | PR acceptance requirement | Codebase clean |
| 9. Verify builds/works on Windows | PR acceptance requirement | Codebase clean |
| 10. Draft PEP (internal) | Parallel with PR per Thomas Wouters advice | Benchmarks complete |
| 11. Submit PR with "may need PEP" note | Terminal goal | All above complete |

**Cross-cutting requirement**: Rigorous git discipline with frequent, atomic commits throughout all work. Enables bisection for debugging and serves as change tracker.

### Confirmed Understanding (Full Detail)

#### Q1: Upstream relationship
**Question**: What is the current relationship with CPython upstream?
**Confirmed**: There is approval from key Python Steering Committee members to pursue this work. Thomas Wouters (core dev) has advised to submit the PR with a note saying "we probably need a PEP for this", allowing the PR and PEP to be processed in parallel rather than sequentially.

#### Q2: Publication requirements
**Question**: What publication/posts need to happen before or alongside the PR?
**Confirmed**: Before/alongside the PR: (1) Rigorous benchmarks for ARM and Intel Linux must be published (external publication). (2) Proof it works on Mac and Windows (functional, not necessarily performant). (3) Windows performance bar is low - optional feature, just not broken or ridiculously slow. (4) A PEP should be drafted but kept internal until the PR is submitted (not published ahead of PR).

#### Q3: Benchmarking needs
**Question**: What additional benchmarking or evidence is needed for the publications?
**Confirmed**: Applying NBS framework approach to existing benchmarks should be sufficient for publication. Sophisticated AI benchmarks are available but should wait until the project is more stable. The AI benchmarks may not work on Python 3.15, potentially requiring backport to 3.14/3.14t. No rush on the AI benchmarks - they're a "nice to have" after core work is locked down.

#### Q4: Code quality requirements
**Question**: Are there code quality/style requirements from CPython that haven't been addressed?
**Confirmed**: Follow CPython coding style (per CPython's own style guides). Follow the engineering standards in ~/local/soma/docs/concepts/engineering-standards.md. Much of this overlaps with NBS framework but should be rigorously applied. No other specific CPython requirements identified beyond these two sources.

#### Q5: Abandoned code status
**Question**: What's the status of the abandoned work (BRC sharding, cleanup workers, fast decref)?
**Confirmed**: The status is unknown. The cleanup plan exists but whether it was executed is uncertain. This needs to be verified during recovery - if the code is still present, it should be removed.

#### Q6: What blocked progress
**Question**: What's blocking progress right now?
**Confirmed**: The project stalled because it became disorganised - goal drift and tech-debt accumulation. The NBS framework and NBS teams were developed specifically to address this class of problem. The recovery path is to apply these tools to bring the project back under epistemic control, then resume development with discipline.

#### Cross-cutting: Git discipline
**Question**: (Volunteered by human during synthesis)
**Confirmed**: There's a cross-cutting requirement throughout all work: rigorous git discipline with frequent, atomic commits. This serves two purposes: enables bisection for debugging, and provides a change tracker for reviewing progress. This applies across all instrumental goals, not just a single step.

---

## Open Questions

1. **Is abandoned code still in codebase?** - BRC sharding, cleanup workers, fast decref - need to verify and remove if present
2. **FTP thread pool refactor status?** - Plan from 09-01-2025 proposed consolidating ad-hoc threads through persistent pool - unclear if implemented
3. **Are docs/ files worth archiving?** - DEVLOG.md has unique atomic mapping table; rest may be discardable
4. **What's the current git state?** - Need to verify branch, uncommitted changes, sync with fork
5. **Python 3.15 compatibility for AI benchmarks?** - May need backport work later

---

## Recommended Next Steps

When ready, run `/nbs-recovery` which will:

1. **Verify git state** - Check branch, uncommitted changes, sync with SonicField/cpython fork
2. **Apply NBS framework** - Create proper project structure with goals, plans, progress tracking
3. **Audit for abandoned code** - Search for BRC sharding, cleanup workers, fast decref - remove if found
4. **Verify CPython style** - Run linters, check against CPython conventions
5. **Verify engineering standards** - Apply ~/local/soma/docs/concepts/engineering-standards.md
6. **Apply NBS to benchmarks** - Make existing benchmarks publication-ready
7. **Build and test on target platforms** - ARM Linux, Intel Linux, Mac, Windows
8. **Run rigorous benchmarks** - ARM and Intel Linux with statistical rigour
9. **Draft internal PEP** - Based on DESIGN_POST.md and benchmark results
10. **Prepare PR** - With "may need PEP" note per Thomas Wouters advice

---

**Report Status**: Ready for recovery
**Generated by**: NBS Discovery process
**Verified**: All sections complete, all confirmed restatements captured in full
