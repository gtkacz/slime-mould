"""HTTP route handlers for the viz API."""

from __future__ import annotations

import tomllib
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _get_version
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from zipmould.io.puzzles import load_corpus
from zipmould.viz.schemas import ALLOWED_VARIANTS, PuzzleSummary, VariantSummary

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CONFIG_DIR = _REPO_ROOT / "configs" / "ablations"
_BASE_CONFIG = _REPO_ROOT / "configs" / "default.toml"
_CORPUS_PATH = _REPO_ROOT / "benchmark" / "data" / "puzzles.cbor"


def _resolve_zipmould_version() -> str:
    try:
        return _get_version("zipmould")
    except PackageNotFoundError:
        return "unknown"


ZIPMOULD_VERSION: str = _resolve_zipmould_version()

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe; returns the installed package version."""
    return {"status": "ok", "version": ZIPMOULD_VERSION}


@router.get("/puzzles", response_model=list[PuzzleSummary])
def list_puzzles() -> list[PuzzleSummary]:
    corpus = load_corpus(_CORPUS_PATH)
    return [
        PuzzleSummary(id=pz.id, name=pz.name, difficulty=str(pz.difficulty), N=pz.N, K=pz.K)
        for pz in corpus.values()
    ]


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        data = tomllib.load(f)
    return data.get("solver", data)


@router.get("/variants", response_model=list[VariantSummary])
def list_variants() -> list[VariantSummary]:
    base = _load_toml(_BASE_CONFIG)
    out: list[VariantSummary] = []
    for name in ALLOWED_VARIANTS:
        path = _CONFIG_DIR / f"{name}.toml"
        merged = dict(base)
        merged.update(_load_toml(path))
        out.append(VariantSummary(name=name, config_path=str(path), defaults=merged))
    return out
