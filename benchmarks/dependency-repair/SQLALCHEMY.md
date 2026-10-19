# SQLAlchemy: unresolved native FT compatibility

Status: decision required. No SQLAlchemy benchmark program has been removed or changed, and no unsafe GIL override has been used.

Updating Greenlet resolves its own FT import failure, but exposes SQLAlchemy's native modules. With the original **SQLAlchemy 1.4.19**, `sqlalchemy.cprocessors` enables the GIL; both original benchmark programs remain rejected by the worker hook. The latest 1.4 release, **1.4.54**, also enables the GIL, starting with `cimmutabledict`. Its source has no FT-safe declaration on these native modules.

The two benchmark programs are `sqlalchemy_declarative` and `sqlalchemy_imperative`. Their four failed baseline FT enabled/disabled checks, the 1.4.54 native build, and the failing import check are preserved in [sqlalchemy-evidence](sqlalchemy-evidence/). The latest import starts GIL-disabled and ends GIL-enabled; the check exits 1.

## Why not upgrade to SQLAlchemy 2?

The original imperative program calls `Delete.execute()`, `Insert.execute()` and `Select.execute()` through bound metadata. SQLAlchemy 2 removes this connectionless execution API. Rewriting it to use explicit connections would change benchmark code and transaction handling. That is outside the agreed dependency-only repair.

## Choice to discuss

The bounded alternative is to retain SQLAlchemy 1.4.19 and build its supported **pure-Python implementation**, using that implementation identically on baseline/current and GIL/FT. The benchmark programs and workload parameters would remain unchanged, but the implementation being benchmarked would differ from historical native-extension runs. Report and keep those results separate.

This requires explicit agreement before execution. The other alternative is separate work to obtain a genuinely FT-safe native implementation compatible with the original 1.4 benchmark API. Simply asserting FT safety or forcing `PYTHON_GIL=0` is not a repair.

Until that choice is made, full-default FT readiness and the sixteen rigorous comparisons are incomplete. The six other dependency repairs are verified in isolated environments, not advertised as a complete repaired default suite.
