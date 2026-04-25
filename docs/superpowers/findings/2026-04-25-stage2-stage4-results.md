# Stage 2 + Stage 4 Results

**Date:** 2026-04-25
**Spec:** docs/superpowers/specs/2026-04-25-zipmould-stage2-stage4-design.md

## Stage 2 outcome

| Variant | Dev solved (tuned) | Dev solved (default) | Decision |
|---|---|---|---|
| zipmould-uni-signed | 370 | 223 | locked: tuned >= default |
| zipmould-uni-positive | 370 | 186 | locked: tuned >= default |
| zipmould-strat-signed | 369 | 220 | locked: tuned >= default |
| zipmould-strat-positive | 369 | 188 | locked: tuned >= default |

(Dev split = 37 puzzles x 10 seeds = 370 (puzzle, seed) pairs; granularity matches `evaluate(...)`.)

**Overall winner:** `zipmould-uni-positive` with dev_solved=370. Tied with `zipmould-uni-signed` at 370/370; tiebreaker on Stage-1 median iters-to-solve (11 vs 25) selects the unified-positive variant.

All four variants passed the non-regression gate (tuned >= default) and were locked to `configs/tuned/<variant>.toml`. Each Optuna study ran 50 TPE trials with `multivariate=True`, `n_startup_trials=10`, `seed=42`, persisted to per-variant SQLite stores.

## Stage 4 outcome

Held-out test split, 30 seeds x 37 puzzles x 4 conditions = 4,440 runs. Zero failed jobs. Aggregated to 37 puzzle rows per condition via `solved_any`.

| Condition | Puzzles solved (of 37) | (puzzle, seed) pairs solved (of 1110) |
|---|---|---|
| tuned-winner | 37 | 1110 |
| backtracking | 36 | 1080 |
| heuristic-only | 22 | 414 |
| aco-vanilla | 10 | 73 |

**Primary McNemar test** (`tuned-winner` vs `backtracking`, the strongest baseline by test solve count): n=37, b=1, c=0, stat=1.000, significant=False. **Decision:** trend favours candidate (does not clear pre-registered threshold b > c + 1.96 sqrt(b+c) = 1.96).

**Secondary McNemar tests** (descriptive, not multiplicity-corrected):

| Baseline | n | b | c | stat | Significant |
|---|---|---|---|---|---|
| aco-vanilla | 37 | 27 | 0 | 5.196 | yes |
| heuristic-only | 37 | 15 | 0 | 3.873 | yes |

## Notes

The tuned ZipMould (uni-positive) is **descriptively optimal** on the held-out test split: 100% solve rate at both the puzzle level (37/37) and the (puzzle, seed) level (1110/1110), with no test puzzle losses against any baseline (c=0 across all three comparisons). It strictly dominates `aco-vanilla` and `heuristic-only` at the McNemar significance threshold and matches-or-beats `backtracking` descriptively.

The primary comparison against `backtracking` does not reach significance because the corpus is too small to resolve a one-puzzle gap: with the pre-registered threshold the candidate would have needed at least b=2, c=0 to clear. The seed-level picture is much sharper (tuned-winner is perfectly reliable; backtracking has 30 seed-level misses concentrated on the single puzzle it fails to solve), but the spec called for a single puzzle-level McNemar test, so the headline number stays at b=1, c=0.

Practical implication for the algorithm: the tuned configuration appears to have closed the operational gap to the strongest deterministic baseline on this benchmark while keeping the stochastic-anytime profile of an ACO method (median Stage-1 iters-to-solve = 11). The residual question is whether the gap to backtracking truly inverts on harder instances or whether the test set is at the easy end of the distribution. Sensible follow-ups: (1) extend the test corpus past 37 puzzles to gain statistical power, (2) inspect the one puzzle backtracking misses for a structural pattern (likely a long-tail with deep dead-ends where backtracking's chronological order thrashes), (3) re-run on a harder puzzle distribution to stress-test before generalising.
