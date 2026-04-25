# ZipMould — Design Document

**Status:** Pre-registered, conceptual. No implementation has begun.
**Scope:** Solver only. Visualization is downstream and out of scope for this document.
**Pre-registration intent:** All hypotheses, baselines, splits, and decision rules below are committed *before* any algorithm output is observed. Any deviation must be logged with a justification.

---

## 1. Problem

Given a Zip puzzle (see [`README.md`](../README.md)), find a sequence of cells $\pi_1, \dots, \pi_{N^2}$ that is a Hamiltonian path on the wall-restricted grid graph and visits the $K$ waypoints in ascending label order. The corpus is 245 scraped puzzles (`benchmark/data/raw.json`), with grid sizes $N \in \{3, \dots, 10\}$ and difficulty labels $\{\text{Easy}, \text{Medium}, \text{Hard}\}$.

The puzzle is NP-hard in general, but tractable in practice for $N \le 10$. The point of this project is **not** to be the fastest solver — exact backtracking will outperform anything bio-inspired at this scale — but to study how a Li-inspired Slime Mould Algorithm (SMA) behaves on a grid-Hamiltonian problem with ordered waypoints, and to produce traces suitable for a future didactic visualizer.

## 2. Notation

| Symbol | Meaning |
|---|---|
| $G = (V, E)$ | Grid graph; $V$ = cells, $E$ = wall-free edges between 4-adjacent cells |
| $N$ | Side length of the grid; $\lvert V \rvert = N^2$ |
| $K$ | Number of labeled waypoints; $w_1, \dots, w_K \in V$ |
| $P$ | Candidate path; an ordered sequence of cells in $V$ |
| $\tau_e$ | Pheromone value on edge $e \in E$; signed real |
| $\tau^{(k)}_e$ | Stratified pheromone for inter-waypoint segment $k$ ($k = 1, \dots, K{-}1$) |
| $\eta(c, c')$ | Heuristic desirability of moving from $c$ to $c'$ |
| $f(P)$ | Fitness of path $P$ |
| $n$ | Population size (walkers per iteration) |
| $T$ | Iteration cap |
| $t \in \{0, \dots, T{-}1\}$ | Iteration index |

## 3. Algorithm: ZipMould

ZipMould is a population-based metaheuristic. Each iteration: $n$ walkers construct candidate paths by stochastic neighbour selection guided by a pheromone field $\tau$ and a domain heuristic $\eta$; fitnesses are computed; an SMA-style update modifies $\tau$ for the next iteration.

### 3.1 Encoding

A *walker* is a stateful constructor, not a fixed solution. State at construction step $s$:
- current cell $c_s$,
- visited set $V_s \subseteq V$,
- segment index $k_s \in \{1, \dots, K{-}1\}$, defined as one greater than the highest waypoint already legally visited,
- partial path $P_s = (c_0, c_1, \dots, c_s)$.

The walker starts at $c_0 = w_1$, $V_0 = \{w_1\}$, $k_0 = 1$. Termination of a single walker:

- **Success:** $V_s = V$ and $c_s = w_K$ with all waypoints visited in order.
- **Dead-end:** no legal move exists from $c_s$.
- **Length-cap:** $s = N^2 - 1$ reached without success.

This encoding is chosen because the alternatives (move strings, fractional ranks, raw permutations) all generate large fractions of infeasible candidates that waste fitness evaluations.

### 3.2 Move legality

From $c_s$, a neighbour $c' \in V$ is *legal* iff:
1. $(c_s, c') \in E$ (no wall),
2. $c' \notin V_s$ (Hamiltonian self-avoidance),
3. if $c'$ is a waypoint $w_j$, then $j = k_s + 1$ (waypoint order enforced as a hard constraint, not a fitness term — eliminates an entire class of infeasible candidates from the search space).

If no legal $c'$ exists, the walker dead-ends.

### 3.3 Heuristic $\eta$

The heuristic combines four components multiplicatively after softplus to keep them positive:

$$
\eta(c, c') \;=\; \mathrm{sp}\!\left(h_{\text{man}}\right)^{\gamma_1} \cdot \mathrm{sp}\!\left(h_{\text{warns}}\right)^{\gamma_2} \cdot \mathrm{sp}\!\left(h_{\text{art}}\right)^{\gamma_3} \cdot \mathrm{sp}\!\left(h_{\text{par}}\right)^{\gamma_4}
$$

where $\mathrm{sp}(x) = \log(1 + e^x)$, and:

- $h_{\text{man}}(c, c')$: negative Manhattan distance from $c'$ to $w_{k_s + 1}$ (the next active waypoint). Pulls walker toward the next sink.
- $h_{\text{warns}}(c, c')$: negative count of legal onward moves from $c'$ given updated visited set $V_s \cup \{c'\}$. Warnsdorff-style; prefers cells with fewer onward options first, preserving flexibility.
- $h_{\text{art}}(c, c')$: $-\infty$ if removing $c'$ from the unvisited subgraph would disconnect the remaining unvisited region into multiple components such that a Hamiltonian path cannot still cover them. Cheap articulation-style check; otherwise $0$.
- $h_{\text{par}}(c, c')$: small positive bonus when $c'$ has the chessboard parity required to maintain the colour-alternation invariant of any Hamiltonian path; small negative penalty otherwise.

Weights $\gamma_i \ge 0$ are configuration parameters.

**Why softplus rather than direct multiplication of raw values:** keeps $\eta$ strictly positive even when raw component values are negative, so that the final sampling distribution (Section 3.5) is always well-defined.

### 3.4 Pheromone field

Two variants are implemented and both are evaluated:

- **Unified ($M = \text{unified}$):** single field $\tau: E \to \mathbb{R}$.
- **Stratified ($M = \text{stratified}$):** $K{-}1$ fields $\tau^{(1)}, \dots, \tau^{(K-1)}$, one per inter-waypoint segment.

In both variants $\tau$ is **signed**: it may take negative values, representing repulsion. This is the design choice that distinguishes a Li-inspired update from plain ACO; without it, the bottom-half walkers in Li's split cannot exert their "wrap food" influence.

To prevent unbounded growth or overflow during numerical updates, $\tau$ is clipped to $[-\tau_{\max}, +\tau_{\max}]$ with $\tau_{\max}$ a configuration parameter.

### 3.5 Sampling distribution

At step $s$ in segment $k$, the walker selects the next cell from the legal neighbour set $\mathcal{L}_s$ via softmax over a logit:

$$
\mathrm{logit}(c \to c') \;=\; \alpha \cdot \tau^{*}_{(c, c')} \;+\; \beta \cdot \log \eta(c, c')
$$

$$
P(c \to c') \;=\; \frac{\exp \mathrm{logit}(c \to c')}{\sum_{c'' \in \mathcal{L}_s} \exp \mathrm{logit}(c \to c'')}
$$

where $\tau^{*}_e = \tau_e$ in the unified variant, and $\tau^{*}_e = \tau^{(k_s)}_e$ in the stratified variant. $\alpha, \beta \ge 0$ are configuration weights.

**Why softmax instead of $\tau^\alpha \eta^\beta$:** the multiplicative form requires $\tau \ge 0$. The softmax-of-logit form admits signed $\tau$ and is numerically stable for any clip range.

### 3.6 Fitness

For a partial or completed path $P$ ending at cell $c$ in segment $k_{\max}(P)$:

$$
f(P) \;=\; \underbrace{\lvert P \rvert}_{\text{coverage}} \;+\; \beta_1 \cdot k_{\max}(P) \;+\; \beta_2 \cdot \frac{1}{1 + d_M(c,\, w_{k_{\max}(P)+1})} \;+\; \beta_3 \cdot \mathbb{1}[P\ \text{is a valid solution}]
$$

with $d_M$ the Manhattan distance, and $\beta_1, \beta_2, \beta_3 \ge 0$.

This fitness is monotone under "the walker made progress" in three smooth or near-smooth ways (length grew, a new waypoint was reached, current cell got closer to the next waypoint). The single discontinuity is the success-bonus $\beta_3 \mathbb{1}[\cdot]$, which is intentional: solutions should rank far above non-solutions. Order violations are *not* penalised in $f$ because they cannot occur (Section 3.2).

### 3.7 Population update (Li-inspired SMA)

Between iterations $t$ and $t{+}1$:

1. Construct $n$ walkers, yielding paths $P_1, \dots, P_n$ with fitnesses $f_1, \dots, f_n$.
2. Sort by descending fitness; let $r(i) \in \{1, \dots, n\}$ be the rank of walker $i$.
3. **Compute signed rank weights:**

$$
W_i \;=\; \frac{n - 2 r(i) + 1}{n - 1} \quad \in [-1, +1]
$$

This is monotone in fitness ($W_1 = +1$, $W_n = -1$, linear in between). Top-half walkers contribute attraction; bottom-half walkers contribute repulsion. This is a deliberate simplification of Li's logarithmic weight (which we judged unnecessarily ornate for the discrete combinatorial setting; the attraction–repulsion structure is the substantive content).

4. **Compute SMA oscillator and contraction:**

$$
v_b(t) \;=\; \mathrm{tanh}\!\left(1 - \frac{t}{T}\right), \qquad v_c(t) \;=\; 1 - \frac{t}{T}
$$

$v_b$ governs deposit magnitude; $v_c$ governs decay (analogous to Li's contraction). Both decrease with $t$, biasing late iterations toward exploitation of accumulated $\tau$.

5. **Update pheromone field.** For unified mode:

$$
\tau_e(t{+}1) \;=\; \mathrm{clip}\!\left( v_c(t)\,\tau_e(t) \;+\; v_b(t)\sum_{i: e \in P_i} W_i,\; -\tau_{\max},\; +\tau_{\max} \right)
$$

For stratified mode, the same update is applied per segment, with each edge's deposit going to $\tau^{(k)}$ where $k$ is the segment in which the walker traversed that edge:

$$
\tau^{(k)}_e(t{+}1) \;=\; \mathrm{clip}\!\left( v_c(t)\,\tau^{(k)}_e(t) \;+\; v_b(t) \sum_{i: e \in P_i^{(k)}} W_i,\; -\tau_{\max},\; +\tau_{\max} \right)
$$

where $P_i^{(k)}$ denotes the subsequence of $P_i$ that lies in segment $k$.

6. **Restart noise.** With probability $z$, each edge has its pheromone reset toward $0$ (Gaussian perturbation with mean $0$, std $\tau_{\max} / 4$). This is Li's $z$-branch escape.

### 3.8 Termination

- **Solved:** any walker produces a valid solution. Record path; halt.
- **Iteration cap:** $t = T$ reached without solution. Report best partial path.
- **Wall-clock cap:** total compute exceeds $W_{\max}$ seconds (configuration parameter; production default 300 s = 5 min per puzzle).

---

## 4. Resolved pre-coding recommendations

The six recommendations from the prior critical review are resolved as follows:

| # | Recommendation | Resolution |
|---|---|---|
| 1 | Add unified-pheromone variant as a parallel arm | `pheromone_mode ∈ {unified, stratified}` is a configuration knob (Section 3.4). Both are evaluated in Stage 1. No premature commitment. |
| 2 | Make $\tau$ signed; use softmax sampling | $\tau$ is signed real, clipped to $[-\tau_{\max}, +\tau_{\max}]$ (Section 3.4). Sampling is softmax over logit $\alpha\tau + \beta \log \eta$ (Section 3.5). Restores Li-style attraction–repulsion. |
| 3 | Smooth fitness with continuous waypoint progress | New fitness has continuous coverage, integer-but-monotone $k_{\max}$, smooth Manhattan-progress, and a single intentional cliff at success (Section 3.6). Order violations are precluded by construction (Section 3.2), so they don't appear in $f$. |
| 4 | Specify baselines and seed budget | See Section 6.1 for the four baselines and Section 6.4 for the seed budget. |
| 5 | Define train/dev/test split | See Section 6.2. Stratified split fixed before any runs. |
| 6 | Plan Stage 1 ablation as the first experiment | See Section 7.1. Hypothesis, metrics, and decision rule are pre-registered. |

---

## 5. Configuration parameters

All parameters with their Stage 1 default values (literature-inspired or otherwise documented). Stage 1 uses these defaults *without* tuning, to give the ablation a clean read.

| Parameter | Symbol | Default | Range explored later |
|---|---|---|---|
| Pheromone–heuristic balance (logit slope on $\tau$) | $\alpha$ | $1.0$ | $[0, 4]$ |
| Heuristic exponent (logit slope on $\log \eta$) | $\beta$ | $2.0$ | $[0, 4]$ |
| Manhattan heuristic weight | $\gamma_1$ | $1.0$ | $[0, 2]$ |
| Warnsdorff heuristic weight | $\gamma_2$ | $1.0$ | $[0, 2]$ |
| Articulation heuristic weight | $\gamma_3$ | $1.0$ | $\{0, 1\}$ (on/off) |
| Parity heuristic weight | $\gamma_4$ | $0.5$ | $[0, 1]$ |
| Fitness: waypoint reach bonus | $\beta_1$ | $N^2$ | derived from $N$ |
| Fitness: progress-toward-next-waypoint weight | $\beta_2$ | $1.0$ | $[0, 5]$ |
| Fitness: completion bonus | $\beta_3$ | $10\, N^2$ | fixed (dominates) |
| Pheromone clip | $\tau_{\max}$ | $10.0$ | $\{1, 5, 10, 20\}$ |
| Restart probability | $z$ | $0.05$ | $\{0, 0.01, 0.05, 0.1\}$ |
| Initial pheromone | $\tau_0$ | $0.0$ | fixed |
| Population size | $n$ | $30$ | $\{10, 30, 60\}$ |
| Iteration cap | $T$ | $200$ (Stage 1), $1000$ (production) | — |
| Wall-clock cap (seconds) | $W_{\max}$ | $300$ | — |
| Pheromone mode | $M$ | both | $\{$unified, stratified$\}$ |

The fitness defaults set $\beta_1 = N^2$ so that reaching one more waypoint always strictly dominates filling more cells without progress — a deliberate lexicographic ordering implemented through linearly-large coefficients.

---

## 6. Validation methodology

### 6.1 Baselines

Four baselines, plus four ZipMould variants, totalling eight conditions:

| Condition | Construction | Pheromone | Update | Purpose |
|---|---|---|---|---|
| `random` | uniform over legal neighbours | none | — | absolute lower bound |
| `heuristic-only` | $\eta$-weighted softmax | none | — | isolates contribution of $\eta$ alone |
| `aco-vanilla` | $\tau \eta$-weighted, $\tau \ge 0$ | unsigned, unified | classical ACO (constant evaporation, fitness-proportional positive deposit) | isolates contribution of *Li-style* updates over ACO |
| `zipmould-uni-pos` | as 3.5 with $\tau$ clipped to $\ge 0$ | unsigned, unified | Section 3.7 | tests Li-style update without negative pheromone |
| `zipmould-uni-signed` | as 3.5 | signed, unified | Section 3.7 | full Li-inspired ZipMould, unified field |
| `zipmould-strat-pos` | as 3.5 with $\tau \ge 0$ | unsigned, stratified | Section 3.7 | tests stratification under positive-only |
| `zipmould-strat-signed` | as 3.5 | signed, stratified | Section 3.7 | full Li-inspired ZipMould, stratified field |
| `backtracking` | DFS with forward checking, waypoint-order pruning, articulation pruning | — | — | exact upper bound, time-limited to $W_{\max}$ |

The two-by-two structure (unified vs. stratified) × (positive vs. signed) is intentional: each axis is a hypothesis, and a $2\times 2$ design isolates main effects.

### 6.2 Data splits

The 245 puzzles are split into **train (172) / dev (37) / test (36)** by stratified random sampling.

**Stratification key:** $(\text{size\_bucket}, \text{difficulty})$ where
- size\_bucket: small ($N \in \{3,4,5\}$, 28 puzzles), medium ($N \in \{6,7\}$, 102), large ($N \in \{8,9,10\}$, 115).
- difficulty: Easy / Medium / Hard.

This produces 9 strata. Within each stratum we sample 70/15/15 rounded to integers. Empty strata are tolerated (e.g., 3×3 Hard has 0 puzzles).

The split is generated **once**, with a fixed seed (`SPLIT_SEED = 20260424`), and persisted to `benchmark/data/splits.json`. The test set is sealed: no algorithmic decision may use information from test puzzles. Touching the test set more than once invalidates the entire reported result.

**Train** is used for hyperparameter tuning (Stage 2). **Dev** is used for ablations and design iteration (Stages 1, 3). **Test** is used once at the very end (Stage 4).

### 6.3 Primary metrics

For a (configuration, puzzle) pair across $S$ seeds:

- **success\_rate** $= (1/S) \sum_s \mathbb{1}[s\text{-th seed produced a valid solution within budget}]$
- **mean\_iters\_to\_solve** $= $ mean iteration index at which the best solution was first observed, conditional on solving. Undefined if 0/$S$ seeds solved.
- **best\_fitness\_normalised** $= (1/S) \sum_s f^\star_s / (N^2 + \beta_1 (K-1) + \beta_2 + \beta_3)$, the per-seed best-fitness divided by the theoretical max. Defined for all puzzles.

Aggregate metrics over a puzzle set: macro-average across puzzles (each puzzle weighted equally regardless of $S$).

### 6.4 Seed budget

- **Stage 1 (ablation, dev set):** $S = 10$ seeds, all 8 conditions × 37 dev puzzles = $2{,}960$ runs. Worst-case wall-clock at $W_{\max} = 300$ s would be 247 hours; realistic estimate at ~5 s per run mean is ~4 hours.
- **Stage 2 (hyperparameter sweep, train set):** Bayesian optimisation, budget of $\sim 200$ trials × 5 seeds × 30 train puzzles = $30{,}000$ runs. Realistic ~40 hours.
- **Stage 3 (design-iteration ablations, dev set):** as Stage 1, repeated as needed.
- **Stage 4 (final report, test set):** $S = 30$ seeds (tighter CI), winning ZipMould variant + 3 baselines × 36 test puzzles = $4{,}320$ runs. Touched once.

Random seeds are integers $\{0, 1, \dots, S{-}1\}$; deterministic given the seed. The full set of seeds is logged per run.

---

## 7. Stage 1 ablation — pre-registered protocol

This is the first experiment. Its outcome determines whether the project continues as designed.

### 7.1 Hypothesis

> **H1.** The Li-inspired SMA pheromone layer measurably improves puzzle-solving performance over a heuristic-only walker, on the dev set, under default Stage 1 hyperparameters.

### 7.2 Operationalisation

"Measurably improves" is defined via two pre-registered comparisons:

- **C1 (success-rate):** at least one of the four ZipMould variants achieves higher mean `success_rate` on the dev set than `heuristic-only`, with the per-puzzle paired difference significant by McNemar's test at $p < 0.05$.
- **C2 (effect size):** the absolute increase in dev-set macro-mean `success_rate` is at least 5 percentage points.

### 7.3 Decision rule

| Outcome | Decision |
|---|---|
| C1 holds **and** C2 holds | **Proceed to Stage 2** with the strongest ZipMould variant. |
| C1 holds, C2 fails (gap is statistically significant but $< 5$ pp) | **Proceed cautiously.** Run Stage 1' (next subsection) on hard-stratum subset; if effect concentrates there, continue; otherwise rebrand as "heuristic walker with adaptive guidance". |
| C1 fails | **Stop.** SMA contributes nothing detectable. Either redesign (add ideas from Section 9) or pivot the project's framing. |

Additionally, secondary diagnostic comparisons (not gating):
- ZipMould-signed vs. ZipMould-positive (does the Li-style sign matter?).
- Stratified vs. unified (does segment-stratification help?).
- ZipMould-best vs. `aco-vanilla` (does Li-style oscillation/contraction add anything over plain ACO?).

These inform Stage 2 design but are not part of the gate.

### 7.4 Stage 1' — hard-only re-test (only if Stage 1 is C1-yes-C2-no)

Restrict to dev puzzles labelled `Hard`. If gap on this subset is $\ge 10$ pp with $p < 0.05$, proceed to Stage 2 with the framing "ZipMould helps on hard instances".

### 7.5 Pre-registration commitment

The above hypothesis, comparisons, and decision rule are committed before any algorithm output is observed. Any post-hoc adjustment must be recorded as a deviation in the eventual report, with reasoning. This is not a research paper, but the discipline matters: without it, the "atlas" angle (Section 9) is impossible to defend later.

---

## 8. Trace format (CBOR)

The solver emits a per-run trace suitable for a downstream visualizer. CBOR is chosen for compactness over JSON without giving up self-describing structure. Schema (described as a CBOR map):

```
TRACE := {
  "version":      uint,                          // schema version (start at 1)
  "puzzle_id":    text,                          // matches benchmark/data/raw.json id
  "config":       CONFIG,                         // all parameters from Section 5
  "seed":         uint,
  "header": {
    "N":          uint,
    "K":          uint,
    "waypoints":  [[uint, uint]],                // K cells in label order
    "walls":      [[[uint,uint],[uint,uint]]]    // unordered pairs of adjacent cells
  },
  "frames":       [FRAME],                       // one per logged iteration
  "footer": {
    "solved":           bool,
    "solution":         [[uint,uint]] | null,    // length-N^2 sequence if solved
    "iterations_used":  uint,
    "wall_clock_s":     float,
    "best_fitness":     float
  }
}

FRAME := {
  "t":          uint,
  "v_b":        float,
  "v_c":        float,
  "tau_delta":  TAU_DELTA,                       // sparse change since last logged frame
  "best": {
    "path":     [[uint,uint]],
    "fitness":  float
  },
  "walkers":    [WALKER]                         // length capped at config.visible_walkers
}

TAU_DELTA := {
  "mode":   "unified" | "stratified",
  "edges":  [[EDGE_ID, FIELD_K, FLOAT_DELTA]]    // FIELD_K omitted in unified mode
}

WALKER := {
  "id":       uint,
  "cell":     [uint, uint],
  "segment":  uint,
  "status":   "alive" | "dead-end" | "complete",
  "fitness":  float
}
```

Frame logging is sub-sampled: a frame is emitted every $\Delta_t$ iterations (configuration parameter, default `5`). Pheromone is delta-encoded; first frame logs full $\tau$, subsequent frames log only changed edges with magnitude above $\epsilon$.

Estimated raw size per puzzle for $N = 8$, $K = 6$, $T = 200$, $\Delta_t = 5$: ~50–150 KB CBOR uncompressed.

The schema is versioned; any breaking change increments `version`. The downstream visualizer pins a minimum version.

---

## 9. Open questions / known limitations

These are deferred to Stage 2 or beyond, but flagged here so they aren't forgotten.

1. **Late-segment learning signal (stratified mode).** $\tau^{(k)}$ for large $k$ receives no deposits until walkers complete segments $1, \dots, k{-}1$. Possible mitigations (untested): partial-credit deposits across segments; bidirectional walkers seeded from $w_K$; curricular activation of segments. Investigated only if Stage 1 says stratified is worth pursuing.
2. **Walker recovery.** Currently no backtracking inside a single walker. Adding a $k$-step lookahead at each construction step would dramatically improve solve rate but blurs the boundary with local search. Reserved for Stage 3.
3. **Source uniformity.** All 245 puzzles come from one source (LinkedIn-scraped, per upstream). External validity claims are limited to that distribution.
4. **Stochastic CI width.** $S = 10$ seeds gives ±~30 pp Wilson 95% CI on per-puzzle success rate. This is fine for aggregate metrics but loose per-puzzle. The test set ($S = 30$) is tighter (±~17 pp).
5. **Compute estimate uncertainty.** "Single-digit minutes" cap is generous, but an unrecoverably bad parameter setting could time out frequently. Stage 1 default of $T = 200$ is conservative and exists partly to bound total wall-clock.

---

## 10. Decision rules summary (pre-registration table)

| When | Decision rule | Action |
|---|---|---|
| Before any code | Splits frozen (Section 6.2) | Generate `splits.json` once, never regenerate. |
| End of Stage 1 | C1 (McNemar $p < 0.05$) and C2 ($\Delta \ge 5$ pp) on dev | Proceed to Stage 2 with best ZipMould variant. |
| End of Stage 1 | C1 holds, C2 fails | Run Stage 1' on hard-stratum dev. If $\Delta \ge 10$ pp, proceed; else rebrand. |
| End of Stage 1 | C1 fails | Stop or redesign. |
| End of Stage 2 | Best train-tuned config does not regress on dev relative to Stage 1 defaults | Lock config; proceed to Stage 4. |
| End of Stage 4 | Test-set results reported once | No further tuning. Report. |

Deviations from this table during execution must be logged with date, reason, and impact on interpretation.

---

## 11. What this document does *not* cover

- **Visualization.** Trace format is specified (Section 8) so the visualizer has a contract; everything beyond that is out of scope.
- **Implementation language and structure.** Python is implied by the existing codebase, but module layout, library choices, and packaging are not part of this design.
- **Test strategy.** Unit/integration tests are out of scope here; they will be planned alongside implementation.
- **Hyperparameter optimisation method.** Stage 2 will use Bayesian optimisation (likely `optuna`), but the exact protocol is specified in Stage 2's own design note when written.
