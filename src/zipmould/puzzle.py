"""Outer-layer puzzle representation.

`Puzzle` is the canonical, immutable view of a single Zip puzzle as
loaded from `benchmark/data/puzzles.cbor`. The kernel never sees these
objects; `solver.state.pack` projects them into NumPy arrays.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

import cbor2

Coord = tuple[int, int]
Edge = tuple[Coord, Coord]

Difficulty = Literal["Easy", "Medium", "Hard"]

_VALID_DIFFICULTIES: Final[frozenset[str]] = frozenset({"Easy", "Medium", "Hard"})


def _canonical_edge(a: Coord, b: Coord) -> Edge:
    return (a, b) if a <= b else (b, a)


@dataclass(frozen=True, slots=True)
class Puzzle:
    id: str
    name: str
    difficulty: Difficulty
    N: int
    K: int
    waypoints: tuple[Coord, ...]
    walls: frozenset[Edge]
    blocked: frozenset[Coord]

    def free_cells(self) -> frozenset[Coord]:
        all_cells = {(r, c) for r in range(self.N) for c in range(self.N)}
        return frozenset(all_cells - self.blocked)

    def L(self) -> int:
        return self.N * self.N - len(self.blocked)


def _from_cbor_dict(raw: dict[str, object]) -> Puzzle:
    difficulty = raw["difficulty"]
    if difficulty not in _VALID_DIFFICULTIES:
        msg = f"unknown difficulty {difficulty!r} in puzzle {raw.get('id')!r}"
        raise ValueError(msg)

    waypoints_raw = raw["waypoints"]
    walls_raw = raw["walls"]
    blocked_raw = raw["blocked"]

    waypoints = tuple((int(r), int(c)) for r, c in waypoints_raw)  # type: ignore[union-attr]
    walls = frozenset(
        _canonical_edge((int(a[0]), int(a[1])), (int(b[0]), int(b[1])))
        for a, b in walls_raw  # type: ignore[union-attr]
    )
    blocked = frozenset((int(r), int(c)) for r, c in blocked_raw)  # type: ignore[union-attr]

    return Puzzle(
        id=str(raw["id"]),
        name=str(raw["name"]),
        difficulty=difficulty,  # type: ignore[arg-type]
        N=int(raw["N"]),  # type: ignore[arg-type]
        K=int(raw["K"]),  # type: ignore[arg-type]
        waypoints=waypoints,
        walls=walls,
        blocked=blocked,
    )


def load_puzzles_cbor(path: Path) -> dict[str, Puzzle]:
    """Load all puzzles from `path`, keyed by `puzzle.id`."""
    with path.open("rb") as f:
        payload = cbor2.load(f)
    raw_list = payload["puzzles"]
    return {p["id"]: _from_cbor_dict(p) for p in raw_list}
