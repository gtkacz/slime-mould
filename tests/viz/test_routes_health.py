"""Liveness check for the viz FastAPI app."""

from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from zipmould.viz.server import create_app


def test_health_returns_ok() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == HTTPStatus.OK
    body = resp.json()
    assert body["status"] == "ok"
    assert isinstance(body["version"], str) and body["version"]


def test_cors_allows_configured_origin(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ZIPMOULD_ALLOWED_ORIGINS", "https://app.example.com")
    app = create_app()
    client = TestClient(app)
    resp = client.options(
        "/api/runs",
        headers={
            "Origin": "https://app.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == HTTPStatus.OK
    assert resp.headers["access-control-allow-origin"] == "https://app.example.com"


def test_cors_rejects_unconfigured_origin(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ZIPMOULD_ALLOWED_ORIGINS", "https://app.example.com")
    app = create_app()
    client = TestClient(app)
    resp = client.options(
        "/api/runs",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == HTTPStatus.BAD_REQUEST
