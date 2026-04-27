"""Liveness check for the viz FastAPI app."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from zipmould.viz import server


def test_health_returns_ok() -> None:
    app = server.create_app()
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == HTTPStatus.OK
    body = resp.json()
    assert body["status"] == "ok"
    assert isinstance(body["version"], str) and body["version"]


def test_cors_allows_configured_origin(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("ZIPMOULD_ALLOWED_ORIGINS", "https://app.example.com")
    app = server.create_app()
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
    app = server.create_app()
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


def test_static_index_revalidates_for_fresh_app_shell(
    tmp_path: Path,
) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    index = static_dir / "index.html"
    index.write_text("<div id='app'></div>", encoding="utf-8")

    static_files = server.CacheBustingStaticFiles(directory=static_dir, html=True)
    resp = static_files.file_response(
        index,
        index.stat(),
        {"type": "http", "method": "GET", "path": "/index.html", "headers": []},
    )

    assert resp.headers["cache-control"] == "no-cache, max-age=0, must-revalidate"
    assert resp.headers["pragma"] == "no-cache"
    assert resp.headers["expires"] == "0"


def test_static_hashed_assets_are_immutable(
    tmp_path: Path,
) -> None:
    assets_dir = tmp_path / "static" / "assets"
    assets_dir.mkdir(parents=True)
    asset = assets_dir / "index-abc123.js"
    asset.write_text("console.log('ok')", encoding="utf-8")

    static_files = server.CacheBustingStaticFiles(directory=tmp_path / "static", html=True)
    resp = static_files.file_response(
        asset,
        asset.stat(),
        {"type": "http", "method": "GET", "path": "/assets/index-abc123.js", "headers": []},
    )

    assert resp.headers["cache-control"] == "public, max-age=31536000, immutable"
