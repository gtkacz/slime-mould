"""LRU trace cache."""

from __future__ import annotations

import pytest

from zipmould.viz.cache import TraceCache


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
