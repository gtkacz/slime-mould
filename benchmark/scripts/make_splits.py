"""Generate train/dev/test splits over the puzzle corpus.

Reads benchmark/data/puzzles.cbor and emits benchmark/data/splits.json with
stratified random sampling keyed on (size_bucket, difficulty). The split
seed is fixed at SPLIT_SEED = 20260424 per docs/design.md sec 6.2.

Re-running with the same input is bit-identical idempotent.

Run:
    uv run python benchmark/scripts/make_splits.py
"""

import json
import logging
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import cbor2

logger = logging.getLogger("make_splits")

# Frozen per docs/design.md sec 6.2 — the test set is sealed once this
# split is produced. Changing the seed invalidates the test set.
SPLIT_SEED = 20260424
SPLITS_FORMAT_VERSION = 1

TRAIN_FRAC = 0.70
DEV_FRAC = 0.15
TEST_FRAC = 0.15

SIZE_BUCKETS: dict[str, list[int]] = {
    "small": [3, 4, 5],
    "medium": [6, 7],
    "large": [8, 9, 10],
}


def _size_bucket(n: int) -> str:
    for name, sizes in SIZE_BUCKETS.items():
        if n in sizes:
            return name
    msg = f"grid size {n} not in any bucket"
    raise ValueError(msg)


def _stratify(puzzles: list[dict[str, Any]]) -> dict[tuple[str, str], list[str]]:
    strata: dict[tuple[str, str], list[str]] = defaultdict(list)
    for p in puzzles:
        key = (_size_bucket(p["N"]), p["difficulty"])
        strata[key].append(p["id"])
    return strata


def _split_stratum(
    ids: list[str],
    rng: random.Random,
) -> tuple[list[str], list[str], list[str]]:
    # Sort first so the shuffle order depends only on rng state, not input order.
    shuffled = sorted(ids)
    rng.shuffle(shuffled)

    size = len(shuffled)
    n_test = round(size * TEST_FRAC)
    n_dev = round(size * DEV_FRAC)
    n_train = size - n_test - n_dev

    train = shuffled[:n_train]
    dev = shuffled[n_train : n_train + n_dev]
    test = shuffled[n_train + n_dev :]
    return train, dev, test


def make_splits(puzzles_path: Path, out_path: Path) -> None:
    with puzzles_path.open("rb") as f:
        payload = cbor2.load(f)
    puzzles: list[dict[str, Any]] = payload["puzzles"]
    logger.info("Loaded %d puzzles from %s", len(puzzles), puzzles_path)

    strata = _stratify(puzzles)
    rng = random.Random(SPLIT_SEED)

    train: list[str] = []
    dev: list[str] = []
    test: list[str] = []
    stratum_summary: list[dict[str, Any]] = []

    for key in sorted(strata):
        ids = strata[key]
        s_train, s_dev, s_test = _split_stratum(ids, rng)
        train.extend(s_train)
        dev.extend(s_dev)
        test.extend(s_test)
        stratum_summary.append(
            {
                "size_bucket": key[0],
                "difficulty": key[1],
                "total": len(ids),
                "train": len(s_train),
                "dev": len(s_dev),
                "test": len(s_test),
            }
        )
        logger.info(
            "stratum %s/%s: total=%d train=%d dev=%d test=%d",
            key[0],
            key[1],
            len(ids),
            len(s_train),
            len(s_dev),
            len(s_test),
        )

    splits = {
        "version": SPLITS_FORMAT_VERSION,
        "split_seed": SPLIT_SEED,
        "stratification_key": ["size_bucket", "difficulty"],
        "size_buckets": SIZE_BUCKETS,
        "fractions": {"train": TRAIN_FRAC, "dev": DEV_FRAC, "test": TEST_FRAC},
        "totals": {"train": len(train), "dev": len(dev), "test": len(test)},
        "strata": stratum_summary,
        "train": sorted(train),
        "dev": sorted(dev),
        "test": sorted(test),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        json.dump(splits, f, indent=2)
        f.write("\n")
    logger.info(
        "Wrote %s (train=%d dev=%d test=%d)",
        out_path,
        len(train),
        len(dev),
        len(test),
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    repo_root = Path(__file__).resolve().parents[2]
    puzzles_path = repo_root / "benchmark" / "data" / "puzzles.cbor"
    out_path = repo_root / "benchmark" / "data" / "splits.json"
    make_splits(puzzles_path, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
