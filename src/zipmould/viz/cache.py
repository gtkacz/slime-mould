"""Bounded in-memory cache of Trace CBOR payloads, keyed by trace id."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock


class TraceCache:
    """A small thread-safe LRU keyed cache for byte payloads."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            msg = f"capacity must be positive, got {capacity}"
            raise ValueError(msg)
        self._capacity = capacity
        self._items: OrderedDict[str, bytes] = OrderedDict()
        self._lock = Lock()

    def put(self, key: str, value: bytes) -> None:
        with self._lock:
            if key in self._items:
                self._items.move_to_end(key)
            self._items[key] = value
            while len(self._items) > self._capacity:
                self._items.popitem(last=False)

    def get(self, key: str) -> bytes | None:
        with self._lock:
            value = self._items.get(key)
            if value is not None:
                self._items.move_to_end(key)
            return value
