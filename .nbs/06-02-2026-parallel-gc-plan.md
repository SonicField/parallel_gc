# Parallel GC for CPython - Project Plan

**Date**: 06-02-2026
**Terminal Goal**: Merged PR to upstream CPython for parallel garbage collection, with publications on performance benefits and a PEP processed in parallel.

---

## Current Phase

Recovery Phase - applying NBS framework to restore epistemic control.

---

## Instrumental Goals

| # | Goal | Why Needed | Status |
|---|------|------------|--------|
| 1 | Apply NBS framework to project | Restore epistemic control | COMPLETE |
| 2 | Verify/remove abandoned code | Clean codebase for PR | COMPLETE |
| 3 | Verify CPython style compliance | PR acceptance requirement | COMPLETE |
| 4 | Verify engineering standards | Quality per soma/docs | COMPLETE |
| 5 | Apply NBS to benchmarks | Publication-ready evidence | COMPLETE (P6: audit + smoke test) |
| 6 | Run ARM Linux benchmarks | Publication requirement | PENDING (need ARM machine) |
| 7 | Run Intel Linux benchmarks | Publication requirement | COMPLETE (P8: optimised PGO+LTO, 1.25-2.61x) |
| 8 | Verify Mac build | PR requirement | PENDING (need Mac) |
| 9 | Verify Windows build | PR requirement | PENDING (need Windows) |
| 10 | Draft internal PEP | Per Thomas Wouters advice | IN PROGRESS (outline complete) |
| 11 | Submit PR | Terminal goal | PENDING |

---

## Cross-Cutting Requirements

- **Git discipline**: Frequent, atomic commits throughout all work
- **Engineering standards**: Per ~/local/soma/docs/concepts/engineering-standards.md
- **Falsifiability**: Every claim has a potential falsifier
- **Build discipline**: Single source of truth, rebuild from source, no invented paths

---

## Key Constraints

- Parallel GC exists for both GIL (gc_parallel.c) and FTP (gc_free_threading_parallel.c)
- The PR may include both, but FTP scope needs clarification with upstream
- Sweet spot: 500K+ objects, AI/ML workloads
- Windows performance bar is low - just not broken
- PEP drafted internally, not published ahead of PR

---

## Valuable Outcomes to Preserve

1. **Working implementation** - gc_parallel.c (GIL), gc_free_threading_parallel.c (FTP)
2. **Benchmark suite** - 8 heap shapes, FTP/GIL handling, throughput + pause measurement
3. **Publication drafts** - DESIGN_POST.md (HIGH readiness), WORKPLACE_POST.md, KNOWLEDGE_MANIFOLD.md
4. **Design rationale** - 500K threshold, static slicing, thread-local pools, batched buffers

---

## Dead Ends (Do Not Revisit)

| Dead End | Root Cause |
|----------|------------|
| Multi-threaded delete (FTP) | Mimalloc inter-thread cost |
| Work stealing from roots (GIL) | Queue-based more efficient |
| Biased RC internals (FTP) | No improvement |
| Parallel cleanup workers (cw1+) | BRC mutex contention |
| BRC sharding | No benefit in realistic benchmarks |
| Fast decref atomic ADD | Cache-line contention remains |

---

## Upstream Relationship

- Approval from Python Steering Committee members
- Thomas Wouters advice: Submit PR with "may need PEP" note
- PR and PEP processed in parallel

---

## References

- Discovery report: .nbs/discovery-report.md
- Recovery plan: .nbs/06-02-2026-parallel-gc-recovery-plan.md
- Engineering standards: ~/local/soma/docs/concepts/engineering-standards.md
