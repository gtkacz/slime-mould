"""Deterministic RNG seeding for ZipMould runs.

A Numba-compatible 32-bit kernel seed is derived from a 256-bit blake2b
digest of the run identity tuple. The same identity produces the same
kernel seed and the same `numpy.random.Generator`, byte-for-byte.
"""

from __future__ import annotations

import hashlib

import numpy as np


def _digest(global_seed: int, run_seed: int, puzzle_id: str, config_hash: str) -> bytes:
    h = hashlib.blake2b(digest_size=32)
    h.update(int(global_seed).to_bytes(8, "little", signed=False))
    h.update(int(run_seed).to_bytes(8, "little", signed=False))
    h.update(puzzle_id.encode("utf-8"))
    h.update(bytes.fromhex(config_hash))
    return h.digest()


def derive_kernel_seed(
    global_seed: int, run_seed: int, puzzle_id: str, config_hash: str
) -> int:
    """Return a deterministic 32-bit unsigned integer suitable for `np.random.seed` inside `@njit`."""
    digest = _digest(global_seed, run_seed, puzzle_id, config_hash)
    return int.from_bytes(digest[:4], "little") & 0xFFFFFFFF


def make_rng(
    global_seed: int, run_seed: int, puzzle_id: str, config_hash: str
) -> np.random.Generator:
    """Return a `Generator` for any outer-layer sampling that must share the run identity."""
    digest = _digest(global_seed, run_seed, puzzle_id, config_hash)
    seed_seq = np.random.SeedSequence(int.from_bytes(digest, "little"))
    return np.random.default_rng(seed_seq)
