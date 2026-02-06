# Recovery Plan: Parallel GC for CPython

**Based on**: ~/local/parallel_gc/.nbs/discovery-report.md
**Date**: 2026-02-06
**Approach**: NBS Teams Supervisor - delegatable tasks with success criteria

---

## Terminal Goal

Merged PR to upstream CPython for parallel garbage collection, with publications on performance benefits and a PEP processed in parallel.

## Cross-Cutting Requirements

- **Git discipline**: Frequent, atomic commits throughout all work
- **Engineering standards**: Per ~/local/soma/docs/concepts/engineering-standards.md
- **Falsifiability**: Every claim has a potential falsifier

---

## Phase 1: Foundation (Supervisor executes directly)

These steps establish the infrastructure for delegated work. Supervisor executes with human confirmation.

### Step 1.1: Verify git state ✓
- **What**: Check branch, uncommitted changes, remote sync status
- **Why**: Need clean baseline before any changes
- **Reversible**: Read-only check
- **Status**: COMPLETE - analysed divergence, committed untracked files, force pushed to fork

### Step 1.2: Create NBS project structure ✓
- **What**: Create plan and progress files with proper naming convention
- **Why**: Apply NBS framework per discovery requirement
- **Reversible**: Delete created files
- **Status**: COMPLETE - created plan.md and progress.md

### Step 1.3: Commit recovery starting point ✓
- **What**: Commit discovery report and plan files
- **Why**: Git discipline - track recovery start
- **Reversible**: git reset
- **Status**: COMPLETE - initialised outer repo, added cpython submodule, initial commit

---

## Phase 2: Codebase Audit (Delegated to workers)

### Task 2.1: Audit for abandoned code
- **Scope**: Search entire cpython tree for BRC sharding, cleanup workers (cw1+), fast decref code
- **Success criteria**:
  1. Report listing all occurrences found (or confirmed none)
  2. For each occurrence: file, line numbers, what it does
  3. Recommendation: remove/keep with rationale
- **Worker can**: Read files, search code, analyse
- **Worker cannot**: Make changes (report only)
- **Dependencies**: None
- **Status**: Pending

### Task 2.2: Verify FTP thread pool refactor status
- **Scope**: Determine if 09-01-2025 refactor plan was implemented
- **Success criteria**:
  1. Are ad-hoc thread functions still present?
  2. Is all parallel work routed through persistent pool?
  3. If incomplete: what remains to be done?
- **Worker can**: Read code, trace call paths
- **Worker cannot**: Make changes
- **Dependencies**: None
- **Status**: Pending

### Task 2.3: CPython style audit
- **Scope**: Check parallel GC code against CPython coding conventions
- **Success criteria**:
  1. Run any available linters (ruff, etc.)
  2. Check naming conventions, formatting
  3. List violations found with file:line references
- **Worker can**: Read code, run linters
- **Worker cannot**: Make changes
- **Dependencies**: None
- **Status**: Pending

### Task 2.4: Engineering standards audit
- **Scope**: Check against ~/local/soma/docs/concepts/engineering-standards.md
- **Success criteria**:
  1. Verify assertions present (preconditions, postconditions, invariants)
  2. Check test coverage for critical paths
  3. Identify gaps with specific recommendations
- **Worker can**: Read code, read standards doc, analyse
- **Worker cannot**: Make changes
- **Dependencies**: None
- **Status**: Pending

### Task 2.5: Audit files to relocate from cpython to parallel_gc
- **Scope**: Identify benchmark scripts and documentation that should not be in the CPython PR
- **Success criteria**:
  1. List all gc_*_benchmark.py, gc_*_analysis.py, gc_*_experiment.py files in cpython/Lib/test/
  2. List all .md files in cpython/Lib/test/ that are investigation/plan docs
  3. Confirm which test_gc_*.py files should STAY (feature tests)
  4. Recommend target locations in parallel_gc/
- **Worker can**: Read files, list contents, analyse
- **Worker cannot**: Make changes
- **Dependencies**: None
- **Status**: Pending

---

## Phase 3: Documentation Consolidation (Delegated)

### Task 3.1: Archive stale docs
- **Scope**: cpython/docs/ directory (DEVLOG.md, STATUS.md, NEXT_SESSION.md, WORKSPACE.md)
- **Success criteria**:
  1. Extract unique information from DEVLOG.md (atomic mapping table)
  2. Move stale files to archive location
  3. Update any references
- **Worker can**: Read, move files, create archive
- **Worker cannot**: Delete permanently
- **Dependencies**: Step 1.3 complete
- **Status**: Pending

### Task 3.2: Reconcile code comments with design docs
- **Scope**: Compare implementation comments against DESIGN_POST.md, KNOWLEDGE_MANIFOLD.md
- **Success criteria**:
  1. List discrepancies found
  2. For each: which is correct (code or doc)?
  3. Recommendations for fixes
- **Worker can**: Read code, read docs, analyse
- **Worker cannot**: Make changes
- **Dependencies**: Task 2.1 complete (need clean codebase picture)
- **Status**: Pending

---

## Phase 4: Build Verification (Delegated)

### Task 4.1: Build and test on Intel Linux (current machine)
- **Scope**: Full build cycle with tests
- **Success criteria**:
  1. Configure succeeds (debug build)
  2. Make succeeds
  3. test_gc_parallel passes
  4. test_gc_ft_parallel passes
  5. All related tests pass
- **Worker can**: Run configure, make, tests
- **Worker cannot**: Modify source code
- **Dependencies**: Tasks 2.1-2.4 complete (know codebase state)
- **Status**: Pending

### Task 4.2: Benchmark smoke test
- **Scope**: Run quick benchmark to verify infrastructure works
- **Success criteria**:
  1. gc_perf_benchmark.py --quick runs without error
  2. Results are plausible (not obviously broken)
  3. Parallel GC shows some speedup on suitable heap
- **Worker can**: Run benchmarks
- **Worker cannot**: Modify benchmark code
- **Dependencies**: Task 4.1 complete
- **Status**: Pending

---

## Phase 5: Remediation (Supervisor + Workers)

Based on audit findings from Phase 2-3, create remediation tasks. These will be defined after audits complete.

### Task 5.x: [TBD based on audit findings]
- Pattern: One task per remediation area
- Each task has clear success criteria
- Changes committed atomically

---

## Phase 6: Publication Preparation (Future)

After codebase is clean and verified:

### Task 6.1: Apply NBS to benchmarks
### Task 6.2: Run rigorous ARM benchmarks
### Task 6.3: Run rigorous Intel benchmarks
### Task 6.4: Verify Mac build
### Task 6.5: Verify Windows build
### Task 6.6: Draft internal PEP

---

## Execution Model

1. **Phase 1**: Supervisor executes directly, human confirms each step
2. **Phase 2-4**: Workers execute in parallel where no dependencies
3. **Phase 5**: Defined after Phase 2-4 findings, then executed
4. **Phase 6**: Defined after Phase 5 complete

**Worker spawning**: Use pty-session for independent Claude workers
**Reporting**: Workers update their task files in .nbs/workers/
**Supervisor**: Applies 3Ws after each worker, self-check after every 3

---

## Plan Status

- **Created**: 2026-02-06
- **Approved**: Pending human approval
- **Current phase**: Awaiting approval
