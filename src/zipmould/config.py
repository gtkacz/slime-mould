"""Pydantic v2 configuration models for the solver and experiments.

`SolverConfig` is the per-puzzle solver knob set; `ExperimentManifest`
declares Stage-N batches. String sentinels `"N_squared"` and
`"10_N_squared"` for `beta1`/`beta3` survive TOML round-trips and
are materialised inside `solver.state.pack(puzzle, config)`.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

_BETA1_DEFAULT: Final[str] = "N_squared"
_BETA3_DEFAULT: Final[str] = "10_N_squared"


class SolverConfig(BaseModel):
    """Validated solver knobs. Extension: `tau_signed` covers design.md §6.1's
    pos/signed axis missing from the impl spec §4.2."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    gamma_man: float = Field(default=1.0, ge=0.0)
    gamma_warns: float = Field(default=1.0, ge=0.0)
    gamma_art: float = Field(default=1.0, ge=0.0)
    gamma_par: float = Field(default=0.5, ge=0.0)

    alpha: float = Field(default=1.0, ge=0.0)
    beta: float = Field(default=2.0, ge=0.0)

    beta1: float | Literal["N_squared"] = _BETA1_DEFAULT
    beta2: float = Field(default=1.0, ge=0.0)
    beta3: float | Literal["10_N_squared"] = _BETA3_DEFAULT
    tau_max: float = Field(default=10.0, gt=0.0)
    z: float = Field(default=0.05, ge=0.0, le=1.0)
    tau_0: float = 0.0

    population: int = Field(default=30, ge=1)
    iter_cap: int = Field(default=200, ge=1)
    wall_clock_s: float = Field(default=300.0, gt=0.0)

    pheromone_mode: Literal["unified", "stratified"] = "unified"
    tau_signed: bool = True

    visible_walkers: int = Field(default=5, ge=0)
    frame_interval: int = Field(default=5, ge=1)
    tau_delta_epsilon: float = Field(default=1e-3, ge=0.0)

    @field_validator("beta1")
    @classmethod
    def _check_beta1(cls, v: float | str) -> float | str:
        if isinstance(v, str) and v != _BETA1_DEFAULT:
            msg = f"beta1 string sentinel must be {_BETA1_DEFAULT!r}, got {v!r}"
            raise ValueError(msg)
        if isinstance(v, int | float) and v < 0:
            msg = "beta1 must be non-negative"
            raise ValueError(msg)
        return v

    @field_validator("beta3")
    @classmethod
    def _check_beta3(cls, v: float | str) -> float | str:
        if isinstance(v, str) and v != _BETA3_DEFAULT:
            msg = f"beta3 string sentinel must be {_BETA3_DEFAULT!r}, got {v!r}"
            raise ValueError(msg)
        if isinstance(v, int | float) and v < 0:
            msg = "beta3 must be non-negative"
            raise ValueError(msg)
        return v

    @classmethod
    def from_toml(cls, path: Path) -> Self:
        with path.open("rb") as f:
            data = tomllib.load(f)
        body = data.get("solver", data)
        return cls.model_validate(body)

    def canonical_json(self) -> bytes:
        d = self.model_dump(mode="json")
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def config_hash(self) -> str:
        return hashlib.blake2b(self.canonical_json(), digest_size=16).hexdigest()


class ConditionEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    solver: Literal["zipmould", "random_walk", "heuristic_only", "aco_vanilla", "backtracking"]
    config: str


class ExperimentManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    stage: str
    split: Literal["train", "dev", "test"]
    seeds: tuple[int, ...]
    global_seed: int = Field(ge=0)
    conditions: tuple[ConditionEntry, ...]
    trace_seed: int = Field(default=0, ge=0)
    output_dir: str

    @classmethod
    def from_toml(cls, path: Path) -> Self:
        with path.open("rb") as f:
            data = tomllib.load(f)
        return cls.model_validate(data)


class ConfigError(ValueError):
    """Raised when a TOML config fails validation."""
