"""Optuna-backed optimizer: seeded TPE ask/tell (Stage 4 Commit 4C).

Maps the abstract ask/tell protocol onto `optuna.study.Study.ask` with
per-parameter float distributions and `Study.tell`. Ask/tell pairing is
strict and FIFO: `observe()` completes the oldest open suggestion and
rejects mismatched parameters instead of silently misattributing them.
Determinism: same seed + same observation sequence gives the same
suggestion sequence (TPESampler is seeded; startup trials are seeded
random draws, stated plainly, not intelligence).
"""

from __future__ import annotations

import math
from collections import deque

import optuna
from optuna.trial import Trial

from analog_ic_design.optimize.optimizer import Optimizer, SearchSpace


class OptunaOptimizer(Optimizer):
    """`Optimizer` over Optuna TPE (single scalar objective)."""

    def __init__(
        self,
        space: SearchSpace,
        *,
        seed: int,
        study_name: str = "study",
        direction: str = "maximize",
    ) -> None:
        super().__init__(space, seed=seed)
        if direction == "maximize":
            study_direction = optuna.study.StudyDirection.MAXIMIZE
        elif direction == "minimize":
            study_direction = optuna.study.StudyDirection.MINIMIZE
        else:
            raise ValueError(
                f"Schema: direction must be maximize/minimize, got {direction!r}"
            )
        self._study = optuna.create_study(
            study_name=study_name,
            direction=study_direction,
            sampler=optuna.samplers.TPESampler(seed=seed),
        )
        self._open: deque[tuple[Trial, dict[str, float]]] = deque()

    @property
    def study_name(self) -> str:
        """Optuna study name (ledger `study` should match)."""
        return str(self._study.study_name)

    def suggest(self) -> dict[str, float]:
        """Ask Optuna for the next SI parameter vector."""
        trial = self._study.ask(
            {
                name: optuna.distributions.FloatDistribution(float(low), float(high))
                for name, (low, high) in self.space.bounds.items()
            }
        )
        params = {
            name: float(trial.suggest_float(name, float(low), float(high)))
            for name, (low, high) in self.space.bounds.items()
        }
        self._open.append((trial, params))
        return params

    def observe(self, params: dict[str, float], value: float) -> None:
        """Tell Optuna the scalar objective value of the oldest suggestion."""
        if not self._open:
            raise ValueError("Schema: observe() with no open suggestion")
        trial, expected = self._open[0]
        if expected != {k: float(v) for k, v in params.items()}:
            raise ValueError(
                "Schema: observe() parameters do not match the open suggestion"
            )
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Schema: objective value is not numeric ({value!r})")
        if not math.isfinite(float(value)):
            raise ValueError(f"Schema: objective value is not finite ({value!r})")
        self._open.popleft()
        self._study.tell(trial, float(value))
