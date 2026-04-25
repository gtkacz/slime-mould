"""Puzzle and split loaders.

The CBOR puzzle corpus is produced by ``benchmark/scripts/parse_to_cbor.py``
and the splits manifest by ``benchmark/scripts/make_splits.py``.  This
module exposes minimal readers that materialise frozen ``Puzzle``
dataclasses for the solver.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from zipmould.puzzle import Puzzle, load_puzzles_cbor

DEFAULT_CORPUS_PATH: Final[Path] = Path("benchmark/data/puzzles.cbor")
DEFAULT_SPLITS_PATH: Final[Path] = Path("benchmark/data/splits.json")

_VALID_SPLITS: Final[frozenset[str]] = frozenset({"train", "dev", "test"})


def load_corpus(path: Path | str = DEFAULT_CORPUS_PATH) -> dict[str, Puzzle]:
    """Load the canonical puzzle corpus keyed by puzzle id."""
    return load_puzzles_cbor(Path(path))


def load_split(name: str, path: Path | str = DEFAULT_SPLITS_PATH) -> list[str]:
    """Load the list of puzzle ids belonging to a named split (train/dev/test)."""
    if name not in _VALID_SPLITS:
        msg = f"unknown split {name!r}; expected train|dev|test"
        raise ValueError(msg)
    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    ids = manifest.get(name)
    if not isinstance(ids, list):
        msg = f"splits manifest at {p} missing list for {name!r}"
        raise ValueError(msg)
    return [str(x) for x in ids]  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
