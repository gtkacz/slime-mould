"""Builders for tiny synthetic traces used in viz tests."""

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
from zipmould.viz.trace_codec import write_cbor_bytes


def tiny_cbor() -> bytes:
    """Two-frame trace small enough to embed in tests."""
    header = TraceHeader(
        N=3,
        K=2,
        L=9,
        waypoints=((0, 0), (2, 2)),
        walls=(),
        blocked=(),
    )
    walker = WalkerSnapshot(id=0, cell=(0, 0), segment=0, status="alive", fitness=0.0)
    frames = (
        Frame(
            t=0,
            v_b=0.0,
            v_c=0.0,
            tau_delta=TauDelta(mode="unified", edges=()),
            best=BestPath(path=((0, 0),), fitness=0.0),
            walkers=(walker,),
        ),
        Frame(
            t=5,
            v_b=0.1,
            v_c=0.2,
            tau_delta=TauDelta(mode="unified", edges=((0, -1, 0.5),)),
            best=BestPath(path=((0, 0), (0, 1)), fitness=0.5),
            walkers=(walker,),
        ),
    )
    footer = TraceFooter(
        solved=False,
        infeasible=False,
        solution=None,
        iterations_used=10,
        wall_clock_s=0.001,
        best_fitness=0.5,
    )
    trace = Trace(
        version=1,
        puzzle_id="fixture",
        config={"alpha": 1.0, "tau_max": 10.0, "tau_signed": True},
        seed=0,
        header=header,
        frames=frames,
        footer=footer,
    )
    return write_cbor_bytes(trace)
