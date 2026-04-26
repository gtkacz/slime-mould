"""Round-trip a fixture Trace through the public JSON helpers."""

from __future__ import annotations

from zipmould.io.trace import (
    BestPath,
    Frame,
    TauDelta,
    Trace,
    TraceFooter,
    TraceHeader,
    WalkerSnapshot,
)
from zipmould.viz.trace_codec import jsonable_to_trace, trace_to_jsonable


def _fixture_trace() -> Trace:
    header = TraceHeader(N=3, K=2, L=9, waypoints=((0, 0), (2, 2)), walls=(), blocked=())
    walker = WalkerSnapshot(id=0, cell=(1, 1), segment=0, status="alive", fitness=0.5)
    frame = Frame(
        t=0,
        v_b=0.1,
        v_c=0.2,
        tau_delta=TauDelta(mode="unified", edges=((0, -1, 0.5),)),
        best=BestPath(path=((0, 0),), fitness=0.0),
        walkers=(walker,),
    )
    footer = TraceFooter(
        solved=False,
        infeasible=False,
        solution=None,
        iterations_used=1,
        wall_clock_s=0.01,
        best_fitness=0.5,
    )
    return Trace(
        version=1,
        puzzle_id="fixture",
        config={"alpha": 1.0},
        seed=7,
        header=header,
        frames=(frame,),
        footer=footer,
    )


def test_round_trip_preserves_all_fields() -> None:
    original = _fixture_trace()
    payload = trace_to_jsonable(original)
    restored = jsonable_to_trace(payload)
    assert restored == original


def test_jsonable_uses_pure_python_types() -> None:
    payload = trace_to_jsonable(_fixture_trace())
    assert payload["puzzle_id"] == "fixture"
    assert payload["frames"][0]["walkers"][0]["status"] == "alive"
    assert payload["header"]["waypoints"] == [[0, 0], [2, 2]]
