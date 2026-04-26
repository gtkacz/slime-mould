"""Regression tests for kernel state construction."""

from __future__ import annotations

from zipmould.config import SolverConfig
from zipmould.puzzle import Puzzle
from zipmould.solver.state import pack


def test_pack_removes_walled_edges_from_adjacency() -> None:
    puzzle = Puzzle(
        id="wall-edge",
        name="wall-edge",
        difficulty="Easy",
        N=2,
        K=2,
        waypoints=((0, 0), (1, 1)),
        walls=frozenset({((0, 0), (0, 1))}),
        blocked=frozenset(),
    )

    state = pack(puzzle, SolverConfig())

    left = 0
    right = 1
    assert right not in set(int(c) for c in state.adjacency[left] if c >= 0)
    assert left not in set(int(c) for c in state.adjacency[right] if c >= 0)
