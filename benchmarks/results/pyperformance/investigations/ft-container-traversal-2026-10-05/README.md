# Free-threaded container traversal exploratory evidence

## Scope

These files preserve the exploratory `gc_traversal` campaigns used to decide whether exact-container traversal warrants a controlled optimization investigation. They are not final acceptance evidence.

All three campaigns ran on `devbig340.ncg1.facebook.com`, a 72-logical-CPU AArch64 host running Linux `6.16.1-0_fbk3_0_gd6c130b80483`. The target was a CPython 3.16 free-threaded PGO+LTO build configured with `--with-parallel-gc --disable-gil --enable-optimizations --with-lto` and GCC 11.5.0.

## Preserved campaigns

| Directory | CPython state | Disabled mean | Enabled mean | Observation |
|-----------|---------------|--------------:|-------------:|-------------|
| `baseline/` | Clean `01a89cbeb84b41931a3f30875022cc854d210fc8` | 1.57 ms | 2.81 ms | Parallel was 1.79x slower. |
| `forced-inline/` | `01a89cbeb8` plus forced inlining of `_PyGC_TryMarkAlive` | 1.58 ms | 2.83 ms | Parallel remained 1.79x slower; the experiment was reverted. |
| `direct-list/` | `01a89cbeb8` plus `direct-list-experiment.patch` | 1.57 ms | 1.98 ms | Parallel was 1.26x slower; this failed to falsify the direct-list hypothesis. |

Each directory retains the four raw pyperformance results in disabled, enabled, enabled, disabled order, the two combined results, the pyperformance comparison, and `campaign.json`. The campaign file records commands, build configuration, repository state, host identity, timestamps, preflight mode attestation, and SHA-256 hashes of every result file.

## Experimental patch identity

The uncommitted direct-list diff is preserved in `direct-list-experiment.patch`. Its SHA-256 is `b7520df6e6992d6c41424e82fc20412c785f8ab6099076abf4e8bef9c7f8a976` when produced by `git diff --binary -- Python/gc_free_threading_parallel.c` from CPython revision `01a89cbeb84b41931a3f30875022cc854d210fc8`.

The candidate executable used by the direct-list campaign remained available when this evidence was archived:

- Path: `/data/users/alexturner/parallel_gc/build-pyperformance-ft/python`
- SHA-256: `44e5b80b73c46d48f7b057682a2ea3322d36e71b4d6fe8516c9314d4e8ecf505`
- ELF build ID: `dbb823d6972e450f61fe8206d5d95228d4ac86b8`
- Version timestamp recorded by the campaign: `Oct 5 2026, 10:17:58`

## Limitations

- The baseline executable was overwritten before its executable hash and build ID were recorded. Its source revision, build configuration, compiler, version timestamp, campaign files, and result hashes remain recorded, but the binary itself cannot be authenticated now.
- These campaigns compare enabled and disabled modes within one binary. They do not alternate the baseline and candidate binaries with parallel GC enabled in both.
- CPU affinity was not fixed; `campaign.json` records `affinity` as null.
- The parent repository and pyperformance submodule were dirty. Their exact recorded states appear in each `campaign.json`.
- The direct-list patch had passed the four focused free-threaded parallel-GC test files, but it did not yet have the adversarial exact-container contract tests required by the optimization plan.

Consequently, these files justify the next experiment but cannot satisfy the retention gate. A fresh baseline/candidate binary ABBA campaign with complete executable identity remains mandatory.
