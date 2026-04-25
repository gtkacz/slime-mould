"""CBOR trace schema and codec.

The on-disk shape mirrors `docs/design.md` §8. `Trace` and its
subordinate dataclasses are immutable; they are built once from the
kernel's array buffers and serialised via `cbor2`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cbor2

from zipmould.puzzle import Coord, Edge

TRACE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class WalkerSnapshot:
    id: int
    cell: Coord
    segment: int
    status: Literal["alive", "dead-end", "complete"]
    fitness: float


@dataclass(frozen=True, slots=True)
class BestPath:
    path: tuple[Coord, ...]
    fitness: float


@dataclass(frozen=True, slots=True)
class TauDelta:
    mode: Literal["unified", "stratified"]
    edges: tuple[tuple[int, int, float], ...]


@dataclass(frozen=True, slots=True)
class Frame:
    t: int
    v_b: float
    v_c: float
    tau_delta: TauDelta
    best: BestPath
    walkers: tuple[WalkerSnapshot, ...]


@dataclass(frozen=True, slots=True)
class TraceHeader:
    N: int
    K: int
    L: int
    waypoints: tuple[Coord, ...]
    walls: tuple[Edge, ...]
    blocked: tuple[Coord, ...]


@dataclass(frozen=True, slots=True)
class TraceFooter:
    solved: bool
    infeasible: bool
    solution: tuple[Coord, ...] | None
    iterations_used: int
    wall_clock_s: float
    best_fitness: float


@dataclass(frozen=True, slots=True)
class Trace:
    version: int
    puzzle_id: str
    config: Mapping[str, object]
    seed: int
    header: TraceHeader
    frames: tuple[Frame, ...]
    footer: TraceFooter


_STATUS_NAMES = ("alive", "dead-end", "complete", "error")


def _status_name(code: int) -> Literal["alive", "dead-end", "complete"]:  # pyright: ignore[reportUnusedFunction]
    if code == 0:
        return "alive"
    if code == 1:
        return "dead-end"
    if code == 2:  # noqa: PLR2004
        return "complete"
    msg = f"invalid kernel status code {code}"
    raise ValueError(msg)


def _walker_to_dict(w: WalkerSnapshot) -> dict[str, object]:
    return {
        "id": w.id,
        "cell": [w.cell[0], w.cell[1]],
        "segment": w.segment,
        "status": w.status,
        "fitness": w.fitness,
    }


def _frame_to_dict(f: Frame) -> dict[str, object]:
    return {
        "t": f.t,
        "v_b": f.v_b,
        "v_c": f.v_c,
        "tau_delta": {
            "mode": f.tau_delta.mode,
            "edges": [list(e) for e in f.tau_delta.edges],
        },
        "best": {
            "path": [[r, c] for (r, c) in f.best.path],
            "fitness": f.best.fitness,
        },
        "walkers": [_walker_to_dict(w) for w in f.walkers],
    }


def _trace_to_dict(trace: Trace) -> dict[str, object]:
    return {
        "version": trace.version,
        "puzzle_id": trace.puzzle_id,
        "config": dict(trace.config),
        "seed": trace.seed,
        "header": {
            "N": trace.header.N,
            "K": trace.header.K,
            "L": trace.header.L,
            "waypoints": [[r, c] for (r, c) in trace.header.waypoints],
            "walls": [
                [[a[0], a[1]], [b[0], b[1]]] for (a, b) in trace.header.walls
            ],
            "blocked": [[r, c] for (r, c) in trace.header.blocked],
        },
        "frames": [_frame_to_dict(f) for f in trace.frames],
        "footer": {
            "solved": trace.footer.solved,
            "infeasible": trace.footer.infeasible,
            "solution": (
                [[r, c] for (r, c) in trace.footer.solution]
                if trace.footer.solution is not None
                else None
            ),
            "iterations_used": trace.footer.iterations_used,
            "wall_clock_s": trace.footer.wall_clock_s,
            "best_fitness": trace.footer.best_fitness,
        },
    }


def _walker_from_dict(d: dict[str, object]) -> WalkerSnapshot:
    cell = d["cell"]
    return WalkerSnapshot(
        id=int(d["id"]),  # type: ignore[arg-type]
        cell=(int(cell[0]), int(cell[1])),  # type: ignore[index]
        segment=int(d["segment"]),  # type: ignore[arg-type]
        status=d["status"],  # type: ignore[assignment]
        fitness=float(d["fitness"]),  # type: ignore[arg-type]
    )


def _frame_from_dict(d: dict[str, object]) -> Frame:
    td = d["tau_delta"]
    best = d["best"]
    return Frame(
        t=int(d["t"]),  # type: ignore[arg-type]
        v_b=float(d["v_b"]),  # type: ignore[arg-type]
        v_c=float(d["v_c"]),  # type: ignore[arg-type]
        tau_delta=TauDelta(
            mode=td["mode"],  # type: ignore[index, assignment]
            edges=tuple(
                (int(e[0]), int(e[1]), float(e[2]))  # pyright: ignore[reportUnknownArgumentType]
                for e in td["edges"]  # type: ignore[index, union-attr]
            ),
        ),
        best=BestPath(
            path=tuple((int(r), int(c)) for (r, c) in best["path"]),  # type: ignore[index, union-attr]
            fitness=float(best["fitness"]),  # type: ignore[index, arg-type]
        ),
        walkers=tuple(_walker_from_dict(w) for w in d["walkers"]),  # type: ignore[arg-type]
    )


def write_cbor(trace: Trace, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        cbor2.dump(_trace_to_dict(trace), f)


def read_cbor(path: Path) -> Trace:
    with path.open("rb") as f:
        raw = cbor2.load(f)
    h = raw["header"]
    ft = raw["footer"]
    return Trace(
        version=int(raw["version"]),
        puzzle_id=str(raw["puzzle_id"]),
        config=dict(raw["config"]),
        seed=int(raw["seed"]),
        header=TraceHeader(
            N=int(h["N"]),
            K=int(h["K"]),
            L=int(h["L"]),
            waypoints=tuple((int(r), int(c)) for (r, c) in h["waypoints"]),
            walls=tuple(
                ((int(a[0]), int(a[1])), (int(b[0]), int(b[1])))
                for (a, b) in h["walls"]
            ),
            blocked=tuple((int(r), int(c)) for (r, c) in h["blocked"]),
        ),
        frames=tuple(_frame_from_dict(f) for f in raw["frames"]),
        footer=TraceFooter(
            solved=bool(ft["solved"]),
            infeasible=bool(ft["infeasible"]),
            solution=(
                tuple((int(r), int(c)) for (r, c) in ft["solution"])
                if ft["solution"] is not None
                else None
            ),
            iterations_used=int(ft["iterations_used"]),
            wall_clock_s=float(ft["wall_clock_s"]),
            best_fitness=float(ft["best_fitness"]),
        ),
    )
