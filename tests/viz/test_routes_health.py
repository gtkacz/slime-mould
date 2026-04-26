"""Liveness check for the viz FastAPI app."""

from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

from zipmould.viz.server import create_app


def test_health_returns_ok() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == HTTPStatus.OK
    body = resp.json()
    assert body["status"] == "ok"
    assert isinstance(body["version"], str) and body["version"]
