# SQLAlchemy pure-Python benchmark compatibility

Status: pure-Python implementation approved and verified on 19 October 2026. No SQLAlchemy benchmark program has been removed or changed, and no unsafe GIL override has been used.

Updating Greenlet resolves its own FT import failure, but exposes SQLAlchemy's native modules. With the original **SQLAlchemy 1.4.19**, `sqlalchemy.cprocessors` enables the GIL; both original benchmark programs remain rejected by the worker hook. The latest 1.4 release, **1.4.54**, also enables the GIL, starting with `cimmutabledict`. Its source has no FT-safe declaration on these native modules.

The two benchmark programs are `sqlalchemy_declarative` and `sqlalchemy_imperative`. Their four failed baseline FT enabled/disabled checks, the 1.4.54 native build, and the failing import check are preserved in [sqlalchemy-evidence](sqlalchemy-evidence/). The latest import starts GIL-disabled and ends GIL-enabled; the check exits 1.

## Why not upgrade to SQLAlchemy 2?

The original imperative program calls `Delete.execute()`, `Insert.execute()` and `Select.execute()` through bound metadata. SQLAlchemy 2 removes this connectionless execution API. Rewriting it to use explicit connections would change benchmark code and transaction handling. That is outside the agreed dependency-only repair.

## Approved implementation

Alex approved retaining SQLAlchemy 1.4.19 and building its supported **pure-Python implementation**, using it identically on baseline/current and GIL/FT. Benchmark programs and workload parameters remain unchanged, but this implementation differs from historical native-extension runs. Report and keep those results separate.

Build separately using each target Python:

```bash
DISABLE_SQLALCHEMY_CEXT=1 \
  "$target_python" -m pip wheel --no-cache-dir --no-deps \
  --no-binary=sqlalchemy --wheel-dir "$wheel_directory" sqlalchemy==1.4.19
```

Both wheels contain zero native extensions, and their `sqlalchemy/` package files are byte-identical across GIL/FT. Their platform-specific wheel tags are retained, not manually rewritten. Use the same mode-specific wheel for baseline/current.

## Verification

The new [test_sqlalchemy_pure.py](test_sqlalchemy_pure.py) fails against the original native FT environment: native-module presence and GIL-enabled execution violate the contract. With the approved build all three tests pass on every baseline/current GIL/FT binary. Both original workload functions execute with 100 rows; the tests independently check both database row counts. No native SQLAlchemy modules are discoverable, and FT remains GIL-disabled.

Both unchanged benchmark programs also pass all eight source/build/policy combinations, producing sixteen correctly attested short results. [Tests, build logs, failing control and raw results](sqlalchemy-pure-evidence/). These are correctness checks, not performance measurements.

- GIL wheel SHA-256: `b5cc72ab108916e9e68c7c109015173c43f4ebb27b61c72c4e3d0c2473867422`.
- FT wheel SHA-256: `629a8830c152fa325e0e28e4af46244d1bac7e2f85bae622ef36c37e11c22e55`.

All seven dependency repairs now pass targeted checks. Fresh complete environments, repeated full-default readiness and the sixteen rigorous comparisons remain separate requirements; targeted checks are not advertised as a complete default suite.
