# Getting started: build, test and use

## Repositories

- `cpython/` is the `SonicField/cpython` fork (branch
  `parallel-gc-upstream-port`): implementation, build integration, focused
  correctness tests and CPython-facing documentation.
- This parent repository holds the design and evidence documents, CI, the
  benchmark laboratory, raw results and reproducibility records, and pins the
  exact CPython commit.
- `pyperformance/` pins the unmodified upstream suite. Activation, ABBA
  orchestration and provenance live in this repository.

## Obtain the source

```bash
git clone --recurse-submodules https://github.com/SonicField/parallel_gc.git
cd parallel_gc
git submodule update --init --recursive
git ls-tree HEAD cpython          # commit recorded by this parent revision
git -C cpython rev-parse HEAD     # must match
```

The parent's gitlink selects the source, not the submodule's branch setting.
The documents describe CPython `c67363fa59543ef5d572383af927f1cff88514a1`,
based on `python/cpython` `333071231d3a46cccc32d7f44b99328c3299d0b1`.
[VALIDATION.md](VALIDATION.md) records which evidence applies to which source.
The root `Makefile` and scripts under `tools/` belong to an older workflow; do
not use them for current builds or evidence.

## Build

Install CPython's normal
[build dependencies](https://devguide.python.org/getting-started/setup-building/).
A 64-bit target is required. Use one out-of-tree directory per configuration
and never share objects between them; run `make -C <dir> distclean` before
changing an existing directory's configure options.

| Directory | Configure flags | Purpose |
|-----------|-----------------|---------|
| `build-port-gil/` | `--with-pydebug --with-parallel-gc` | GIL parallel collector |
| `build-port-ft/` | `--disable-gil --with-pydebug --with-parallel-gc` | Free-threaded parallel collector |
| `build-baseline-gil/` | `--with-pydebug` | GIL feature-off control |
| `build-baseline-ft/` | `--disable-gil --with-pydebug` | FT feature-off control |

```bash
for cfg in "port-gil:--with-pydebug --with-parallel-gc" \
           "port-ft:--disable-gil --with-pydebug --with-parallel-gc" \
           "baseline-gil:--with-pydebug" \
           "baseline-ft:--disable-gil --with-pydebug"; do
    dir="build-${cfg%%:*}"; mkdir -p "$dir"
    (cd "$dir" && ../cpython/configure ${cfg#*:})
    make -C "$dir" -j"$(nproc)"
done
```

GIL and free-threaded builds are both first-class: a change is not ready
because it works in one. Optimized benchmark builds are described in
[PERFORMANCE.md](PERFORMANCE.md) §2.

## Verify and use

```bash
build-port-ft/python -c "
import gc
print(gc.get_parallel_config())   # 'available': True
gc.enable_parallel(); gc.collect()
print(gc.get_parallel_config(), gc.get_parallel_stats())
gc.disable_parallel()
"
```

Parallel collection is off until `gc.enable_parallel()`; there is no
environment variable, `-X` option or `PyConfig` field. Enabling arms the
collector without creating threads. GIL creates its 16 helpers at the first
collection with at least 16,384 candidates; FT creates 15 helpers at its first
collection, before stopping the world, with the collecting thread as worker
zero. An adaptive controller chooses 2–16 participants. If the pool cannot
start, the collection completes serially, one `RuntimeWarning` is issued and
later collections stay serial until another explicit enable. Without
`--with-parallel-gc`, enable and disable raise `RuntimeError` and
`get_parallel_config()` reports `available: False`. Details:
[DESIGN.md](DESIGN.md) §5–7.

## Focused tests

```bash
build-port-gil/python -m test -j4 \
    test_gc test_gc_ft_parallel test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_fork test_gc_parallel_properties \
    test_gc_parallel_mark_alive test_parallel_gc_profile \
    test_capi.test_config test_embed

build-port-ft/python -m test -j4 \
    test_gc test_gc_ft_parallel test_gc_ws_deque test_gc_parallel \
    test_gc_parallel_fork test_gc_parallel_properties \
    test_parallel_gc_profile test_capi.test_config test_embed \
    test_free_threading.test_gc
```

Run the same lists (without `test_gc_parallel_mark_alive` and
`test_parallel_gc_profile`) in the two baseline builds when a result might come
from the port rather than the collector; they also check that the API reports
the feature unavailable. Build-specific modules skip in the other mode;
investigate any unexplained skip in the active mode. The module-by-module
coverage table, CI workflows and evidence required per change type are in
[TESTING.md](TESTING.md).

## Broad regression runs

Run the full suite separately in both feature-on builds and keep the command,
seed, summary, failures and skips:

```bash
build-port-gil/python -m test -q -j4 --timeout=300 --fail-env-changed \
    --randseed=20260929 -x test_cext test_multiprocessing_fork \
    test_multiprocessing_forkserver test_multiprocessing_spawn

build-port-ft/python -m test -q -j4 --timeout=300 --fail-env-changed \
    --randseed=20260929 -x test_cext test_free_threading \
    test_multiprocessing_fork test_multiprocessing_forkserver \
    test_multiprocessing_spawn
```

The exclusions are environmental on the development host and must stay
visible: `test_cext` needs unavailable build dependencies; the three
multiprocessing modules hit an upstream `NameError` that the feature-off build
reproduces; the FT `test_free_threading` package imports the unavailable
optional `_ctypes`. The hosted full-suite workflow runs without exclusions; see
[TESTING.md](TESTING.md).

## Sanitizers

Use separate directories: ASan with `CC=clang CXX=clang++` and
`--with-address-sanitizer`; TSan (recorded with GCC 11.5.0) with
`--with-thread-sanitizer`. Run the focused lists. Use `ASAN_OPTIONS=detect_leaks=0` and
`TSAN_OPTIONS='halt_on_error=1 die_after_fork=0'`; GCC TSan otherwise kills a
child that starts threads after a multithreaded fork. On the AArch64
development host, GCC's `libtsan.so` linker script names
`/usr/lib64/libtsan.so.0.0.0`, which is not installed; install
`libtsan-11.5.0-15.el9.aarch64` or extract it and pass its directory with
`LDFLAGS=-Wl,-rpath,...`. Exact recorded commands, results and suppressions are
in [TESTING.md](TESTING.md). These are bounded selections, not exhaustive race
or memory coverage.

## Recorded results

Current local and remote evidence, and the runs still required for the
published source pair, are in [VALIDATION.md](VALIDATION.md). Earlier
four-configuration and broad-suite results (for example 47,914 FT and 48,103
GIL tests at predecessor `9da963f754`) are historical and listed in
`BUILD_AND_TEST.md` (removed; `git show 724b74b:docs/BUILD_AND_TEST.md`); they do not validate
later code.

## Layout

```text
parallel_gc/
  cpython/        authoritative CPython submodule
  pyperformance/  pinned upstream benchmark suite
  docs/           active documents (superseded ones are in git history)
  benchmarks/     benchmark drivers and raw results
  Makefile, tools/  legacy workflow (do not use)
```

Next: [DESIGN.md](DESIGN.md) for the collectors,
[PERFORMANCE.md](PERFORMANCE.md) for measurement,
[OPEN_ISSUES.md](OPEN_ISSUES.md) for what is unresolved.
