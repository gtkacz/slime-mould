"""Pydantic models for the viz HTTP API."""

from __future__ import annotations

from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

ALLOWED_VARIANTS: Final[tuple[str, ...]] = (
    "zipmould-uni-signed",
    "zipmould-uni-positive",
    "zipmould-strat-signed",
    "zipmould-strat-positive",
)

VariantName = Literal[
    "zipmould-uni-signed",
    "zipmould-uni-positive",
    "zipmould-strat-signed",
    "zipmould-strat-positive",
]


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    puzzle_id: str = Field(min_length=1)
    variant: VariantName
    seed: int = Field(ge=0)
    config_overrides: dict[str, Any] = Field(default_factory=dict)


class PuzzleSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    difficulty: str
    N: int
    K: int


class VariantSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    config_path: str
    defaults: dict[str, Any]


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    detail: str


class RunResponse(BaseModel):
    """Wrapper around a JSON-shaped Trace plus a server-issued trace id."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    trace: dict[str, Any]
