"""Parse benchmark/data/raw.json into the custom CBOR puzzle format.

Outputs benchmark/data/puzzles.cbor: a CBOR map containing version metadata
and a list of normalized puzzles. Walls are deduplicated as canonical edge
pairs, blocked cells (#) are extracted as a separate list, and waypoint
ordering is verified to be consecutive 1..K.

Run:
    uv run python benchmark/scripts/parse_to_cbor.py
"""

import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cbor2

logger = logging.getLogger("parse_to_cbor")

PUZZLE_FORMAT_VERSION = 1

# Wall bit layout mirrors src/models/cell.py so the on-disk and in-memory
# representations interpret hex characters identically.
WALL_TOP = 0x8
WALL_RIGHT = 0x4
WALL_BOTTOM = 0x2
WALL_LEFT = 0x1

EMPTY_CELL = "."
BLOCKED_CELL = "#"


@dataclass(frozen=True, order=True)
class Coord:
    r: int
    c: int

    def as_tuple(self) -> tuple[int, int]:
        return (self.r, self.c)


@dataclass(frozen=True)
class Edge:
    a: Coord
    b: Coord

    @classmethod
    def canonical(cls, a: Coord, b: Coord) -> "Edge":
        return cls(a, b) if a <= b else cls(b, a)

    def as_pair(self) -> tuple[tuple[int, int], tuple[int, int]]:
        return (self.a.as_tuple(), self.b.as_tuple())


def _parse_cells(
    cells_rows: list[str],
    n: int,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    if len(cells_rows) != n:
        msg = f"cells row count {len(cells_rows)} != expected {n}"
        raise ValueError(msg)

    labelled: dict[int, Coord] = {}
    blocked: list[Coord] = []
    for r, row in enumerate(cells_rows):
        if len(row) != n:
            msg = f"row {r} has length {len(row)} != expected {n}"
            raise ValueError(msg)
        for c, ch in enumerate(row):
            if ch == EMPTY_CELL:
                continue
            if ch == BLOCKED_CELL:
                blocked.append(Coord(r, c))
                continue
            if not ch.isdigit():
                msg = f"unexpected cell char {ch!r} at ({r},{c})"
                raise ValueError(msg)
            label = int(ch)
            if label in labelled:
                msg = f"duplicate waypoint label {label} at ({r},{c})"
                raise ValueError(msg)
            labelled[label] = Coord(r, c)

    if labelled:
        expected_labels = set(range(1, max(labelled) + 1))
        if labelled.keys() != expected_labels:
            msg = f"waypoint labels are not consecutive 1..K: have {sorted(labelled)}"
            raise ValueError(msg)
        waypoints = [labelled[k].as_tuple() for k in sorted(labelled)]
    else:
        waypoints = []

    return waypoints, [b.as_tuple() for b in blocked]


def _parse_walls(walls_rows: list[str], n: int) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    if len(walls_rows) != n:
        msg = f"walls row count {len(walls_rows)} != n {n}"
        raise ValueError(msg)

    edges: set[Edge] = set()
    for r, row in enumerate(walls_rows):
        if len(row) != n:
            msg = f"walls row {r} has length {len(row)} != n {n}"
            raise ValueError(msg)
        for c, ch in enumerate(row):
            try:
                bits = int(ch, 16)
            except ValueError as exc:
                msg = f"non-hex wall char {ch!r} at ({r},{c})"
                raise ValueError(msg) from exc

            here = Coord(r, c)
            if bits & WALL_TOP and r > 0:
                edges.add(Edge.canonical(here, Coord(r - 1, c)))
            if bits & WALL_RIGHT and c < n - 1:
                edges.add(Edge.canonical(here, Coord(r, c + 1)))
            if bits & WALL_BOTTOM and r < n - 1:
                edges.add(Edge.canonical(here, Coord(r + 1, c)))
            if bits & WALL_LEFT and c > 0:
                edges.add(Edge.canonical(here, Coord(r, c - 1)))

    return sorted(e.as_pair() for e in edges)


def _normalize_puzzle(raw: dict[str, Any]) -> dict[str, Any]:
    n = raw["gridWidth"]
    if n != raw["gridHeight"]:
        msg = f"puzzle {raw['id']} is non-square: {n}x{raw['gridHeight']}"
        raise ValueError(msg)

    waypoints, blocked = _parse_cells(raw["cells"], n)
    walls = _parse_walls(raw["walls"], n)

    return {
        "id": raw["id"],
        "name": raw.get("name", ""),
        "difficulty": raw["difficulty"],
        "N": n,
        "K": len(waypoints),
        "waypoints": waypoints,
        "walls": walls,
        "blocked": blocked,
    }


def parse_corpus(raw_path: Path, out_path: Path) -> None:
    logger.info("Reading %s", raw_path)
    with raw_path.open() as f:
        raw_puzzles = json.load(f)

    ordered = sorted(raw_puzzles, key=lambda p: p["sortOrder"])
    normalized = [_normalize_puzzle(p) for p in ordered]
    logger.info("Normalized %d puzzles", len(normalized))

    payload = {
        "version": PUZZLE_FORMAT_VERSION,
        "count": len(normalized),
        "puzzles": normalized,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        cbor2.dump(payload, f)
    logger.info("Wrote %s (%d bytes)", out_path, out_path.stat().st_size)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    repo_root = Path(__file__).resolve().parents[2]
    raw_path = repo_root / "benchmark" / "data" / "raw.json"
    out_path = repo_root / "benchmark" / "data" / "puzzles.cbor"
    parse_corpus(raw_path, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
