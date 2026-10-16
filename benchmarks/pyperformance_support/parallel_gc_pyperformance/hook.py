"""A pyperf hook that verifies and records the parallel-GC mode."""

import os
from pathlib import Path
import sys
import sysconfig

from pyperf._hooks import HookError

from .mode import MODE_ENV, VERIFIED_PID_ENV, apply_mode, verify_mode


class ParallelGCHook:
    def __init__(self):
        mode = os.environ.get(MODE_ENV)
        if mode is None:
            raise HookError(f"{MODE_ENV} is not set")
        if Path(sys.argv[0]).name == "_process_time.py":
            self.active = False
            self.mode = mode
            self.config = None
            self.entries = 0
            return
        self.active = True
        self.mode = mode
        try:
            self.config = apply_mode(mode)
        except RuntimeError as exc:
            raise HookError(str(exc)) from exc
        os.environ[VERIFIED_PID_ENV] = str(os.getpid())
        self.entries = 0

    def _verify(self):
        if os.environ.get(VERIFIED_PID_ENV) != str(os.getpid()):
            raise HookError("parallel-GC activation belongs to another process")
        try:
            return verify_mode(self.mode)
        except RuntimeError as exc:
            raise HookError(str(exc)) from exc

    def __enter__(self):
        if not self.active:
            return self
        self.config = self._verify()
        self.entries += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.active:
            return False
        self.config = self._verify()
        return False

    def teardown(self, metadata):
        if not self.active:
            return
        self.config = self._verify()
        # Check after workload imports and outside the timed sections. An FT
        # extension can enable the GIL, invalidating the intended comparison.
        free_threaded = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
        probe = getattr(sys, "_is_gil_enabled", None)
        if probe is None and free_threaded:
            raise HookError("Cannot verify the free-threaded runtime GIL state")
        gil_enabled = bool(probe()) if probe is not None else True
        if free_threaded and gil_enabled:
            raise HookError("Free-threaded benchmark ran with the GIL enabled")
        if not free_threaded and not gil_enabled:
            raise HookError("GIL-build benchmark ran with the GIL disabled")
        metadata["parallel_gc_build_gil_disabled"] = free_threaded
        metadata["parallel_gc_runtime_gil_enabled"] = gil_enabled
        metadata["parallel_gc_mode"] = self.mode
        metadata["parallel_gc_available"] = bool(
            self.config.get("available", False)
        )
        metadata["parallel_gc_enabled"] = bool(
            self.config.get("enabled", False)
        )
        metadata["parallel_gc_num_workers"] = int(
            self.config.get("num_workers", 0)
        )
        if "adaptive_workers" in self.config:
            metadata["parallel_gc_adaptive_workers"] = int(
                self.config["adaptive_workers"]
            )
        metadata["parallel_gc_hook_entries"] = self.entries
