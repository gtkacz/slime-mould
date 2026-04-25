# ZipMould
ZipMould is a [Li](https://www.sciencedirect.com/science/article/abs/pii/S0167739X19320941)-inspired slime mould solver for Zip puzzles.

## 1. Problem Statement

A *Zip* puzzle consists of:

- An $N \times N$ grid of cells.
- A subset $\mathcal{W} \subseteq \{1, 2, \dots, N^2\}$ of cells pre-labelled with strictly-increasing positive integers $1, 2, \dots, K$ (the **waypoints**). Let $K = |\mathcal{W}|$.
- An optional set of **wall constraints**: for any cell, zero or more of its four edges may be marked impassable.

A valid solution is a sequence of cells $\pi_1, \pi_2, \dots, \pi_{N^2}$ satisfying:

1. $\pi_1$ is the cell labelled $1$ and $\pi_{N^2}$ is the cell labelled $K$.
2. Consecutive cells $\pi_t, \pi_{t+1}$ are 4-adjacent and the edge between them is not walled.
3. Every cell of the grid appears exactly once (Hamiltonian path).
4. Waypoints are visited in ascending order: if $\pi_a$ has label $k$ and $\pi_b$ has label $k+1$, then $a < b$.
5. The path neither branches nor crosses itself (implied by Hamiltonian).
