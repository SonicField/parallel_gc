# Sanitiser Build Scripts — Rescue Notes

**Captured:** 2026-05-29 during the 3.15 consolidation pass.

These `.original` scripts were preserved from the soon-to-be-deleted `cpython-asan/`, `cpython-tsan/`, `cpython-release/`, and the original `cpython/` worktrees. They are kept verbatim for reference. Paths inside are hardcoded to those worktrees and **will not work as-is** after Phase 1 deletion.

Phase 4 of the consolidation will refactor them to operate against the consolidated `parallel_gc/cpython/` tree.

## Critical institutional knowledge captured here

### The `configure` → `pyconfig.h` bug

Every script contains this manual fix:

```bash
sed -i 's|/\* #undef Py_PARALLEL_GC \*/|#define Py_PARALLEL_GC 1|' pyconfig.h
```

**Cause:** `./configure --with-parallel-gc` does not emit `#define Py_PARALLEL_GC 1` in `pyconfig.h`. It writes `/* #undef Py_PARALLEL_GC */` (the unset state), so the parallel-GC code is not actually compiled despite the configure flag being accepted.

**Workaround:** patch `pyconfig.h` after `./configure`, before `make`.

**Real fix (Phase 4 candidate):** the autoconf macro for `--with-parallel-gc` needs to be repaired so the `#define` is emitted. Until then, every build script must apply the `sed` workaround.

### ASan/TSan flag injection

Sanitiser scripts inject `-fsanitize=address` (or `thread`) into `BASECFLAGS` and `CONFIGURE_LDFLAGS` via `sed` on the generated `Makefile`. This is fragile (depends on Makefile structure) but works.

```bash
# ASan
sed -i 's/^BASECFLAGS=\t/BASECFLAGS=\t -fsanitize=address/' Makefile
sed -i 's/^CONFIGURE_LDFLAGS=.*/CONFIGURE_LDFLAGS=\t-fsanitize=address/' Makefile

# TSan
sed -i 's/^BASECFLAGS=\t/BASECFLAGS=\t -fsanitize=thread/' Makefile
sed -i 's/^CONFIGURE_LDFLAGS=.*/CONFIGURE_LDFLAGS=\t-fsanitize=thread/' Makefile
```

### Compilers used

- ASan/TSan: `clang` (CC=clang CXX=clang++)
- Release: `gcc` (CC=gcc CFLAGS="-O3")
- Debug-no-sanitiser: `gcc` (CC=gcc CFLAGS='-O2 -g')

### Verification command after build

```bash
./python -c "import gc; print(gc.get_parallel_config())"
```

Should print the parallel-GC config (worker count, etc.) — confirms the macro was actually defined at compile time, not just configured.
