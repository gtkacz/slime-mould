"""Standardised error envelope."""

from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

from zipmould.viz.server import create_app


def test_404_uses_envelope() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/traces/no-such.cbor")
    assert resp.status_code == HTTPStatus.NOT_FOUND
    body = resp.json()
    assert body == {"kind": "trace_not_found", "detail": "no-such"}


def test_422_validation_uses_envelope() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.post("/api/runs", json={"puzzle_id": "", "variant": "x", "seed": -1})
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    body = resp.json()
    assert body["kind"] == "validation_error"
    assert isinstance(body["detail"], str) and body["detail"]
