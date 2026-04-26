"""GET /api/puzzles."""

from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

from zipmould.viz.server import create_app


def test_puzzles_list_has_expected_fields() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/puzzles")
    assert resp.status_code == HTTPStatus.OK
    items = resp.json()
    assert isinstance(items, list) and items
    sample = items[0]
    assert {"id", "name", "difficulty", "N", "K"} <= sample.keys()
