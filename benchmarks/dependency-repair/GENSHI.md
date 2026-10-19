# Genshi Python 3.16 compatibility

Repair: retain Genshi **0.7.7**, the benchmark's original dependency, and supply AST fields when constructing nodes. Python 3.16 no longer permits creating a required-field node empty and filling its fields afterwards. Genshi 0.7.11 still has the same failure, so merely upgrading does not solve it.

The patch changes AST cloning, the expression/module wrappers and the `_new()` helper. Cloning still recursively visits the same fields and copies the same source attributes. It also repairs the helper's pre-existing keyword iteration bug (`kwargs` instead of `kwargs.items()`), exposed by testing required fields supplied as keywords. Duplicate positional/keyword fields retain the existing `ValueError`.

## Verification

- Tests were written and failed before the repair: [unpatched-gil.log](genshi-evidence/unpatched-gil.log).
- Eight tests pass on baseline/current GIL/FT optimized Python 3.16 binaries: cloning preserves AST fields and locations; string/AST expressions and suites produce the expected values; keyword and duplicate-field handling work; XML/text output is correct; both original benchmark functions execute; FT remains GIL-disabled.
- The same eight tests pass on Python 3.12, with upstream AST deprecation warnings.
- The **unchanged original XML and text benchmark programs** pass all eight baseline/current × GIL/FT × enabled/disabled short checks. Sixteen saved workload results contain the expected activation metadata; all FT results attest GIL-disabled execution. Raw JSON, logs and target test logs are in [genshi-evidence](genshi-evidence/).
- Applying the checked-in patch to a second unpacking produces byte-identical repaired source files.

These are correctness/readiness checks, not performance measurements or a claim that the entire Genshi library supports Python 3.16.

## Reproduce

Use the isolated wheel unpack/patch/pack procedure in [CLOUDPICKLE.md](CLOUDPICKLE.md), substituting:

- dependency `genshi==0.7.7`;
- original wheel `Genshi-0.7.7-py3-none-any.whl`;
- unpacked directory `Genshi-0.7.7`;
- patch `genshi-0.7.7-python316.patch`;
- test script `test_genshi_316.py`.

Install the repaired wheel identically in fresh baseline/current GIL/FT benchmark environments. Retain `six==1.17.0`, already present in the original benchmark environments. Do not modify the pyperformance submodule or publish this wheel as an upstream release.

## Provenance

- Original wheel SHA-256: `bed85e4015485a808bdd8d5bbb25cdc5fc093efab50776e2888be7b45b46f084`.
- Patch SHA-256: `fa4b9b82bd93ba9f5ca29817f50dc9f8b937dc82814de67979708544cc76f265`.
- Tested repaired wheel SHA-256: `95b93a31421b4ac57bccd854e16486ebe1cee76a09ac29c48af13abec54d907c`. Wheel archive timestamps can vary when repacked.
- Baseline/current binaries and diagnostic dependency-overlay method are the same as [the Cloudpickle check](CLOUDPICKLE.md). Historical benchmark environments remain unchanged.
