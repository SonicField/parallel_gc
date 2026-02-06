# Supervisor State: Parallel GC for CPython

## Terminal Goal

Merged PR to upstream CPython for parallel garbage collection, with publications on performance benefits and a PEP processed in parallel.

## Current Phase

Phase 6: Publication Preparation — Workers P4-P7 complete. Ready for benchmark runs.

## Active Workers

None.

## Workers Since Last Self-Check

Counter: 4 (SELF-CHECK REQUIRED)

## Completed Workers (This Session)

| Worker | Task | Result |
|--------|------|--------|
| p4-build | Build verification + full test suite | PASS: clean rebuild, 5 test suites pass 3/3, 1049 regression tests pass |
| p5-design | Rewrite DESIGN_POST.md | DONE: 449 lines, all 15 discrepancies addressed, FTP section added |
| p6-bench | Benchmark NBS audit + smoke test | DONE: all 4 benchmarks publication-ready, 1.33x geomean at 500K, optimised build needed |
| p7-pep | Draft PEP outline | DONE: PEP_OUTLINE.md with all sections, 7 rejected alternatives, benchmark data |

## Previous Sessions Summary

**Discovery (Session 1):** 5 workers analysed artefact groups. Discovery report produced.

**Recovery (Sessions 2-3):**
- Phase 1: Foundation (git state, NBS structure, submodule) - COMPLETE
- Phase 2: Codebase audit (5 workers) - COMPLETE
- Phase 5: Remediation (workers 5a-5e) - COMPLETE
- Task 6: FTP race investigation - COMPLETE (tuple untracking fix)
- NBS review remediation (workers R1-R5) - COMPLETE

**Key results:** All 5 test suites pass 3 consecutive runs. FTP race fixed. GC_DEBUG_ATOMICS fixed. 22 stale docs archived. 15 discrepancies catalogued.

## Remaining Work

- Goal 6: Run ARM Linux benchmarks (need ARM machine)
- Goal 7: Run Intel Linux benchmarks (need optimised build first)
- Goal 8: Verify Mac build (need Mac)
- Goal 9: Verify Windows build (need Windows)
- Goal 10: Write full PEP (outline complete)
- Goal 11: Submit PR (depends on everything)

**Immediate next steps on this machine:**
1. Build optimised cpython binary (`--disable-gil --enable-optimizations --with-lto`)
2. Run rigorous Intel benchmarks with optimised build
3. Minor benchmark cleanup (P6 "should fix" items)

## 3Ws + Self-Check Log

### Discovery Workers 1-5 - 2026-02-06

**What went well:** All 5 workers completed, comprehensive analysis, key dead ends identified.
**What didn't work:** Worker 4 stalled, needed nudge.
**What we can do better:** Add timeout monitoring, explicit "write now" instructions.

### Audit Workers 2.1-2.5 - 2026-02-06

**What went well:** All 5 completed with detailed findings, parallel execution saved time.
**What didn't work:** Worker 4 stalled briefly.
**What we can do better:** Include explicit write instruction, use underscore-only session names.

### Remediation Workers 5a-5e - 2026-02-10

**What went well:** All 5 completed, build verified, submodule boundary handled.
**What didn't work:** Worker 5a needed command resent, Hypothesis unavailable.
**What we can do better:** Increase delay before sending, bundle Hypothesis in requirements.

### NBS Review Workers R1-R5 - 2026-02-10

**What went well:** All 5 completed. R2 found secondary bug (#ifdef vs #if). R1 confirmed tuples only type.
**What didn't work:** Workers couldn't push to GitHub (proxy). R4 needed many permission prompts.
**What we can do better:** Use fresh pty-session for git push. Select "don't ask again" for file ops.

### Publication Workers P4-P7 - 2026-02-11

**What went well:**
- All 4 workers completed all tasks successfully
- P7 (PEP outline) finished first — correct since it was read-only research
- P6 ran actual benchmarks (smoke test) and got meaningful results (1.33x geomean)
- P5 addressed all 15 discrepancies with verification against source code
- P4 verified clean build with 1049 regression tests passing

**What didn't work:**
- Initial nbs-worker spawn sent prompts before Claude was ready — all 4 stuck
- Had to dismiss and respawn using pty-session with manual prompt timing
- 3-second delay in nbs-worker is insufficient when 4 workers start simultaneously

**What we can do better:**
- Use pty-session directly for more control over prompt timing
- Wait for Claude's "Try..." placeholder before sending prompt
- Or increase nbs-worker delay to 10+ seconds on loaded systems

**Self-check (workers_since_check = 4 >= 3):**
- [x] Am I still pursuing terminal goal? YES — build verified, docs updated, benchmarks audited, PEP outlined
- [x] Am I delegating vs doing tactical work myself? YES — all 4 tasks delegated to workers
- [x] Have I captured learnings that should improve future tasks? YES — nbs-worker timing issue documented
- [x] Should I escalate anything to human? YES — need decisions on:
  1. Run optimised benchmarks now on this Intel machine? (Goal 7)
  2. Mac/Windows verification — does Alex have access to those machines?
  3. Minor benchmark fixes — worth doing now or defer?

Workers since check reset to: 0

### Optimised Benchmark Worker P8 - 2026-02-12

**What went well:**
- Worker completed entire pipeline: build + 4 benchmark configs + analysis
- PGO build failure handled autonomously (excluded test_sqlite3)
- Publication-quality results: 1.25x–2.61x collection speedup, up to -74% STW pause
- Thorough analysis comparing debug vs optimised, current vs archived, worker scaling

**What didn't work:**
- PGO profile generation failed on test_sqlite3 (unrelated test) — worker worked around it
- Archived results (3.35x–4.78x) not reproduced — different benchmark methodology. Current results are more conservative but more representative.
- 1-worker overhead not tested (would need separate benchmark run)

**What we can do better:**
- Pre-check PGO-problematic tests before starting the build
- Include 1-worker overhead test in benchmark plan

Workers since check: 1
