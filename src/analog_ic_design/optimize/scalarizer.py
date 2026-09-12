"""Trial objective scalarizer (R0-5 Commit 1, RFC-001 binding verdict 4).

Bayesian optimization needs a gradient, not a verdict: a 19 dB
near-miss must outscore a 2 dB disaster or TPE collapses into blind
search. Violating trials score `-1000 * (1 + sum of relative
constraint violations)` (continuous slope toward feasibility);
passing trials score a positive figure of merit (product of the
passing metric values — monotone, ordering is what TPE consumes).
No boolean ever reaches the optimizer. All values SI floats.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

#: Penalty floor: worse than any honest failure score (formula floor).
TIMEOUT_PENALTY: float = -1e18


def relative_violation(
    *, metric: str, operator: str, threshold: float, value: float
) -> float:
    """Relative violation of one rule, 0.0 when satisfied (sign-adjusted)."""
    scale = abs(threshold) if threshold != 0.0 else 1.0
    if operator == ">=":
        return max(0.0, (threshold - value) / scale)
    if operator == "<=":
        return max(0.0, (value - threshold) / scale)
    if operator == "=":
        return abs(value - threshold) / scale
    raise ValueError(f"Schema: unknown operator {operator!r} for metric {metric!r}")


def score_trial(
    metrics: Mapping[str, float],
    rules: Sequence[tuple[str, str, float]],
) -> float:
    """Scalar objective for one trial: penalty gradient or positive FOM.

    `rules` are (metric, operator, threshold) triples. Missing or
    non-finite metrics score TIMEOUT_PENALTY (fail closed: no silent
    drop, still finite for observe()).
    """
    total = 0.0
    worst = 0.0
    for metric, operator, threshold in rules:
        value = metrics.get(metric)
        if value is None or not math.isfinite(float(value)):
            return TIMEOUT_PENALTY
        viol = relative_violation(
            metric=metric, operator=operator, threshold=threshold,
            value=float(value),
        )
        total += viol
        worst = max(worst, viol)
    if worst > 0.0:
        return -1000.0 * (1.0 + total)
    fom = 1.0
    for metric, _, _ in rules:
        fom *= float(metrics[metric])
    return fom
