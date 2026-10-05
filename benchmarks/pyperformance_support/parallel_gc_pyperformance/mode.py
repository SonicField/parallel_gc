"""Apply and verify the requested parallel-GC benchmark mode."""

import gc


MODE_ENV = "PARALLEL_GC_PYPERFORMANCE_MODE"
VERIFIED_PID_ENV = "PARALLEL_GC_PYPERFORMANCE_VERIFIED_PID"
RUN_ID_ENV = "PYPERFORMANCE_RUNID"
MODES = frozenset(("enabled", "disabled", "feature-off"))


def _get_config(gc_module=gc):
    get_config = getattr(gc_module, "get_parallel_config", None)
    if get_config is None:
        return {"available": False, "enabled": False, "num_workers": 0}
    config = get_config()
    if not isinstance(config, dict):
        raise RuntimeError("gc.get_parallel_config() did not return a dict")
    return config


def verify_mode(mode, gc_module=gc):
    """Return the current configuration if it matches *mode*."""
    if mode not in MODES:
        raise RuntimeError(f"unknown parallel-GC benchmark mode: {mode!r}")

    config = _get_config(gc_module)
    available = config.get("available") is True
    enabled = config.get("enabled") is True

    if mode == "enabled" and not (available and enabled):
        raise RuntimeError(
            "parallel GC was requested but is not available and enabled: "
            f"{config!r}"
        )
    if mode == "disabled" and not (available and not enabled):
        raise RuntimeError(
            "runtime-disabled mode requires an available, disabled collector: "
            f"{config!r}"
        )
    if mode == "feature-off" and (available or enabled):
        raise RuntimeError(
            "feature-off mode requires a build without parallel GC: "
            f"{config!r}"
        )
    return config


def apply_mode(mode, gc_module=gc):
    """Apply *mode* and return the verified resulting configuration."""
    if mode == "enabled":
        enable = getattr(gc_module, "enable_parallel", None)
        if enable is None:
            raise RuntimeError("gc.enable_parallel() is not available")
        enable()
    elif mode == "disabled":
        disable = getattr(gc_module, "disable_parallel", None)
        if disable is None:
            raise RuntimeError("gc.disable_parallel() is not available")
        disable()
    elif mode != "feature-off":
        raise RuntimeError(f"unknown parallel-GC benchmark mode: {mode!r}")
    return verify_mode(mode, gc_module)
