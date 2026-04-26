"""GET /api/variants."""

from __future__ import annotations

from http import HTTPStatus

from fastapi.testclient import TestClient

from zipmould.viz.server import create_app


def test_variants_list_contains_four_zipmould_kinds() -> None:
    app = create_app()
    client = TestClient(app)
    resp = client.get("/api/variants")
    assert resp.status_code == HTTPStatus.OK
    items = resp.json()
    names = {item["name"] for item in items}
    assert names == {
        "zipmould-uni-signed",
        "zipmould-uni-positive",
        "zipmould-strat-signed",
        "zipmould-strat-positive",
    }
    for item in items:
        assert "config_path" in item
        assert isinstance(item["defaults"], dict)
