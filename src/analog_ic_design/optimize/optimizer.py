"""Optimizer interface, search space, and trial result (Stage 4 Commit 4B).

`Optimizer` speaks ask/tell: `suggest()` proposes the next SI parameter
vector inside the `SearchSpace`; `observe()` reports its scalar objective
value. Determinism contract: same seed + same observation sequence gives
the same suggestion sequence (proven by tests, no simulator needed).
`TrialResult` is the ledger-bound outcome of one evaluated suggestion.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SearchSpace:
    """SI parameter bounds: name -> (low, high), finite with low < high."""

    bounds: Mapping[str, tuple[float, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.bounds:
            raise ValueError("Schema: search space defines no parameters")
        for name, (low, high) in self.bounds.items():
            if not name:
                raise ValueError("Schema: search space has an empty parameter name")
            for edge in (low, high):
                if isinstance(edge, bool) or not isinstance(edge, (int, float)):
                    raise ValueError(
                        f"Schema: bound of {name!r} is not a numeric SI value"
                    )
                if not math.isfinite(float(edge)):
                    raise ValueError(f"Schema: bound of {name!r} is not finite")
            if not float(low) < float(high):
                raise ValueError(
                    f"Schema: bound of {name!r} is empty ({low!r} >= {high!r})"
                )

    def in_bounds(self, params: Mapping[str, float]) -> bool:
        """True iff every space parameter lies within its bounds."""
        for name, (low, high) in self.bounds.items():
            value = params.get(name)
            if (
                value is None
                or isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                return False
            if not float(low) <= float(value) <= float(high):
                return False
        return True


@dataclass(frozen=True)
class TrialResult:
    """One evaluated suggestion, ready for the ledger (all SI floats)."""

    study: str
    trial: int
    kind: str
    status: str
    corner: str
    parameters: dict[str, float]
    metrics: dict[str, float]
    verdict: str
    reproducibility_id: str
    seed: int
    job_id: str | None


class Optimizer(ABC):
    """Abstract ask/tell optimizer over a fixed `SearchSpace`."""

    def __init__(self, space: SearchSpace, *, seed: int) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError(f"Schema: optimizer seed must be an int, got {seed!r}")
        self._space = space
        self._seed = seed

    @property
    def space(self) -> SearchSpace:
        """The searched space (fixed for the study)."""
        return self._space

    @property
    def seed(self) -> int:
        """Study seed (recorded per trial for reproducibility)."""
        return self._seed

    @abstractmethod
    def suggest(self) -> dict[str, float]:
        """Propose the next SI parameter vector inside the space."""
        raise NotImplementedError

    @abstractmethod
    def observe(self, params: dict[str, float], value: float) -> None:
        """Report the scalar objective value of an evaluated suggestion."""
        raise NotImplementedError
