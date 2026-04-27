"""POST /api/runs."""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from tests.viz.fixtures.builder import tiny_cbor
from zipmould.viz.server import create_app
from zipmould.viz.trace_codec import read_cbor_bytes, trace_to_jsonable


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
    assert resp.json()["kind"] == "puzzle_not_found"


def test_runs_unknown_variant_returns_422() -> None:
    app = create_app()
    client = TestClient(app)
    body = {"puzzle_id": "level_001", "variant": "frobnicate", "seed": 0}
    resp = client.post("/api/runs", json=body)
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_runs_uses_prod_disk_cache_for_default_requests(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ZIPMOULD_ENV", "production")
    monkeypatch.setenv("ZIPMOULD_RUN_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ZIPMOULD_DEPLOY_ID", "test-deploy")
    raw = tiny_cbor()
    trace = trace_to_jsonable(read_cbor_bytes(raw))
    calls = 0

    def fake_run_solve(
        puzzle: Any,
        variant: str,
        seed: int,
        config_overrides: dict[str, Any],
    ) -> tuple[dict[str, Any], bytes]:
        nonlocal calls
        assert puzzle.id == "level_001"
        assert variant == "zipmould-uni-positive"
        assert seed == 0
        assert config_overrides == {}
        calls += 1
        return trace, raw

    monkeypatch.setattr("zipmould.viz.routes.run_solve", fake_run_solve)
    app = create_app()
    client = TestClient(app)
    body = {"puzzle_id": "level_001", "variant": "zipmould-uni-positive", "seed": 0}

    first = client.post("/api/runs", json=body)
    second = client.post("/api/runs", json=body)

    assert first.status_code == HTTPStatus.OK, first.text
    assert second.status_code == HTTPStatus.OK, second.text
    assert calls == 1
    first_trace_id = first.json()["trace_id"]
    second_trace_id = second.json()["trace_id"]
    assert first_trace_id != second_trace_id
    assert client.get(f"/api/traces/{second_trace_id}.cbor").content == raw


def test_runs_bypass_disk_cache_outside_prod(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ZIPMOULD_ENV", raising=False)
    monkeypatch.setenv("ZIPMOULD_RUN_CACHE_DIR", str(tmp_path))
    raw = tiny_cbor()
    trace = trace_to_jsonable(read_cbor_bytes(raw))
    calls = 0

    def fake_run_solve(
        puzzle: Any,
        variant: str,
        seed: int,
        config_overrides: dict[str, Any],
    ) -> tuple[dict[str, Any], bytes]:
        nonlocal calls
        assert puzzle.id == "level_001"
        assert variant == "zipmould-uni-positive"
        assert seed == 0
        assert config_overrides == {}
        calls += 1
        return trace, raw

    monkeypatch.setattr("zipmould.viz.routes.run_solve", fake_run_solve)
    app = create_app()
    client = TestClient(app)
    body = {"puzzle_id": "level_001", "variant": "zipmould-uni-positive", "seed": 0}

    assert client.post("/api/runs", json=body).status_code == HTTPStatus.OK
    assert client.post("/api/runs", json=body).status_code == HTTPStatus.OK
    expected_calls = 2
    assert calls == expected_calls
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []


def test_runs_with_config_overrides_bypass_prod_disk_cache(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ZIPMOULD_ENV", "production")
    monkeypatch.setenv("ZIPMOULD_RUN_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("ZIPMOULD_DEPLOY_ID", "test-deploy")
    raw = tiny_cbor()
    trace = trace_to_jsonable(read_cbor_bytes(raw))
    calls = 0

    def fake_run_solve(
        puzzle: Any,
        variant: str,
        seed: int,
        config_overrides: dict[str, Any],
    ) -> tuple[dict[str, Any], bytes]:
        nonlocal calls
        assert puzzle.id == "level_001"
        assert variant == "zipmould-uni-positive"
        assert seed == 0
        assert config_overrides == {"iter_cap": 20}
        calls += 1
        return trace, raw

    monkeypatch.setattr("zipmould.viz.routes.run_solve", fake_run_solve)
    app = create_app()
    client = TestClient(app)
    body = {
        "puzzle_id": "level_001",
        "variant": "zipmould-uni-positive",
        "seed": 0,
        "config_overrides": {"iter_cap": 20},
    }

    assert client.post("/api/runs", json=body).status_code == HTTPStatus.OK
    assert client.post("/api/runs", json=body).status_code == HTTPStatus.OK
    expected_calls = 2
    assert calls == expected_calls
