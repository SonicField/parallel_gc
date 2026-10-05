"""A pyperf hook that verifies and records the parallel-GC mode."""

import os
from pathlib import Path
import sys

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
