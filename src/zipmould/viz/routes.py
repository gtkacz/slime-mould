"""HTTP route handlers for the viz API."""

from __future__ import annotations

import tomllib
import uuid
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _get_version
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from zipmould.io.puzzles import load_corpus
from zipmould.viz.runner import RunnerError, run_solve
from zipmould.viz.schemas import ALLOWED_VARIANTS, PuzzleSummary, RunRequest, RunResponse, VariantSummary

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


@router.post("/runs", response_model=RunResponse)
def post_run(req: RunRequest, request: Request) -> RunResponse:
    corpus = load_corpus(_CORPUS_PATH)
    if req.puzzle_id not in corpus:
        raise HTTPException(
            status_code=404,
            detail={"kind": "puzzle_not_found", "detail": f"unknown puzzle {req.puzzle_id!r}"},
        )
    puzzle = corpus[req.puzzle_id]
    try:
        trace_dict, cbor_bytes = run_solve(
            puzzle=puzzle,
            variant=req.variant,
            seed=req.seed,
            config_overrides=req.config_overrides,
        )
    except RunnerError as exc:
        raise HTTPException(
            status_code=422,
            detail={"kind": "infeasible", "detail": str(exc)},
        ) from exc
    trace_id = uuid.uuid4().hex
    request.app.state.trace_cache.put(trace_id, cbor_bytes)
    return RunResponse(trace_id=trace_id, trace=trace_dict)
