"""ZipMould — Li-inspired Slime Mould Algorithm for Zip puzzles."""

from zipmould.config import ConfigError, ExperimentManifest, SolverConfig
from zipmould.feasibility import FeasibilityReport, precheck
from zipmould.io.trace import (
    BestPath,
    Frame,
    TauDelta,
    Trace,
    TraceFooter,
    TraceHeader,
    WalkerSnapshot,
)
from zipmould.puzzle import Coord, Edge, Puzzle, load_puzzles_cbor
from zipmould.rng import derive_kernel_seed, make_rng
from zipmould.solver.api import DeterminismError, KernelError, RunResult, solve

__version__ = "0.1.0"

__all__ = [
    "BestPath",
    "ConfigError",
    "Coord",
    "DeterminismError",
    "Edge",
    "ExperimentManifest",
    "FeasibilityReport",
    "Frame",
    "KernelError",
    "Puzzle",
    "RunResult",
    "SolverConfig",
    "TauDelta",
    "Trace",
    "TraceFooter",
    "TraceHeader",
    "WalkerSnapshot",
    "__version__",
    "derive_kernel_seed",
    "load_puzzles_cbor",
    "make_rng",
    "precheck",
    "solve",
]
