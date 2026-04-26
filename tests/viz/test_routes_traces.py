"""POST /api/traces/upload and GET /api/traces/{id}.cbor."""

from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

from tests.viz.fixtures.builder import tiny_cbor
from zipmould.viz.server import create_app


def test_upload_returns_jsonable_trace_and_id() -> None:
    app = create_app()
    client = TestClient(app)
    payload = tiny_cbor()
    resp = client.post(
        "/api/traces/upload",
        files={"file": ("tiny.cbor", payload, "application/cbor")},
    )
    assert resp.status_code == HTTPStatus.OK, resp.text
    body = resp.json()
    assert body["trace"]["puzzle_id"] == "fixture"
    assert isinstance(body["trace_id"], str) and body["trace_id"]


def test_upload_then_download_round_trips_bytes() -> None:
    app = create_app()
    client = TestClient(app)
    payload = tiny_cbor()
    upload = client.post(
        "/api/traces/upload",
        files={"file": ("tiny.cbor", payload, "application/cbor")},
    )
    trace_id = upload.json()["trace_id"]
    download = client.get(f"/api/traces/{trace_id}.cbor")
    assert download.status_code == HTTPStatus.OK
    assert download.content == payload
    assert download.headers["content-type"].startswith("application/cbor")


def test_download_unknown_id_returns_404() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/traces/deadbeef.cbor")
    assert resp.status_code == HTTPStatus.NOT_FOUND
