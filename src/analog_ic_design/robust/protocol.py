"""Statistical protocol, Wilson interval, robustness report (Stage 4.5 Commit 4.5C).

A `StatisticalProtocol` declares EVERYTHING a yield number depends on:
sample count, seeds, corners, supplies, temperatures, variation mechanisms,
sampling method, metric thresholds, confidence level. `build_report`
returns counts, a yield point estimate, and a Wilson score interval —
never a headline sentence. Headlines go through the §8 blocking checkpoint,
uttered by a human, never asserted by code.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class StatisticalProtocol:
    """Versioned declaration of a robustness experiment's full conditions."""

    name: str
    sample_count: int
    seed: int
    corners: tuple[str, ...] = ()
    supplies: tuple[float, ...] = ()
    temperatures: tuple[float, ...] = ()
    variation_mechanisms: tuple[str, ...] = ()
    sampling_method: str = ""
    metric_thresholds: Mapping[str, tuple[str, float, float]] = field(default_factory=dict)
    confidence_level: float = 0.95

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Schema: protocol needs a non-empty name")
        if isinstance(self.sample_count, bool) or not isinstance(self.sample_count, int):
            raise ValueError("Schema: sample_count must be an int")
        if self.sample_count <= 0:
            raise ValueError("Schema: sample_count must be positive")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("Schema: protocol seed must be an int")
        if not self.corners:
            raise ValueError("Schema: protocol declares no corners")
        if not self.variation_mechanisms:
            raise ValueError("Schema: protocol declares no variation mechanisms")
        if not self.sampling_method:
            raise ValueError("Schema: protocol declares no sampling method")
        if not self.metric_thresholds:
            raise ValueError("Schema: protocol declares no metric thresholds")
        for metric, (operator, threshold, tolerance) in self.metric_thresholds.items():
            if operator not in (">=", "<=", "="):
                raise ValueError(f"Schema: bad operator {operator!r} for {metric!r}")
            for label, bound in (("threshold", threshold), ("tolerance", tolerance)):
                if (
                    isinstance(bound, bool)
                    or not isinstance(bound, (int, float))
                    or not math.isfinite(float(bound))
                ):
                    raise ValueError(f"Schema: {label} for {metric!r} is not finite")
            if float(tolerance) < 0.0:
                raise ValueError(f"Schema: tolerance for {metric!r} is negative")
        for label, values in (("supplies", self.supplies), ("temperatures", self.temperatures)):
            for value in values:
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    or float(value) <= 0.0
                ):
                    raise ValueError(f"Schema: {label} must hold positive SI numbers")
        if (
            isinstance(self.confidence_level, bool)
            or not isinstance(self.confidence_level, (int, float))
            or not 0.0 < float(self.confidence_level) < 1.0
        ):
            raise ValueError("Schema: confidence_level must lie in (0, 1)")


def wilson_interval(passes: int, total: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (pure math, no SciPy).

    Returns (lower, upper) clamped to [0, 1]. `passes` out of `total`
    Bernoulli trials at the given confidence level.
    """
    for label, value in (("passes", passes), ("total", total)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Schema: {label} must be an int")
    if total <= 0:
        raise ValueError("Schema: wilson interval needs total > 0")
    if not 0 <= passes <= total:
        raise ValueError("Schema: passes must satisfy 0 <= passes <= total")
    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not 0.0 < float(confidence) < 1.0
    ):
        raise ValueError("Schema: confidence must lie in (0, 1)")
    z = statistics.NormalDist().inv_cdf((1.0 + float(confidence)) / 2.0)
    denom = 1.0 + z * z / total
    center = (passes / total + z * z / (2.0 * total)) / denom
    variance = passes / total * (1.0 - passes / total) / total
    half = z * math.sqrt(variance + z * z / (4.0 * total * total)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


@dataclass(frozen=True)
class RobustnessReport:
    """Counts + yield + interval for one metric under one protocol."""

    protocol_name: str
    metric_id: str
    operator: str
    threshold: float
    passes: int
    total: int
    yield_estimate: float
    ci_lower: float
    ci_upper: float
    trial_ids: tuple[str, ...] = ()


def build_report(
    protocol: StatisticalProtocol,
    metric_id: str,
    results: Sequence[tuple[str, float]],
) -> RobustnessReport:
    """Evaluate `results` (trial id, measured value) against the protocol's
    threshold for `metric_id`. Counts only — never a headline sentence."""
    if metric_id not in protocol.metric_thresholds:
        raise ValueError(f"Schema: protocol has no threshold for {metric_id!r}")
    operator, threshold, tolerance = protocol.metric_thresholds[metric_id]
    passed = 0
    for trial_id, value in results:
        if not isinstance(trial_id, str) or not trial_id:
            raise ValueError("Schema: trial results need non-empty string ids")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Schema: trial {trial_id!r} value is not numeric")
        if not math.isfinite(float(value)):
            raise ValueError(f"Schema: trial {trial_id!r} value is not finite")
        delta = float(value) - float(threshold)
        if operator == ">=":
            ok = delta >= -float(tolerance)
        elif operator == "<=":
            ok = delta <= float(tolerance)
        else:
            ok = abs(delta) <= float(tolerance)
        if ok:
            passed += 1
    total = len(results)
    if total == 0:
        raise ValueError("Schema: cannot build a report from zero trials")
    ci_lower, ci_upper = wilson_interval(passed, total, protocol.confidence_level)
    return RobustnessReport(
        protocol_name=protocol.name,
        metric_id=metric_id,
        operator=operator,
        threshold=float(threshold),
        passes=passed,
        total=total,
        yield_estimate=passed / total,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        trial_ids=tuple(trial_id for trial_id, _ in results),
    )
