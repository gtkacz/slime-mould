"""Optuna search space for Stage-2 ZipMould tuning.

Per spec §2, defines 9 tunable knobs and the per-variant pinned
parameters. ``build_config`` consumes an Optuna ``Trial`` and returns
a fully-validated ``SolverConfig`` with the variant's structural
choices baked in.
"""

from __future__ import annotations

from typing import Final

import optuna  # pyright: ignore[reportMissingTypeStubs]

from zipmould.config import SolverConfig

PINNED_GLOBAL: Final[dict[str, object]] = {
    "iter_cap": 200,
    "wall_clock_s": 300.0,
    "tau_0": 0.0,
    "beta1": "N_squared",
    "beta2": 1.0,
    "beta3": "10_N_squared",
    "visible_walkers": 5,
    "frame_interval": 5,
    "tau_delta_epsilon": 1e-3,
}

VARIANT_PINS: Final[dict[str, dict[str, object]]] = {
    "zipmould-uni-signed": {"pheromone_mode": "unified", "tau_signed": True},
    "zipmould-uni-positive": {"pheromone_mode": "unified", "tau_signed": False},
    "zipmould-strat-signed": {"pheromone_mode": "stratified", "tau_signed": True},
    "zipmould-strat-positive": {"pheromone_mode": "stratified", "tau_signed": False},
}


def build_config(trial: optuna.Trial, variant: str) -> SolverConfig:
    """Materialize a SolverConfig for a single Optuna trial."""
    if variant not in VARIANT_PINS:
        msg = f"unknown variant {variant!r}; expected one of {sorted(VARIANT_PINS)}"
        raise ValueError(msg)

    sampled: dict[str, object] = {
        "gamma_man": trial.suggest_float("gamma_man", 0.1, 4.0, log=True),
        "gamma_warns": trial.suggest_float("gamma_warns", 0.1, 4.0, log=True),
        "gamma_art": trial.suggest_float("gamma_art", 0.1, 4.0, log=True),
        "gamma_par": trial.suggest_float("gamma_par", 0.0, 2.0, log=False),
        "alpha": trial.suggest_float("alpha", 0.1, 4.0, log=True),
        "beta": trial.suggest_float("beta", 0.1, 4.0, log=True),
        "z": trial.suggest_float("z", 0.0, 0.5, log=False),
        "tau_max": trial.suggest_float("tau_max", 1.0, 50.0, log=True),
        "population": trial.suggest_int("population", 10, 60),
    }

    body: dict[str, object] = {**PINNED_GLOBAL, **VARIANT_PINS[variant], **sampled}
    return SolverConfig.model_validate(body)
