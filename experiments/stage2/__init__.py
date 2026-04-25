"""Stage-2 hyperparameter tuning for ZipMould variants.

Per docs/superpowers/specs/2026-04-25-zipmould-stage2-stage4-design.md:
runs Optuna TPE searches on the train split for all four variants,
followed by a dev-set non-regression gate.
"""
