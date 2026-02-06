# Parallel GC for CPython - Progress Log

**Date started**: 06-02-2026
**Plan file**: 06-02-2026-parallel-gc-plan.md

---

## 06-02-2026 - Recovery Session

### Discovery Phase (Complete)

- Ran `/nbs-discovery` with 5 parallel workers analysing artefacts
- Identified valuable outcomes: implementation, benchmarks, publication drafts
- Documented dead ends: BRC sharding, cleanup workers, fast decref
- Gap analysis with 6 questions confirmed with human
- Discovery report written to `.nbs/discovery-report.md`

### Recovery Phase (In Progress)

**Step 1.1: Verify git state** ✓
- Found divergence: local 9 ahead, 1 behind fork
- Analysed all commits - local contains all valuable work
- 3 untracked files identified as valuable (unified_phase_design.md, atomic results)
- Committed untracked files
- Force pushed to fork with --force-with-lease
- Result: Branch clean, synced with fork

**Step 1.2: Create NBS project structure** ✓
- Created plan file: 06-02-2026-parallel-gc-plan.md
- Created progress file: 06-02-2026-parallel-gc-progress.md (this file)

**Step 1.3: Commit recovery starting point** ✓
- Initialised outer git repo for parallel_gc/
- Added cpython as submodule pointing to SonicField/cpython parallel-gc-dev branch
- NBS structure committed

---

## Phase 2: Codebase Audit (Complete)

Spawned 5 parallel workers via pty-session:

| Worker | Task | Status | Key Findings |
|--------|------|--------|--------------|
| audit-2_1 | Abandoned code | ✓ | Dead `#ifdef Py_BRC_SHARDED` block, orphaned test classes |
| audit-2_2 | Thread pool refactor | ✓ | 4 dead ad-hoc functions remain |
| audit-2_3 | Style audit | ✓ | `GC_DEBUG_ATOMICS=1` enabled, copyright headers |
| audit-2_4 | Engineering standards | ✓ | 6 gaps: postconditions, property testing |
| audit-2_5 | File relocation | ✓ | 4 benchmarks + 6 docs to move |

### 3Ws - Phase 2 Workers

**What went well:**
- All 5 workers completed successfully with detailed findings
- Parallel execution saved significant time
- Workers followed task structure and provided evidence-based findings
- Clear separation of concerns across audit domains

**What didn't work:**
- Worker 4 stalled briefly after "thinking" - needed nudge to continue
- Session names with dots converted to underscores (minor)

**What we can do better:**
- Include explicit "write findings now" instruction in worker prompts
- Use underscore-only session names from start

---

## Phase 5: Remediation (Complete)

Spawned 2 workers to execute remediation:

### Worker 5a: Code Cleanup ✓

| ID | Task | Result |
|----|------|--------|
| 5.1 | Remove `#ifdef Py_BRC_SHARDED` block | 9 lines removed from gc_free_threading.c |
| 5.2 | Remove orphaned test classes | ~390 lines removed from test_gc_parallel.py |
| 5.3 | Disable `GC_DEBUG_ATOMICS` | Changed to 0 in pycore_gc_ft_parallel.h |
| 5.4 | Delete dead ad-hoc thread functions | ~435 lines + 22 declarations removed |

**Build verification**: `make -j8` passed

### Worker 5b: File Relocation ✓

| ID | Task | Result |
|----|------|--------|
| 5.5 | Relocate benchmark files | 4 files → parallel_gc/benchmarks/ |
| 5.6 | Relocate investigation docs | 6 files → parallel_gc/.nbs/docs/ |

**Note**: Files copied (not git mv) due to submodule boundary. Originals deleted from submodule.

### Worker 5c: Copyright Headers ✓

| ID | Task | Result |
|----|------|--------|
| 5.7 | PSF copyright headers | Removed Meta copyright from pycore_gc_parallel.h |

**Finding**: Only 1 file had Meta copyright. Others had descriptive headers only.

### Worker 5d: Assertions ✓

| ID | Task | Result |
|----|------|--------|
| 5.8 | Precondition assertion | Added NULL check to gc_try_mark_reachable_atomic |
| 5.8 | Postcondition assertion | Added list linkage verification to _PyGC_ParallelMoveUnreachable |
| 5.8 | Error messages with context | Changed PyErr_SetString to PyErr_Format with values |
| 5.8 | Silent fallback logging | Added debug logging for serial fallback |

**Build verification**: `make -j8` passed

### Worker 5e: Property-Based Tests ✓

| ID | Task | Result |
|----|------|--------|
| 5.9 | Property-based tests | 16 new tests in test_gc_parallel_properties.py |
| 5.10 | Boundary value tests | 8 boundary tests (min/max workers, empty/single collections) |

**Note**: Hypothesis unavailable (network blocked). Used Python's random module instead.

**Tests created:**
- TestPropertyCyclicGarbageCollected (2 tests)
- TestPropertyReachableObjectsSurvive (2 tests)
- TestPropertyWorkerStatisticsConsistency (1 test)
- TestBoundaryValues (8 tests)
- TestPropertyMixedGarbageAndReachable (1 test)
- TestPropertyThreadedGarbageCollection (2 tests)

**All 16 tests pass.**

### 3Ws - Phase 5 Workers (5a-5e)

**What went well:**
- All 5 workers completed all tasks successfully
- Build verified after each code change
- Workers correctly handled submodule boundary
- Property tests found real behaviours (min workers is 2, not 1)

**What didn't work:**
- Worker 5a needed command resent (didn't receive initial prompt)
- Hypothesis unavailable due to network restrictions

**What we can do better:**
- Increase delay before sending commands to new sessions
- Consider bundling Hypothesis in test requirements

---

## Git State After Phase 5

**Main repo (parallel_gc/):**
- 10 relocated files staged (benchmarks + docs)
- Worker task files updated

**Submodule (cpython/):**
- Code cleanups applied (5.1-5.4)
- Copyright headers fixed (5.7)
- Assertions added (5.8)
- 1 new test file created (5.9-5.10)
- 7 file deletions staged (relocated files)

---

## Phase 6: Publication Preparation (Complete)

Spawned 4 parallel workers via pty-session:

| Worker | Task | Status | Key Result |
|--------|------|--------|------------|
| P4 | Build verification + full test suite | ✓ | Clean rebuild, 5 test suites pass 3/3, 1049 regression tests pass |
| P5 | Rewrite DESIGN_POST.md | ✓ | 449 lines, all 15 R5 discrepancies addressed, FTP section added |
| P6 | Benchmark NBS audit + smoke test | ✓ | All 4 benchmarks publication-ready, 1.33x geomean at 500K |
| P7 | Draft PEP outline | ✓ | PEP_OUTLINE.md with all sections, 7 rejected alternatives |

### P4: Build Verification

- Clean rebuild: `make clean && ./configure --with-pydebug --disable-gil && make -j8` — PASS
- test_gc_parallel (35 tests): 3/3 PASS
- test_gc_ft_parallel (30 tests): 3/3 PASS
- test_gc_parallel_mark_alive: skipped (expected — GIL-only tests on FTP build)
- test_gc_ws_deque (9 tests): 3/3 PASS
- test_gc_parallel_properties (16 tests): 3/3 PASS
- test_gc (58 tests): PASS
- test_threading + test_concurrent_futures + test_multiprocessing_spawn (1049 tests): PASS

### P5: DESIGN_POST.md Rewrite

All 15 discrepancies from R5 addressed. Key changes:
- Atomic marking: CAS → Fetch-And with code sample
- Work distribution: simple round-robin → multi-phase architecture
- Static slicing: naive formula → split vector with 8K intervals
- Added full FTP section (was listed as "future work")
- Clarified mark phase is local-only, work-stealing is in mark_alive
- Corrected all API names, return values, function names

Output: `.nbs/docs/DESIGN_POST.md` (449 lines)

### P6: Benchmark Audit

**Publication readiness**: All 4 benchmarks ready with minor cleanup.
**Critical finding**: Current debug build unsuitable for publication numbers — need optimised build.

Smoke test results (debug build, 500K objects, 8 workers):

| Heap Type | Serial (ms) | Parallel (ms) | Speedup |
|-----------|-------------|---------------|---------|
| chain | 335.5 | 249.4 | 1.34x |
| wide_tree | 360.2 | 260.8 | 1.38x |
| graph | 387.1 | 265.9 | 1.46x |
| independent | 373.8 | 252.4 | 1.48x |
| **Geomean** | | | **1.33x** |

### P7: PEP Outline

PEP_OUTLINE.md written with: Abstract, Motivation, Rationale, Specification, Backwards Compatibility, Security Implications, Performance Impact, Rejected Alternatives (7 dead ends), Reference Implementation, Open Issues.

### 3Ws - Phase 6 Workers

**What went well:**
- All 4 workers completed successfully
- P6 ran actual benchmarks with meaningful results
- P5 verified every claim against source code

**What didn't work:**
- nbs-worker spawn timing issue — prompts sent before Claude ready
- Had to dismiss and respawn with pty-session

**What we can do better:**
- Use pty-session directly for more control over prompt timing
- Wait for Claude's prompt placeholder before sending task

---

## Next Actions

1. ~~Build optimised cpython binary~~ ✓ (P8)
2. ~~Run rigorous Intel benchmarks with optimised build~~ ✓ (P8)
3. Minor benchmark cleanup (P6 "should fix" items)
4. Run ARM benchmarks (Goal 6 — needs ARM machine)
5. Verify Mac build (Goal 8 — needs Mac)
6. Verify Windows build (Goal 9 — needs Windows)
7. Write full PEP from outline (Goal 10)
8. Submit PR (Goal 11)

---

## Phase 7: Optimised Intel Benchmarks (Complete)

Worker P8 built optimised PGO+LTO binary and ran rigorous benchmarks.

**System**: Intel Xeon Platinum 8339HC, 192 CPUs (4 sockets × 24 cores × 2 threads), 4 NUMA nodes.

**Build**: `--disable-gil --enable-optimizations --with-lto` (O3 + PGO + LTO). PGO excluded test_sqlite3 (unrelated failure).

### Collection Time Results (Optimised FTP Build)

| Heap Type | 500K/8W | 1M/8W | 1M/16W |
|-----------|---------|-------|--------|
| chain | 1.91x | 1.90x | 1.53x |
| tree | 1.41x | 2.21x | 1.87x |
| wide_tree | 1.41x | 1.63x | 1.81x |
| graph | 1.82x | 1.95x | **2.61x** |
| layered | 1.53x | 1.68x | 1.68x |
| independent | 1.69x | 1.25x | 1.86x |
| ai_workload | 1.55x | 1.63x | 1.71x |
| web_server | 1.86x | 1.38x | 1.63x |

### Throughput and Pause Results

| Configuration | Throughput Change | STW Pause Reduction |
|---------------|------------------|---------------------|
| 500K / 8W | -0.4% (neutral) | -58% |
| 1M / 8W | +2.7% | -17% |
| 1M / 16W | +3.6% | -59% |

### Worker Scaling (1M Objects)

5 of 8 topologies benefit from 16 workers vs 8. Graph topology scales best (1.95x → 2.61x). Chain/tree degrade at 16W (contention on sequential traversals).

### Locality Benchmark

Serial: 59.92ms → Parallel: 39.49ms = **1.52x** on worst-case sequential chain at 1M objects.

### Results Files

- `benchmarks/results/intel_500k_w8.json` / `.txt`
- `benchmarks/results/intel_1m_w8.json` / `.txt`
- `benchmarks/results/intel_1m_w16.json` / `.txt`
- `benchmarks/results/intel_locality_1m.txt`
- `benchmarks/results/system_info.txt`

---

## NBS Review Remediation (Complete)

Spawned 5 workers to address NBS review findings:

| Worker | Task | Result |
|--------|------|--------|
| R1 | MaybeUntrack analysis | Tuples only - no fix needed |
| R2 | GC_DEBUG_ATOMICS fix | Fixed #ifdef→#if guards + CFLAGS override |
| R3 | Property test seeds | Deterministic seeds + GC_TEST_SEED env var |
| R4 | Archive stale docs | 22 docs archived from cpython to .nbs/docs/archive/ |
| R5 | Reconcile docs/code | 15 discrepancies found, code authoritative in all cases |

**Key findings:**
- R1: Tuples are the only CPython type with MaybeUntrack. Fix is complete.
- R2: Found secondary bug - `#ifdef GC_DEBUG_ATOMICS` tests if defined (always true), not value. Changed all 7 guards to `#if`.
- R4: Found 22 project-management docs in cpython that don't belong in PR. All archived.
- R5: DESIGN_POST.md was written early and never updated. 3 high-severity discrepancies (e.g., docs say CAS marking but code uses Fetch-And).

**All 5 test suites pass 3 consecutive runs after remediation.**

**Pushed**: `5f44a9425fb` → SonicField/cpython parallel-gc-dev

---

## Task 6: FTP Race Investigation (Complete)

**Classification**: Missing parallel code path (not a race condition)

**Root cause**:
Parallel propagation in `propagate_pool_work` was calling `tp_traverse` directly without special tuple handling. Serial GC uses `gc_mark_traverse_tuple` which:
1. Calls `_PyTuple_MaybeUntrack()` to untrack tuples containing only non-GC objects
2. Clears the ALIVE bit if the tuple becomes untracked

Parallel GC was missing this, causing tuples to retain ALIVE bits after being untracked.

**Fix applied** (`c4c192c2106`):
- Added tuple untracking to `propagate_pool_work` matching serial behaviour
- Clear alive bit for tuples that become untracked during propagation
- Added defensive cleanup in error paths

**Verification**: Tests passed 5 consecutive runs.

**Pushed**: `c4c192c2106` → SonicField/cpython parallel-gc-dev
