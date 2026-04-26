"""End-to-end runner: solve a tiny puzzle and verify the trace shape."""

from __future__ import annotations

from zipmould.puzzle import Puzzle
from zipmould.viz.runner import run_solve


def _tiny_puzzle() -> Puzzle:
    """A 3x3 grid with waypoints in opposite corners; trivially solvable."""
    return Puzzle(
        id="tiny",
        name="tiny",
        difficulty="Easy",
        N=3,
        K=2,
        waypoints=((0, 0), (2, 2)),
        walls=frozenset(),
        blocked=frozenset(),
    )


def test_runner_returns_trace_and_bytes() -> None:
    trace_dict, cbor_bytes = run_solve(
        puzzle=_tiny_puzzle(),
        variant="zipmould-uni-positive",
        seed=0,
        config_overrides={"iter_cap": 200, "population": 8},
    )
    assert trace_dict["puzzle_id"] == "tiny"
    assert isinstance(trace_dict["frames"], list)
    assert len(trace_dict["frames"]) > 0
    assert cbor_bytes[:2] != b""  # non-empty


def test_runner_applies_overrides() -> None:
    expected_iter_cap = 50
    expected_population = 4
    trace_dict, _ = run_solve(
        puzzle=_tiny_puzzle(),
        variant="zipmould-uni-positive",
        seed=0,
        config_overrides={"iter_cap": expected_iter_cap, "population": expected_population},
    )
    cfg = trace_dict["config"]
    assert cfg["iter_cap"] == expected_iter_cap
    assert cfg["population"] == expected_population
