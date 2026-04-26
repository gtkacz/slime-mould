"""API schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from zipmould.viz.schemas import ALLOWED_VARIANTS, RunRequest


def test_run_request_minimal_payload() -> None:
    req = RunRequest.model_validate(
        {"puzzle_id": "level_1", "variant": "zipmould-uni-positive", "seed": 0}
    )
    assert req.puzzle_id == "level_1"
    assert req.variant == "zipmould-uni-positive"
    assert req.seed == 0
    assert req.config_overrides == {}


def test_run_request_with_overrides() -> None:
    req = RunRequest.model_validate(
        {
            "puzzle_id": "level_1",
            "variant": "zipmould-uni-positive",
            "seed": 7,
            "config_overrides": {"alpha": 1.5, "iter_cap": 500},
        }
    )
    assert req.config_overrides == {"alpha": 1.5, "iter_cap": 500}


def test_run_request_rejects_unknown_variant() -> None:
    with pytest.raises(ValidationError):
        RunRequest.model_validate(
            {"puzzle_id": "x", "variant": "nope", "seed": 0}
        )


def test_allowed_variants_lists_four_zipmould_kinds() -> None:
    assert sorted(ALLOWED_VARIANTS) == [
        "zipmould-strat-positive",
        "zipmould-strat-signed",
        "zipmould-uni-positive",
        "zipmould-uni-signed",
    ]
