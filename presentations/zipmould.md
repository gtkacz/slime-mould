---
marp: true
theme: default
class: invert
math: katex
paginate: true
size: 16:9
title: "ZipMould — A Slime-Mould-Inspired Solver for Zip Puzzles"
author: "Gabriel Mitelman Tkacz"
description: "Porting Li et al.'s 2020 SMA from continuous optimisation to a discrete Hamiltonian-path domain."

style: |
  section {
    background: #0f172a;
    color: #e2e8f0;
    font-family: 'Inter', 'Helvetica Neue', system-ui, sans-serif;
    padding: 50px 70px 60px;
    font-size: 26px;
    line-height: 1.45;
  }
  h1 {
    color: #22d3ee;
    font-weight: 700;
    letter-spacing: -0.015em;
    font-size: 1.6em;
    margin-bottom: 0.35em;
  }
  h2 {
    color: #22d3ee;
    font-weight: 600;
    border-bottom: 2px solid #1e293b;
    padding-bottom: 0.25em;
    margin-bottom: 0.55em;
    font-size: 1.25em;
  }
  h3 { color: #fbbf24; font-weight: 600; font-size: 1.0em; margin-top: 0.6em; margin-bottom: 0.25em; }
  strong { color: #fbbf24; }
  em { color: #94a3b8; }
  code {
    background: #1e293b;
    color: #f0abfc;
    padding: 0.08em 0.32em;
    border-radius: 3px;
    font-size: 0.86em;
    font-family: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
  }
  pre {
    background: #020617;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 0.75em 1em;
    font-size: 0.62em;
    line-height: 1.45;
    overflow-x: auto;
  }
  pre code { background: transparent; color: #cbd5e1; padding: 0; font-size: inherit; }
  blockquote { border-left: 4px solid #fbbf24; color: #94a3b8; font-style: italic; padding-left: 1em; margin-left: 0; }
  a { color: #22d3ee; text-decoration: none; }
  table { border-collapse: collapse; margin: 0.5em 0; font-size: 0.78em; width: 100%; }
  th, td { border: 1px solid #334155; padding: 0.32em 0.6em; text-align: left; vertical-align: top; }
  th { background: #1e293b; color: #fbbf24; font-weight: 600; }
  section.lead { padding: 80px 100px; }
  section.lead h1 { font-size: 2.2em; text-align: left; margin-bottom: 0.3em; }
  section.lead h2 { border: none; text-align: left; color: #94a3b8; font-weight: 400; font-size: 1.1em; margin-bottom: 1.5em; }
  section.lead p { font-size: 1.0em; color: #94a3b8; }
  section.lead p strong { color: #e2e8f0; font-weight: 600; }
  section::after {
    color: #475569;
    font-size: 0.6em;
    bottom: 18px;
    right: 30px;
  }
  footer { color: #64748b; font-size: 0.55em; }
  .columns { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5em; }
  .columns-wide-left { display: grid; grid-template-columns: 3fr 2fr; gap: 1.5em; }
  .ribbon {
    background: #1e293b;
    border-left: 4px solid #22d3ee;
    padding: 0.6em 1em;
    margin: 0.4em 0;
    border-radius: 0 4px 4px 0;
    font-size: 0.92em;
  }
  .key {
    color: #fbbf24;
    font-weight: 600;
  }
  .muted {
    color: #64748b;
    font-size: 0.78em;
  }
  ul li, ol li { margin-bottom: 0.25em; }
  .citation {
    color: #64748b;
    font-size: 0.7em;
    font-style: italic;
    margin-top: 1em;
  }
  .math-display { text-align: center; margin: 0.6em 0; }
---

<!-- _class: lead -->
<!-- _paginate: false -->

# ZipMould

## A slime-mould-inspired solver for Zip puzzles

**Gabriel Mitelman Tkacz** · May 2026

From continuous metaheuristic to discrete combinatorial search — porting **Li et al. (2020)** to a Hamiltonian-path domain.

---

## Three acts, twenty minutes

<div class="columns">

<div>

### Act 1 · Li (≈7 min)
What is the **Slime Mould Algorithm**?
The biology, the equations, the empirical case.

### Act 2 · ZipMould (≈7 min)
Porting continuous SMA to a **discrete combinatorial** problem. Where the analogy holds, where it breaks, what we changed.

### Act 3 · Demo (≈5 min)
Live trace replay in the **Vue 3 visualiser**.

</div>

<div>

<div class="ribbon">

**The bridge in one line**

Li's update
$$X(t+1) = v_c \cdot X(t) + v_b \cdot (W \cdot X_A - X_B)$$

becomes ZipMould's edge update
$$\tau \leftarrow v_c \cdot \tau + v_b \cdot \Delta_{\text{rank-weighted}}$$

</div>

</div>

</div>

---

## What is *Physarum polycephalum*?

- **Acellular slime mould.** Single multinucleate organism, no nervous system.
- Forages by extending a **venous network** through a substrate.
- **Positive feedback**: high food concentration → faster cytoplasmic flow → vein thickens.
- **Negative feedback**: starved branches retract.
- Demonstrated to solve mazes, approximate **Tokyo's rail network**, and behave like a distributed optimiser without any centralised control.

<div class="ribbon">

The algorithm we'll see formalises three observed behaviours: <strong>approaching food</strong>, <strong>wrapping food</strong> (the venous-thickness feedback), and <strong>grabbling food</strong> (the bio-oscillator amplitude).

</div>

<p class="citation">Li, Chen, Wang, Heidari & Mirjalili (2020), <em>Future Generation Computer Systems</em> 111, 300–323. Tero et al. (2010), <em>Science</em> 327, 439–442.</p>

---

## SMA Eq. (2.1) — *approach food*

<div class="math-display">

$$
\vec{X}(t+1) =
\begin{cases}
\vec{X_b}(t) + \vec{v_b} \cdot \big(\vec{W} \cdot \vec{X_A}(t) - \vec{X_B}(t)\big), & r < p \\[4pt]
\vec{v_c} \cdot \vec{X}(t), & r \geq p
\end{cases}
$$

</div>

- $\vec{X_b}$ — best individual found so far.
- $\vec{X_A}, \vec{X_B}$ — two random individuals (provides exploration vector).
- $\vec{W}$ — fitness-rank-derived **weight** (Eq. 2.5, next slide).
- $\vec{v_b} \in [-a, a]$, where $a = \mathrm{arctanh}(1 - t/T)$.
- $\vec{v_c}$ decreases linearly from $1$ to $0$.
- $p = \tanh\lvert S(i) - DF\rvert$ — adaptive switching threshold.

<p class="citation">Li et al. (2020), §2.3.1.</p>

---

## SMA Eq. (2.5) — the weight $\vec{W}$

<div class="math-display">

$$
W_i =
\begin{cases}
1 + r \cdot \log\!\Big(\dfrac{bF - S(i)}{bF - wF} + 1\Big), & i \in \text{top half (good fitness)} \\[6pt]
1 - r \cdot \log\!\Big(\dfrac{bF - S(i)}{bF - wF} + 1\Big), & i \in \text{bottom half (poor fitness)}
\end{cases}
$$

</div>

- **Top half** of population pulls toward favourable areas — **positive feedback**.
- **Bottom half** is pushed away — **negative feedback** simulating retraction of starved veins.
- $\log$ tames the rate of change; $r \sim \mathcal{U}(0,1)$ keeps the response stochastic.
- Captures the slime mould "preference" via **fitness ranking**, not absolute fitness.

<p class="citation">Li et al. (2020), §2.3.2 — "Wrap food" mathematical model.</p>

---

## SMA Eq. (2.7) — the full update

<div class="math-display">

$$
\vec{X^{*}} =
\begin{cases}
\text{rand} \cdot (UB - LB) + LB, & \text{rand} < z \\[4pt]
\vec{X_b}(t) + \vec{v_b} \cdot (W \cdot \vec{X_A} - \vec{X_B}), & r < p \\[4pt]
\vec{v_c} \cdot \vec{X}(t), & r \geq p
\end{cases}
$$

</div>

<div class="columns-wide-left">

<div>

- Three branches, **per individual, per iteration**:
  1. **z-branch** (prob $z = 0.03$ in Li): random restart in the search box.
  2. **Approach** branch (prob $\approx p$): exploit best with W-weighted exploration.
  3. **Oscillate** branch: shrink toward origin with $v_c$.

</div>

<div class="ribbon">

The z-branch is what lets SMA *escape local optima* without explicit niching or restarting the whole population.

</div>

</div>

<p class="citation">Li et al. (2020), §2.3.2 Eq. (2.7); $z$ chosen as 0.03 from sensitivity sweep §3.4.</p>

---

## The $v_b$ / $v_c$ schedule

<div class="columns">

<div>

### $v_c$ — linear contraction
$$v_c \in [-1, 1], \quad v_c \to 0 \text{ as } t \to T$$

Smoothly damps the *oscillate* branch. Late in the run, $v_c \cdot X \approx 0$: the agent stops drifting on its own.

### $v_b$ — saturating amplitude
$$v_b \in [-a, a], \quad a = \mathrm{arctanh}(1 - t/T)$$

Early: $a \to \infty$ → big jumps. Late: $a \to 0$ → fine-grained exploitation.

</div>

<div class="ribbon">

**Combined effect**

Early iterations: <strong>exploration</strong> dominates via large $v_b$.

Late iterations: <strong>exploitation</strong> dominates as both $v_b$ and $v_c$ shrink.

The slime mould "decides whether to approach the current source or seek another" — encoded as oscillation amplitude.

</div>

</div>

<p class="citation">Li et al. (2020), §2.3.3 "Grabble food", Fig. 5.</p>

---

## SMA — the algorithm

```text
INITIALISE population X_1 ... X_n at random in [LB, UB]
FOR t = 1 ... T:
    evaluate fitness S(i) for all i
    sort population, identify bF, wF, X_b
    compute W via Eq. (2.5)        # rank-based positive/negative weights
    FOR each individual i:
        sample r ~ U(0,1), rand ~ U(0,1)
        update v_b, v_c, p          # schedule
        IF rand < z:
            X_i <- random restart in [LB, UB]
        ELIF r < p:
            X_i <- X_b + v_b * (W * X_A - X_B)   # approach
        ELSE:
            X_i <- v_c * X_i                       # oscillate
RETURN bF, X_b
```

- One outer loop, three inner branches, no derivatives, no gradients.
- Five hyperparameters total: population $n$, iterations $T$, restart prob $z$, plus the schedule constants baked into $v_b, v_c$.

---

## Why the field cared

<div class="columns">

<div>

### Empirical case
- **23 classical benchmarks** (unimodal + multimodal) + **10 CEC2014** functions: SMA wins or ties first on the majority.
- Outperforms WOA, GWO, MFO, BA, SCA, PSO, SSA, MVO, ALO on most multimodal cases.
- **4 engineering design problems** (welded beam, pressure vessel, cantilever, I-beam): best feasible solution on all four.
- Convergence curves show **fast early descent + accurate late refinement**.

</div>

<div>

### Why it works
- $W$ implements an explicit **diversity term** — bottom-half repulsion prevents premature convergence.
- $v_b$ schedule provides **automatic exploration→exploitation** transition, no operator scheduling.
- $z$-branch escape is **simple but effective** for getting out of local basins.

</div>

</div>

<p class="citation">Li et al. (2020), Tables 5–22; Figs. 9–14 (convergence curves).</p>

---

## The Zip puzzle

<div class="columns-wide-left">

<div>

### Formal definition
Given a grid $G_{N \times N}$ with:
- $K$ ordered waypoints $w_1, w_2, \dots, w_K$
- A set of **walls** (forbidden edges between adjacent cells)
- A set of **blocked** cells

Find a **Hamiltonian path** $\pi_1, \dots, \pi_L$ (where $L = N^2 - |\text{blocked}|$) such that:
1. consecutive cells are 4-adjacent and not wall-separated,
2. waypoints appear in **ascending order**,
3. $\pi_1 = w_1$ and $\pi_L = w_K$.

</div>

<div class="ribbon">

**LinkedIn's daily Zip puzzle** popularised the format.

The decision problem is **NP-complete** (reduces to Hamiltonian-path-with-pinned-vertices), but tractable in practice for $N \leq 10$ — which is exactly where metaheuristics earn their keep.

</div>

</div>

---

## Why continuous SMA can't transfer directly

<div class="columns">

<div>

### Li's SMA lives in $\mathbb{R}^d$
- $\vec{X_A} - \vec{X_B}$ is a Euclidean direction vector.
- $v_b \cdot W$ scales an amplitude in continuous space.
- Step is just vector addition.

### Zip lives on a graph
- "Position" is a partial Hamiltonian path, not a coordinate.
- $\vec{X_A} - \vec{X_B}$ is **undefined** between two paths.
- The natural state is **edge usage**, not point coordinates.

</div>

<div class="ribbon">

### The bridge
Borrow **stigmergy** from <strong>Ant Colony Optimisation</strong> (Dorigo, 1992): pheromone $\tau$ on edges plays the role of the agent state.

Then port SMA's <strong>update dynamics</strong> — the $v_b$/$v_c$ schedule, signed rank weights, and z-restart — onto the pheromone, not onto a coordinate.

</div>

</div>

---

## ZipMould — pipeline

```text
┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  Puzzle      │   │  Feasibility     │   │  Solver kernel   │
│  (grid + K   │──▶│  precheck        │──▶│  (Numba @njit)   │
│  waypoints)  │   │  O(N²)           │   │  population × T  │
└──────────────┘   └──────────────────┘   └────────┬─────────┘
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │  Fitness +       │
                                          │  CBOR trace      │
                                          └──────────────────┘
```

### Feasibility checks (cheap, decisive)
- Waypoint reachable & not blocked
- Free subgraph **connected** (BFS from $w_1$ covers all free cells)
- **Parity bound**: $|F_0 - F_1| \leq 1$ on chessboard colouring
- **Endpoint parity** consistent with $w_1, w_K$

Failing any of these proves no Hamiltonian path exists — we skip the kernel entirely.

---

## Step 1 — ACO-style construction

Each walker, at each cell, picks a 4-neighbour by **softmax over (pheromone + heuristic)**:

$$P(c \to c') \propto \exp\!\Big(\alpha \cdot \tau_{cc'} + \beta \cdot \log \eta_{c'}\Big)$$

with combined heuristic $\eta_{c'} = \mathrm{softplus}(h_m)^{\gamma_m} \cdot \mathrm{softplus}(h_w)^{\gamma_w} \cdot \mathrm{softplus}(h_a)^{\gamma_a} \cdot \mathrm{softplus}(h_p)^{\gamma_p}$.

| Heuristic | Role | Source |
|---|---|---|
| $h_m$ — Manhattan | Pull toward the next waypoint | $-d_M(c', w_{\text{seg}+1})$ |
| $h_w$ — Warnsdorff | Prefer low-degree cells; visit dead ends first | classical knight's-tour heuristic (1823) |
| $h_a$ — Articulation | Reject moves that **disconnect** the unvisited free subgraph | flood-fill check |
| $h_p$ — Parity | Maintain $\lvert F_0 - F_1\rvert \leq 1$ post-move | chessboard invariant |

<p class="citation">Combined multiplicatively after softplus to admit any-sign components; α = 1, β = 2 defaults match ACO conventions (Dorigo & Stützle, 2004).</p>

---

## Step 2 — SMA-style pheromone update

```python
# src/zipmould/solver/_kernel.py — _pheromone_update
progress = float(t) / float(T)
v_b = math.tanh(1.0 - progress)        # Li-inspired, BOUNDED (cf. arctanh)
v_c = 1.0 - progress                   # Li 2.4 verbatim

# Signed rank weights ∈ [-1, +1]:  best walker = +1, worst = −1, median ≈ 0
denom = float(n - 1)
weights[i] = (float(n) - 2.0 * float(r) + 1.0) / denom

# Per-edge update — the ZipMould analogue of Li Eq. (2.7)
new_val = v_c * tau[s, e] + v_b * deposit[s, e]

# Li z-branch escape — verbatim, on edges
if z > 0.0 and np.random.random() < z:
    new_val = np.random.normal(0.0, tau_max / 4.0)
```

<div class="ribbon">

The **signed** rank weight is our discrete analogue of Li's $W$: top-half walkers *deposit* pheromone, bottom-half walkers *evaporate* it on the same edges. Without sign, this collapses to vanilla ACO.

</div>

---

## What changed from Li, and why

| Li (2020) — continuous | ZipMould — discrete | Why the change |
|---|---|---|
| State $\vec{X} \in \mathbb{R}^d$ | Pheromone $\tau \in \mathbb{R}^{m}$ ($m$ = #edges) | No coordinate space; edges carry memory |
| $W_i = 1 \pm r \log(\cdot)$ | $W_i = (n - 2r + 1)/(n-1)$ | Linear rank — bounded, no $\log$ singularity |
| $v_b \in [-a, a]$, $a = \mathrm{arctanh}(1-t/T)$ — **unbounded** at $t=0$ | $v_b = \tanh(1 - t/T)$ — bounded in $[0, \tanh 1]$ | Discrete deposits diverge under unbounded $v_b$; saturation stabilises |
| Three-branch *switching* update (z / approach / oscillate) | **Single** sum $v_c\tau + v_b\Delta$ + z-branch noise | All three Li ingredients per step; no per-individual branch lottery |
| $X_A - X_B$ random direction | Replaced by **rank-weighted aggregate** $\sum_w W_w \cdot \mathbb{1}[\text{walker } w \text{ used edge } e]$ | "Difference of two random points" undefined on graph |

These are not improvements — they are **adaptations** that preserve Li's mechanism (positive/negative feedback + amplitude schedule + restart escape) under the constraints of a discrete edge-pheromone state.

---

## Ablation matrix

<div class="columns-wide-left">

<div>

### Two design knobs
- **Pheromone mode**:
  - `unified` — one $\tau$ per edge, shared across the full path
  - `stratified` — one $\tau$ per (edge, inter-waypoint segment) pair
- **Sign**:
  - `signed` — both attract & repel (full SMA analogue)
  - `positive` — only top half deposits (closer to ACO)

</div>

<div>

### 4 conditions × 4 baselines

| | unified | stratified |
|---|---|---|
| **signed**   | A | B |
| **positive** | C | D |

</div>

</div>

### Pre-registered hypotheses
1. **signed** > **positive** on hard puzzles (negative feedback breaks symmetry)
2. **stratified** > **unified** when $K$ is large (per-segment memory matters)
3. ZipMould (any) > vanilla ACO baseline on the held-out test split

<p class="citation">Tested via paired McNemar with FDR correction across 4 conditions × 4 baselines × seeds.</p>

---

## The Numba kernel — why this runs

```python
@nb.njit(cache=True)
def _walker_step(walker_id, pos, visited, ..., tau, alpha, beta_log, ...):
    for d in range(4):                                  # 4 neighbours
        nb_cell = adjacency[cur, d]
        if nb_cell < 0 or _bit_test(visited, walker_id, nb_cell): continue
        h_a = h_articulation(walker_id, nb_cell, visited, adjacency, ...)
        if h_a == NEG_INF: continue                     # disconnects subgraph
        logits[d] = alpha * tau_val + beta_log * math.log(eta)
    # softmax with log-sum-exp; roulette sample; set visited bit; update parity
```

- **Bitset `visited`** (uint64 words) → O(1) membership, cache-friendly.
- `@njit` JIT-compiles the hot loop to **C-speed**; pure-Python is ≈100× slower.
- Articulation flood-fill is the heaviest inner cost — `work_stack` shared across walkers.

---

## Baselines + statistical protocol

| Baseline | Pheromone | Deposit | Notes |
|---|---|---|---|
| **aco-vanilla**     | unsigned, unified | $\propto$ fitness | Classical $\rho$-evaporation, no restart noise |
| **heuristic-only**  | none              | —                  | Greedy on $\eta$ alone — measures heuristic strength |
| **random-walk**     | uniform           | none               | Pure exploration floor |
| **backtracking**    | n/a               | n/a                | Exhaustive DFS with parity + articulation pruning |

### Pre-registered protocol
- **Train / dev / test** splits, stratified by puzzle hardness (computed offline from BFS depth + $K/L$).
- **Held-out test set**: results computed *once*, after design freeze.
- **McNemar paired test** on solve / no-solve outcomes per puzzle.
- **Benjamini-Hochberg FDR correction** across the 4×4 condition matrix.
- All seeds reproducible via `derive_kernel_seed(global_seed, run_seed, puzzle_id, config_hash)`.

---

## Visualiser — how the trace becomes a movie

<div class="columns-wide-left">

<div>

```text
zipmould solver
    │
    ▼
CBOR trace (per-frame snapshot)
    • t, v_b, v_c
    • walker positions + segments
    • tau delta (sparse)
    • best fitness so far
    │
    ▼
FastAPI server (uv run zipmould viz serve)
    │  HTTP + cbor-x stream
    ▼
Vue 3 + Pinia + Tailwind 4
    • GridCanvas (SVG)
    • FitnessChart (Chart.js)
    • WalkerTable
    • Frame scrubber
```

</div>

<div>

### Why CBOR
- **Sparse** $\tau$-deltas only — frames stay small even on 200-iter runs.
- Schema-light, **streamable**, native binary in `cbor-x`.

### Why client-side replay
- Solver is heavy; we run it **once** to disk, then scrub instantly in the browser.
- Decouples experiment runs from presentation/inspection.

</div>

</div>

---

<!-- _class: lead -->

# Live demo

## *Switching to the visualiser…*

```bash
# Terminal 1 — solver/HTTP backend
uv run zipmould viz serve

# Terminal 2 — Vue dev server
cd viz-web && bun run dev
```

What we'll show: load a trace · play it back · toggle τ heatmap and walker layers · scrub to a specific iteration · compare *signed* vs *positive* conditions on the same puzzle.

---

## Takeaways + future work

<div class="columns">

<div>

### Takeaways
- Li's SMA is a **mechanism**, not a code path: $W$ + $v_b/v_c$ + $z$-branch each have a discrete analogue.
- Stigmergy (ACO) supplies the missing state space; SMA supplies the **dynamics on top of it**.
- Bounding the $v_b$ schedule is the **single largest deviation** — and forced by discreteness.
- Pre-registered ablation matrix lets us attribute any win to mechanism, not tuning.

</div>

<div>

### Future work
- **Warm-start** from the heuristic-only baseline path.
- **Learned heuristic** $\eta$ (small MLP on local cell features) — drop in beside Manhattan/Warnsdorff/etc.
- **Multi-objective**: shortest path under a tight wall budget.
- **Beyond Zip**: knight's tours, generalised Hamiltonian-path-with-pinned-vertices.

### Thanks
Questions, sceptical or otherwise, welcomed.

</div>

</div>

---

## References

- **Li, S., Chen, H., Wang, M., Heidari, A. A. & Mirjalili, S.** (2020). Slime mould algorithm: A new method for stochastic optimization. *Future Generation Computer Systems* 111, 300–323.
- **Dorigo, M. & Stützle, T.** (2004). *Ant Colony Optimization*. MIT Press.
- **Mirjalili, S. & Lewis, A.** (2016). The Whale Optimization Algorithm. *Advances in Engineering Software* 95, 51–67.
- **Tero, A. et al.** (2010). Rules for Biologically Inspired Adaptive Network Design. *Science* 327, 439–442.
- **Warnsdorff, H. C.** (1823). *Des Rösselsprungs einfachste und allgemeinste Lösung*.
- **McNemar, Q.** (1947). Note on the sampling error of the difference between correlated proportions or percentages. *Psychometrika* 12, 153–157.
