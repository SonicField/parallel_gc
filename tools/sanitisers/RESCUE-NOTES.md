# Sanitizer Script History

The `*.original` files in this directory are snapshots from former separate
CPython worktrees. Their paths and build procedures are obsolete; retain them
only as development history.

In particular, an old note claimed that `--with-parallel-gc` failed to define
`Py_PARALLEL_GC` and required editing `pyconfig.h`. That problem is not present
in the current tree. The supported configure option emits the definition, and
the project must not patch generated headers after configuration.

`build-asan.sh` and `build-tsan.sh` are newer in-place wrappers, but they are
still provisional:

- they build only the GIL configuration;
- they require Clang and the normal CPython build dependencies;
- they run `make distclean` unconditionally, so they require an existing
  generated Makefile;
- their suggested test commands cover only the GIL implementation.

Use the explicit, mode-specific procedures in
[BUILD_AND_TEST.md](../../docs/BUILD_AND_TEST.md) until the wrappers cover both
GIL and free-threaded builds and have been validated from a fresh checkout.
