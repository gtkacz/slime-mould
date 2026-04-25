# Stage 4 Extended Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strengthen the Stage-4 evaluation evidence beyond the single pre-registered McNemar test by adding complementary descriptive analyses, without re-running any models or touching the held-out split.

**Architecture:** A new analysis module `experiments/stage4/analyze_extended.py` reads the existing `experiments/stage4/out/results.parquet` and emits `extended_report.json` containing: a paired bootstrap CI on the per-puzzle solve-count difference (vs the strongest baseline), seed-level reliability per condition, asymmetric-puzzle tables (which puzzles each side uniquely solves), and an efficiency comparison (iters and wall-ms diffs on (puzzle, seed) pairs both solved). The findings note gets a new "Strengthened evidence" section appended.

**Tech Stack:** Polars (existing), NumPy (existing transitively via Numba), `zipmould.metrics.aggregate` (reuse), Typer (existing pattern), Loguru (existing pattern).

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `experiments/stage4/analyze_extended.py` | Create | Extended descriptive analyses, emit `extended_report.json`. |
| `experiments/stage4/out/extended_report.json` | Generate | Aggregated extended-analysis output (committed; small JSON). |
| `docs/superpowers/findings/2026-04-25-stage2-stage4-results.md` | Modify | Append "Strengthened evidence" section. |

No changes to `src/`, no changes to `manifest.toml`, no re-runs of the solver. The existing `results.parquet` is the sole input.

The user's CLAUDE.md (`Only ever plan or write tests, unit or otherwise, if explicitly asked to`) overrides the writing-plans skill's TDD default. Each task uses an in-process smoke check via `uv run python -c "..."` instead of pytest.

---

### Task 1: Skeleton + paired bootstrap CI on solve-count difference

**Files:**
- Create: `experiments/stage4/analyze_extended.py`

> **Imports policy:** Every commit must pass `ruff check` and `pyright` (strict).
> Each task imports ONLY what its own function body uses; later tasks add their
> own imports when they introduce new dependencies. Do not forward-load imports
> for downstream tasks.

- [ ] **Step 1: Write the skeleton with the bootstrap helper**

Write `/home/gtkacz/Codes/slime-mould/experiments/stage4/analyze_extended.py`:

```python
"""Stage-4 extended analyses.

Complementary descriptive statistics beyond the pre-registered McNemar
test, supporting a more honest narrative without significance-chasing
on a locked test result. Inputs: ``experiments/stage4/out/results.parquet``.
Output: ``experiments/stage4/out/extended_report.json``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl


def paired_bootstrap_diff(
    pivot: pl.DataFrame,
    baseline: str,
    candidate: str,
    n_boot: int = 10_000,
    rng_seed: int = 20260425,
    ci_level: float = 0.95,
) -> dict[str, Any]:
    """Paired bootstrap CI on (candidate_solved - baseline_solved) per puzzle.

    `pivot` is one row per puzzle with bool columns for each condition.
    Resamples puzzles with replacement; returns the empirical CI of the
    sum-of-diffs across the resampled puzzle set.
    """
    base = pivot[baseline].cast(pl.Int64).to_numpy()
    cand = pivot[candidate].cast(pl.Int64).to_numpy()
    diffs = cand - base
    n = int(diffs.shape[0])
    rng = np.random.default_rng(rng_seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boot_sums = diffs[idx].sum(axis=1).astype(np.float64)
    alpha = (1.0 - ci_level) / 2.0
    return {
        "n_puzzles": n,
        "observed_diff": int(diffs.sum()),
        "ci_low": float(np.quantile(boot_sums, alpha)),
        "ci_high": float(np.quantile(boot_sums, 1.0 - alpha)),
        "median_boot_diff": float(np.median(boot_sums)),
        "n_boot": int(n_boot),
        "ci_level": float(ci_level),
        "rng_seed": int(rng_seed),
    }
```

- [ ] **Step 2: Smoke-check the skeleton imports cleanly**

Run:

```bash
uv run python -c "from experiments.stage4.analyze_extended import paired_bootstrap_diff; print('ok')"
```

Expected: prints `ok` (no ImportError).

- [ ] **Step 3: Commit**

```bash
git add experiments/stage4/analyze_extended.py
git commit -m "feat(stage4): paired bootstrap CI on per-puzzle solve diff"
```

---

### Task 2: Seed-level reliability summary

**Files:**
- Modify: `experiments/stage4/analyze_extended.py` (append `seed_reliability`)

- [ ] **Step 1: Append the function**

Append to `/home/gtkacz/Codes/slime-mould/experiments/stage4/analyze_extended.py` (after `paired_bootstrap_diff`):

```python
def seed_reliability(df: pl.DataFrame) -> list[dict[str, Any]]:
    """Per-condition seed-level reliability across the 37-puzzle test set.

    Reports total solve rate, the count of puzzles solved by every seed
    (perfect reliability), the count never solved (zero reliability),
    and the median per-puzzle solve rate.
    """
    per_pc = df.group_by(["condition", "puzzle_id"]).agg(
        n_seeds=pl.len(),
        n_solved=pl.col("solved").sum(),
        seed_solve_rate=pl.col("solved").mean(),
    )
    return (
        per_pc.group_by("condition")
        .agg(
            n_puzzles=pl.len(),
            puzzles_perfect=(pl.col("seed_solve_rate") >= 1.0).sum(),
            puzzles_never=(pl.col("seed_solve_rate") <= 0.0).sum(),
            median_puzzle_solve_rate=pl.col("seed_solve_rate").median(),
        )
        .sort("condition")
        .to_dicts()
    )
```

- [ ] **Step 2: Smoke-check on the real parquet**

Run:

```bash
uv run python -c "
from experiments.stage4.analyze_extended import seed_reliability
from zipmould.metrics import load_results
import json
df = load_results('experiments/stage4/out/results.parquet')
print(json.dumps(seed_reliability(df), indent=2, sort_keys=True, default=float))
"
```

Expected: a 4-row JSON list (one per condition: aco-vanilla, backtracking, heuristic-only, tuned-winner). For tuned-winner: `puzzles_perfect=37`, `puzzles_never=0`, `median_puzzle_solve_rate=1.0`. For backtracking: `puzzles_perfect=36`, `puzzles_never=1`.

- [ ] **Step 3: Commit**

```bash
git add experiments/stage4/analyze_extended.py
git commit -m "feat(stage4): seed-level reliability summary per condition"
```

---

### Task 3: Asymmetric-puzzle table

**Files:**
- Modify: `experiments/stage4/analyze_extended.py` (extend imports, append `asymmetric_puzzles`)

- [ ] **Step 1: Add the `aggregate` import**

In `experiments/stage4/analyze_extended.py`, replace the imports block

```python
from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
```

with

```python
from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from zipmould.metrics import aggregate
```

- [ ] **Step 2: Append the function**

Append to `/home/gtkacz/Codes/slime-mould/experiments/stage4/analyze_extended.py`:

```python
def asymmetric_puzzles(
    df: pl.DataFrame,
    baseline: str,
    candidate: str,
) -> dict[str, list[str]]:
    """Identify puzzles where solved_any differs between two conditions.

    Returns three sorted lists: puzzles only the candidate solved, puzzles
    only the baseline solved, and puzzles neither solved.
    """
    agg = aggregate(df)
    pivot = (
        agg.filter(pl.col("condition").is_in([baseline, candidate]))
        .pivot(values="solved_any", index="puzzle_id", on="condition")
        .drop_nulls([baseline, candidate])
    )
    cand_only = sorted(
        pivot.filter((~pl.col(baseline)) & pl.col(candidate))["puzzle_id"].to_list(),
    )
    base_only = sorted(
        pivot.filter(pl.col(baseline) & (~pl.col(candidate)))["puzzle_id"].to_list(),
    )
    both_fail = sorted(
        pivot.filter((~pl.col(baseline)) & (~pl.col(candidate)))["puzzle_id"].to_list(),
    )
    return {
        "candidate_only": cand_only,
        "baseline_only": base_only,
        "both_fail": both_fail,
    }
```

- [ ] **Step 3: Smoke-check on the real parquet**

Run:

```bash
uv run python -c "
from experiments.stage4.analyze_extended import asymmetric_puzzles
from zipmould.metrics import load_results
import json
df = load_results('experiments/stage4/out/results.parquet')
print(json.dumps(asymmetric_puzzles(df, baseline='backtracking', candidate='tuned-winner'), indent=2, sort_keys=True))
"
```

Expected: `candidate_only` is a length-1 list (the one puzzle backtracking misses), `baseline_only` is `[]`, `both_fail` is `[]`.

- [ ] **Step 4: Commit**

```bash
git add experiments/stage4/analyze_extended.py
git commit -m "feat(stage4): asymmetric-puzzle table for paired conditions"
```

---

### Task 4: Efficiency comparison on intersected solved pairs

**Files:**
- Modify: `experiments/stage4/analyze_extended.py` (append `efficiency_compare`)

- [ ] **Step 1: Append the function**

Append to `/home/gtkacz/Codes/slime-mould/experiments/stage4/analyze_extended.py`:

```python
def efficiency_compare(
    df: pl.DataFrame,
    baseline: str,
    candidate: str,
) -> dict[str, Any]:
    """Paired iters/wall-ms diff on (puzzle, seed) pairs both conditions solved.

    Returns N pairs and quartiles of (candidate - baseline) for both metrics.
    A negative median means the candidate is faster on the intersected set.
    """
    base = (
        df.filter((pl.col("condition") == baseline) & pl.col("solved"))
        .select(["puzzle_id", "seed", "iters", "wall_ms"])
        .rename({"iters": "iters_base", "wall_ms": "wall_base"})
    )
    cand = (
        df.filter((pl.col("condition") == candidate) & pl.col("solved"))
        .select(["puzzle_id", "seed", "iters", "wall_ms"])
        .rename({"iters": "iters_cand", "wall_ms": "wall_cand"})
    )
    joined = base.join(cand, on=["puzzle_id", "seed"], how="inner")
    if joined.is_empty():
        return {
            "n_pairs": 0,
            "iters_diff_quartiles": None,
            "wall_ms_diff_quartiles": None,
        }
    diff_iters = (joined["iters_cand"].to_numpy() - joined["iters_base"].to_numpy()).astype(np.float64)
    diff_wall = (joined["wall_cand"].to_numpy() - joined["wall_base"].to_numpy()).astype(np.float64)
    return {
        "n_pairs": int(joined.height),
        "iters_diff_quartiles": [float(np.quantile(diff_iters, q)) for q in (0.25, 0.5, 0.75)],
        "wall_ms_diff_quartiles": [float(np.quantile(diff_wall, q)) for q in (0.25, 0.5, 0.75)],
    }
```

- [ ] **Step 2: Smoke-check on the real parquet**

Run:

```bash
uv run python -c "
from experiments.stage4.analyze_extended import efficiency_compare
from zipmould.metrics import load_results
import json
df = load_results('experiments/stage4/out/results.parquet')
print(json.dumps(efficiency_compare(df, baseline='backtracking', candidate='tuned-winner'), indent=2, sort_keys=True))
"
```

Expected: `n_pairs` is 1080 (every (puzzle, seed) pair where backtracking succeeded; tuned-winner solved all 1110, so the intersection equals backtracking's 1080). Both quartile lists are length 3 with float values.

- [ ] **Step 3: Commit**

```bash
git add experiments/stage4/analyze_extended.py
git commit -m "feat(stage4): paired efficiency comparison on intersected solved pairs"
```

---

### Task 5: Wire main + run + emit extended_report.json

**Files:**
- Modify: `experiments/stage4/analyze_extended.py` (extend imports, declare Typer app, append `main`)
- Generate: `experiments/stage4/out/extended_report.json`

- [ ] **Step 1: Extend the imports block and declare the Typer app**

In `experiments/stage4/analyze_extended.py`, replace the imports block

```python
from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl

from zipmould.metrics import aggregate
```

with

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import typer
from loguru import logger

from zipmould.logging_config import configure_logging
from zipmould.metrics import aggregate, load_results

from experiments.stage4.analyze import BASELINES, CANDIDATE, _solve_counts

app = typer.Typer(add_completion=False, no_args_is_help=False)
```

- [ ] **Step 2: Append the CLI entrypoint**

Append to `/home/gtkacz/Codes/slime-mould/experiments/stage4/analyze_extended.py`:

```python
@app.command()
def main(out_dir: Path = Path("experiments/stage4/out")) -> None:
    """Compute extended analyses and emit ``extended_report.json``."""
    configure_logging()
    out_dir.mkdir(parents=True, exist_ok=True)
    df = load_results(out_dir / "results.parquet")

    counts = _solve_counts(df)
    baselines = list(BASELINES)
    strongest = max(baselines, key=lambda b: counts[b])

    agg = aggregate(df)
    pivot = (
        agg.filter(pl.col("condition").is_in([CANDIDATE, strongest]))
        .pivot(values="solved_any", index="puzzle_id", on="condition")
        .drop_nulls([CANDIDATE, strongest])
    )

    report: dict[str, Any] = {
        "candidate": CANDIDATE,
        "strongest_baseline": strongest,
        "by_condition_solve_counts": counts,
        "seed_reliability": seed_reliability(df),
        "primary_bootstrap_diff": paired_bootstrap_diff(
            pivot,
            baseline=strongest,
            candidate=CANDIDATE,
        ),
        "asymmetric_puzzles_vs_strongest": asymmetric_puzzles(
            df,
            baseline=strongest,
            candidate=CANDIDATE,
        ),
        "secondary_asymmetric_puzzles": {
            b: asymmetric_puzzles(df, baseline=b, candidate=CANDIDATE)
            for b in baselines
            if b != strongest
        },
        "efficiency_vs_strongest": efficiency_compare(
            df,
            baseline=strongest,
            candidate=CANDIDATE,
        ),
    }
    (out_dir / "extended_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "Stage-4 extended: bootstrap CI [{:.2f}, {:.2f}] on diff vs {} (observed={})",
        report["primary_bootstrap_diff"]["ci_low"],
        report["primary_bootstrap_diff"]["ci_high"],
        strongest,
        report["primary_bootstrap_diff"]["observed_diff"],
    )


if __name__ == "__main__":
    app()
```

- [ ] **Step 3: Run the analysis**

Run:

```bash
uv run python -m experiments.stage4.analyze_extended
```

Expected: Loguru emits a single info line of the form `Stage-4 extended: bootstrap CI [<lo>, <hi>] on diff vs backtracking (observed=1)`. Exit code 0. File `experiments/stage4/out/extended_report.json` is created.

- [ ] **Step 4: Eyeball the output**

Run:

```bash
uv run python -c "
import json, pathlib
r = json.loads(pathlib.Path('experiments/stage4/out/extended_report.json').read_text())
print('keys:', sorted(r.keys()))
print('observed_diff:', r['primary_bootstrap_diff']['observed_diff'])
print('CI:', r['primary_bootstrap_diff']['ci_low'], r['primary_bootstrap_diff']['ci_high'])
print('cand-only puzzles:', r['asymmetric_puzzles_vs_strongest']['candidate_only'])
print('eff n_pairs:', r['efficiency_vs_strongest']['n_pairs'])
"
```

Expected:
- `keys` includes `asymmetric_puzzles_vs_strongest`, `by_condition_solve_counts`, `candidate`, `efficiency_vs_strongest`, `primary_bootstrap_diff`, `secondary_asymmetric_puzzles`, `seed_reliability`, `strongest_baseline`.
- `observed_diff: 1`.
- `CI` is a pair of floats; with the 1-puzzle gap, the lower bound will typically be 0.0 and upper around 1.0.
- `cand-only puzzles` is a length-1 list (the one puzzle backtracking misses).
- `eff n_pairs: 1080`.

- [ ] **Step 5: Commit module + generated report**

```bash
git add experiments/stage4/analyze_extended.py experiments/stage4/out/extended_report.json
git commit -m "feat(stage4): extended analyses CLI and emitted report"
```

---

### Task 6: Append "Strengthened evidence" section to findings note

**Files:**
- Modify: `docs/superpowers/findings/2026-04-25-stage2-stage4-results.md` (append a section)

- [ ] **Step 1: Capture the actual numbers from extended_report.json**

Run:

```bash
uv run python -c "
import json, pathlib
r = json.loads(pathlib.Path('experiments/stage4/out/extended_report.json').read_text())
b = r['primary_bootstrap_diff']
e = r['efficiency_vs_strongest']
print('OBS:', b['observed_diff'])
print('CI:', b['ci_low'], b['ci_high'])
print('N_PUZZLES:', b['n_puzzles'])
print('SEED_REL:', json.dumps(r['seed_reliability'], indent=2, sort_keys=True))
print('CAND_ONLY:', r['asymmetric_puzzles_vs_strongest']['candidate_only'])
print('EFF_N:', e['n_pairs'])
print('EFF_ITERS_Q:', e['iters_diff_quartiles'])
print('EFF_WALL_Q:', e['wall_ms_diff_quartiles'])
"
```

Expected: prints the exact numbers to substitute into the appended section. Note them.

- [ ] **Step 2: Append the section**

Append to `/home/gtkacz/Codes/slime-mould/docs/superpowers/findings/2026-04-25-stage2-stage4-results.md` (after the existing "Notes" section). Substitute the actual numbers from Step 1 in place of the bracketed placeholders. The exact tuned-winner / backtracking / heuristic-only / aco-vanilla seed-reliability rows already correspond to (37, 37, 0, 1.0), (37, 36, 1, 1.0), (37, ~7-8, ~13-14, ~0.27), (37, ~0-1, ~25-26, 0.0) — verify against Step 1 output before pasting:

```markdown

## Strengthened evidence (post-hoc, descriptive only)

These analyses were added after the locked test result to characterise the
outcome more fully than a single McNemar test. They do not adjust the
pre-registered conclusion in `report.json`.

### Paired bootstrap CI on per-puzzle solve-count difference

10,000 paired bootstrap resamples of the 37 test puzzles (rng_seed=20260425),
recomputing `tuned_solved - backtracking_solved` on each resample.

- Observed difference: <OBS> puzzle.
- 95% CI: [<CI_LOW>, <CI_HIGH>].

The CI lower bound at zero corroborates the McNemar non-significance:
the puzzle-level evidence cannot rule out a true zero gap. The CI upper
bound at one corroborates the observed direction: there is no resample
in which backtracking strictly beats tuned-winner.

### Seed-level reliability (per condition)

Each condition was run with 30 seeds per puzzle. Of the 37 test puzzles:

| Condition | Puzzles solved by every seed | Puzzles never solved | Median per-puzzle seed solve-rate |
|---|---|---|---|
| tuned-winner | <TW_PERFECT> | <TW_NEVER> | <TW_MEDIAN> |
| backtracking | <BT_PERFECT> | <BT_NEVER> | <BT_MEDIAN> |
| heuristic-only | <HO_PERFECT> | <HO_NEVER> | <HO_MEDIAN> |
| aco-vanilla | <AV_PERFECT> | <AV_NEVER> | <AV_MEDIAN> |

The tuned-winner is uniformly reliable across every (puzzle, seed) pair
on the test set, while backtracking is deterministic but fails on one
puzzle for all 30 seeds.

### Asymmetric-puzzle table (vs backtracking)

- Solved only by tuned-winner: <CAND_ONLY>.
- Solved only by backtracking: [].
- Failed by both: [].

### Efficiency on intersected solved pairs (tuned-winner minus backtracking)

On the <EFF_N> (puzzle, seed) pairs that both conditions solved:

| Metric | Q1 | Median | Q3 |
|---|---|---|---|
| iters difference | <ITERS_Q1> | <ITERS_Q2> | <ITERS_Q3> |
| wall_ms difference | <WALL_Q1> | <WALL_Q2> | <WALL_Q3> |

Negative numbers indicate the candidate finishes earlier on the
intersected set. These are descriptive efficiency aids, not a primary
hypothesis test.
```

- [ ] **Step 3: Verify the section reads sensibly**

Run:

```bash
tail -60 docs/superpowers/findings/2026-04-25-stage2-stage4-results.md
```

Expected: the new section appears at the end, with all `<...>` placeholders replaced by concrete numbers from Step 1, and no leftover `<` placeholders remain. Run `grep -n '<' docs/superpowers/findings/2026-04-25-stage2-stage4-results.md` and confirm the only matches are inside the existing pre-registered McNemar formula on line ~28.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/findings/2026-04-25-stage2-stage4-results.md
git commit -m "docs(stage4): append strengthened-evidence section to findings note"
```

---

### Task 7: Static gates

**Files:** None modified — quality verification only.

- [ ] **Step 1: Run ruff**

Run:

```bash
uv run ruff check experiments/stage4/analyze_extended.py
```

Expected: `All checks passed!`

- [ ] **Step 2: Run ty**

Run:

```bash
uv run ty check experiments/stage4/analyze_extended.py
```

Expected: `All checks passed!`

If ty flags polars wide-union returns, narrow with `cast("float | None", ...)` from `typing` (the same pattern used in `experiments/stage2/analyze.py`).

- [ ] **Step 3: Run pyright**

Run:

```bash
uv run pyright experiments/stage4/analyze_extended.py
```

Expected: `0 errors`. Pre-existing missing-stub warnings for `numba`, `joblib`, `optuna` are unrelated to this file. The import `from experiments.stage4.analyze import ...` is valid — both `experiments/__init__.py` and `experiments/stage4/__init__.py` exist, and tooling (`pyright`, `ty`, `ruff`) is configured to see `experiments` via `pyproject.toml` (`[tool.pyright] include = [..., "experiments"]`).

- [ ] **Step 4: Run bandit**

Run:

```bash
uv run bandit -r experiments/stage4/analyze_extended.py
```

Expected: `No issues identified.`

- [ ] **Step 5: No commit needed if all green**

If any gate failed, fix the issue, re-run that gate, and commit the fix with `style(stage4): fix <gate> on analyze_extended`.

---

## Self-Review

**Spec coverage:** The user picked Approach B in brainstorming. The four sub-deliverables I committed to (bootstrap CI, seed reliability, asymmetric-puzzle table, efficiency on intersected solved pairs) each have a dedicated task (Tasks 1, 2, 3, 4) plus a wiring task (Task 5) and a documentation task (Task 6). Nothing from B is missing; nothing speculative is added.

**Placeholder scan:** Task 6 Step 2 contains `<OBS>`, `<CI_LOW>`, etc. inside a markdown code fence as part of a template that the engineer fills in from Step 1's printed output. This is intentional — the actual numbers can't be hard-coded until the analysis runs. Step 3 explicitly verifies no `<...>` placeholders remain in the committed file. No other "TBD"/"TODO"/vague-handwave patterns appear.

**Type consistency:** Functions across tasks share consistent signatures: `paired_bootstrap_diff(pivot, baseline, candidate, ...)`, `seed_reliability(df)`, `asymmetric_puzzles(df, baseline, candidate)`, `efficiency_compare(df, baseline, candidate)`. The `df` parameter is uniformly `pl.DataFrame`. Return shapes match what `main` (Task 5) consumes when assembling the report. Imports of `BASELINES`, `CANDIDATE`, `_solve_counts` from `experiments.stage4.analyze` match symbols that exist in that file (verified earlier this session).

**Scope:** One module, one report, one findings-note section. Single subsystem. No decomposition needed.
