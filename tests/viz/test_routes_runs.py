"""POST /api/runs."""

from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

from zipmould.viz.server import create_app


def test_runs_returns_trace_and_id() -> None:
    app = create_app()
    client = TestClient(app)
    body = {
        "puzzle_id": "level_001",
        "variant": "zipmould-uni-positive",
        "seed": 0,
        "config_overrides": {"iter_cap": 200, "population": 8},
    }
    resp = client.post("/api/runs", json=body)
    assert resp.status_code == HTTPStatus.OK, resp.text
    payload = resp.json()
    assert isinstance(payload["trace_id"], str) and payload["trace_id"]
    trace = payload["trace"]
    assert trace["puzzle_id"] == "level_001"
    assert isinstance(trace["frames"], list)


def test_runs_unknown_puzzle_returns_404() -> None:
    app = create_app()
    client = TestClient(app)
    body = {"puzzle_id": "no-such", "variant": "zipmould-uni-positive", "seed": 0}
    resp = client.post("/api/runs", json=body)
    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert resp.json()["detail"]["kind"] == "puzzle_not_found"


def test_runs_unknown_variant_returns_422() -> None:
    app = create_app()
    client = TestClient(app)
    body = {"puzzle_id": "level_001", "variant": "frobnicate", "seed": 0}
    resp = client.post("/api/runs", json=body)
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
