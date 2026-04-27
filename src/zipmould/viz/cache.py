"""Caches used by the viz backend."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections import OrderedDict
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, cast

import cbor2


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


_RUN_CACHE_FORMAT_VERSION = 1


@dataclass(frozen=True)
class CachedRun:
    """A cached solver run loaded from disk."""

    trace: dict[str, Any]
    cbor_bytes: bytes


class RunDiskCache:
    """Deploy-scoped disk cache for default solver runs.

    The key is intentionally limited to `(puzzle_id, seed, variant)`. Requests
    with config overrides bypass this cache at the route layer.
    """

    def __init__(self, root: Path, deploy_id: str) -> None:
        safe_deploy_id = _safe_path_part(deploy_id)
        self._parent = root
        self._root = root / safe_deploy_id
        self._root.mkdir(parents=True, exist_ok=True)
        self._prune_other_deployments()

    def get(self, puzzle_id: str, variant: str, seed: int) -> CachedRun | None:
        path = self._path_for(puzzle_id, variant, seed)
        try:
            with path.open("rb") as f:
                payload = cast("dict[str, Any]", cbor2.load(f))
            if int(payload.get("format_version", -1)) != _RUN_CACHE_FORMAT_VERSION:
                return None
            trace = cast("dict[str, Any]", payload["trace"])
            cbor_bytes = bytes(cast("bytes", payload["cbor_bytes"]))
        except (cbor2.CBORDecodeError, KeyError, OSError, TypeError, ValueError):
            self._discard(path)
            return None
        return CachedRun(trace=trace, cbor_bytes=cbor_bytes)

    def put(self, puzzle_id: str, variant: str, seed: int, trace: dict[str, Any], cbor_bytes: bytes) -> None:
        path = self._path_for(puzzle_id, variant, seed)
        payload = {
            "format_version": _RUN_CACHE_FORMAT_VERSION,
            "trace": trace,
            "cbor_bytes": cbor_bytes,
        }
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=self._root, prefix=".run-", suffix=".cbor", delete=False) as f:
                tmp_path = Path(f.name)
                cbor2.dump(payload, f)
            os.replace(tmp_path, path)
        except OSError:
            if tmp_path is not None:
                self._discard(tmp_path)

    def _path_for(self, puzzle_id: str, variant: str, seed: int) -> Path:
        key = f"{puzzle_id}\0{seed}\0{variant}".encode()
        digest = hashlib.sha256(key).hexdigest()
        return self._root / f"{digest}.cbor"

    def _prune_other_deployments(self) -> None:
        try:
            children = list(self._parent.iterdir())
        except OSError:
            return
        for child in children:
            if child == self._root or child.is_symlink() or not child.is_dir():
                continue
            _remove_tree(child)

    @staticmethod
    def _discard(path: Path) -> None:
        try:
            path.unlink()
        except FileNotFoundError:
            return
        except OSError:
            return


def _safe_path_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in value) or "unknown"


def _remove_tree(root: Path) -> None:
    try:
        children = list(root.iterdir())
    except OSError:
        return
    for child in children:
        if child.is_dir() and not child.is_symlink():
            _remove_tree(child)
        else:
            try:
                child.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass
    with suppress(OSError):
        root.rmdir()
