"""Adapter from a `RunRequest` to a JSON-shaped Trace plus its CBOR bytes."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from zipmould.config import SolverConfig
from zipmould.puzzle import Puzzle
from zipmould.solver.api import solve
from zipmould.viz.trace_codec import trace_to_jsonable, write_cbor_bytes

_CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "configs" / "ablations"
_BASE_CONFIG = Path(__file__).parent.parent.parent.parent / "configs" / "default.toml"


class RunnerError(RuntimeError):
    """Raised when the runner cannot complete a solve cleanly."""


def _load_variant_defaults(variant: str) -> dict[str, Any]:
    """Merge `configs/default.toml` with the variant override TOML."""
    variant_path = _CONFIG_DIR / f"{variant}.toml"
    if not _BASE_CONFIG.exists():
        msg = f"missing base config: {_BASE_CONFIG}"
        raise RunnerError(msg)
    if not variant_path.exists():
        msg = f"unknown variant config: {variant_path}"
        raise RunnerError(msg)
    with _BASE_CONFIG.open("rb") as f:
        merged = tomllib.load(f).get("solver", {})
    with variant_path.open("rb") as f:
        merged.update(tomllib.load(f).get("solver", {}))
    return merged


def build_config(variant: str, overrides: dict[str, Any]) -> SolverConfig:
    """Compose a SolverConfig from variant defaults plus user overrides."""
    merged = _load_variant_defaults(variant)
    merged.update(overrides)
    return SolverConfig.model_validate(merged)


def run_solve(
    puzzle: Puzzle,
    variant: str,
    seed: int,
    config_overrides: dict[str, Any],
) -> tuple[dict[str, Any], bytes]:
    """Execute a synchronous solve and return (trace_dict, cbor_bytes).

    Raises RunnerError if the puzzle is statically infeasible (so the API
    can return 422 rather than a half-baked trace).
    """
    cfg = build_config(variant, config_overrides)
    result = solve(
        puzzle,
        cfg,
        seed=seed,
        trace=True,
        global_seed=0,
        condition=variant,
    )
    if result.infeasible or result.trace is None:
        reason = result.feasibility_reason or "no trace produced"
        msg = f"infeasible: {reason}"
        raise RunnerError(msg)
    trace_dict = trace_to_jsonable(result.trace)
    cbor_bytes = write_cbor_bytes(result.trace)
    return trace_dict, cbor_bytes
