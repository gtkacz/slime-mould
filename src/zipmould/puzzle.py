"""Outer-layer puzzle representation.

`Puzzle` is the canonical, immutable view of a single Zip puzzle as
loaded from `benchmark/data/puzzles.cbor`. The kernel never sees these
objects; `solver.state.pack` projects them into NumPy arrays.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal, cast

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

    def L(self) -> int:  # noqa: N802
        return self.N * self.N - len(self.blocked)


def _from_cbor_dict(raw_obj: object) -> Puzzle:
    raw = cast("dict[str, Any]", raw_obj)
    difficulty = cast("str", raw["difficulty"])
    if difficulty not in _VALID_DIFFICULTIES:
        msg = f"unknown difficulty {difficulty!r} in puzzle {raw.get('id')!r}"
        raise ValueError(msg)

    waypoints = tuple((int(r), int(c)) for r, c in raw["waypoints"])
    walls = frozenset(_canonical_edge((int(a[0]), int(a[1])), (int(b[0]), int(b[1]))) for a, b in raw["walls"])
    blocked = frozenset((int(r), int(c)) for r, c in raw["blocked"])

    return Puzzle(
        id=str(raw["id"]),
        name=str(raw["name"]),
        difficulty=cast("Difficulty", difficulty),
        N=int(raw["N"]),
        K=int(raw["K"]),
        waypoints=waypoints,
        walls=walls,
        blocked=blocked,
    )


def load_puzzles_cbor(path: Path) -> dict[str, Puzzle]:
    """Load all puzzles from `path`, keyed by `puzzle.id`."""
    with path.open("rb") as f:
        payload = cast("dict[str, Any]", cbor2.load(f))
    raw_list = cast("list[dict[str, Any]]", payload["puzzles"])
    return {str(p["id"]): _from_cbor_dict(p) for p in raw_list}
