"""LRU trace cache."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from zipmould.viz.cache import RunDiskCache, TraceCache


def test_put_and_get_returns_same_bytes() -> None:
    cache = TraceCache(capacity=2)
    cache.put("a", b"\x01\x02")
    assert cache.get("a") == b"\x01\x02"


def test_eviction_drops_least_recently_used() -> None:
    cache = TraceCache(capacity=2)
    cache.put("a", b"a")
    cache.put("b", b"b")
    cache.get("a")  # touch a so b becomes LRU
    cache.put("c", b"c")
    assert cache.get("b") is None
    assert cache.get("a") == b"a"
    assert cache.get("c") == b"c"


def test_get_missing_returns_none() -> None:
    cache = TraceCache(capacity=1)
    assert cache.get("nope") is None


def test_capacity_must_be_positive() -> None:
    with pytest.raises(ValueError, match="capacity"):
        TraceCache(capacity=0)


def test_run_disk_cache_round_trips_payload(tmp_path: Path) -> None:
    cache = RunDiskCache(root=tmp_path, deploy_id="deploy-a")
    trace: dict[str, Any] = {"puzzle_id": "level_001", "seed": 7, "frames": []}

    cache.put("level_001", "zipmould-uni-positive", 7, trace, b"trace-cbor")

    cached = cache.get("level_001", "zipmould-uni-positive", 7)
    assert cached is not None
    assert cached.trace == trace
    assert cached.cbor_bytes == b"trace-cbor"


def test_run_disk_cache_keys_include_seed_and_variant(tmp_path: Path) -> None:
    cache = RunDiskCache(root=tmp_path, deploy_id="deploy-a")
    trace: dict[str, Any] = {"puzzle_id": "level_001", "seed": 7, "frames": []}

    cache.put("level_001", "zipmould-uni-positive", 7, trace, b"a")

    assert cache.get("level_001", "zipmould-uni-positive", 8) is None
    assert cache.get("level_001", "zipmould-strat-positive", 7) is None


def test_run_disk_cache_prunes_other_deployments(tmp_path: Path) -> None:
    old_dir = tmp_path / "old-deploy"
    old_dir.mkdir()
    (old_dir / "stale.cbor").write_bytes(b"stale")

    RunDiskCache(root=tmp_path, deploy_id="new-deploy")

    assert not old_dir.exists()
    assert (tmp_path / "new-deploy").is_dir()
