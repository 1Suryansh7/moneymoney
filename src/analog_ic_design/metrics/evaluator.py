"""Specification evaluation: hard/soft/weighted objectives (Stage 3 Commit 3J).

Evaluates `constraint_rule` rows of one specification against measured
metric values (SI floats). Semantics per rule kind:

- hard: must pass within tolerance (`>=`: value >= threshold - tolerance;
  `<=`: value <= threshold + tolerance; `=`: |value - threshold| <=
  tolerance). Any hard failure fails the specification.
- soft: better-is-better normalized score in [0,1] (ratio-based, monotone,
  dimensionless): `>=` goals score min(1, value/threshold);
  `<=` goals score min(1, threshold/value) (guarding divide-by-zero);
  `=` goals score 1 within tolerance else 0. Never fails the spec alone.
- weighted: contributes `weight` (default 1.0 when NULL) to the combined
  figure-of-merit when its hard-style check passes, else 0.0.

Missing measurements fail closed as hard violations. All comparisons are
same-metric SI values; no unit conversion happens here.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class ConstraintViolation:
    """One unmet rule: what was required vs what was measured."""

    rule_id: str
    metric: str
    operator: str
    threshold: float
    value: float | None
    message: str


@dataclass(frozen=True)
class SpecReport:
    """Evaluation verdict for one specification."""

    specification_id: str
    passed: bool
    violations: tuple[ConstraintViolation, ...] = ()
    soft_scores: tuple[tuple[str, float], ...] = ()
    figure_of_merit: float = 0.0


@dataclass
class _Rule:
    id: str
    kind: str
    metric: str
    operator: str
    threshold: float
    tolerance: float
    weight: float | None


def _load_rules(conn: sqlite3.Connection, specification_id: str) -> list[_Rule]:
    rows = conn.execute(
        "SELECT id, kind, metric, operator, threshold, tolerance, weight"
        " FROM constraint_rule WHERE specification_id = ? ORDER BY priority, id",
        (specification_id,),
    ).fetchall()
    rules = [
        _Rule(
            id=str(r[0]),
            kind=str(r[1]),
            metric=str(r[2]),
            operator=str(r[3]),
            threshold=float(r[4]),
            tolerance=float(r[5]),
            weight=None if r[6] is None else float(r[6]),
        )
        for r in rows
    ]
    if not rows:
        raise ValueError(f"unknown specification {specification_id!r}")
    return rules


def _hard_passes(operator: str, value: float, threshold: float, tolerance: float) -> bool:
    if operator == ">=":
        return value >= threshold - tolerance
    if operator == "<=":
        return value <= threshold + tolerance
    if operator == "=":
        return abs(value - threshold) <= tolerance
    raise ValueError(f"unknown operator {operator!r}")


def _soft_score(operator: str, value: float, threshold: float, tolerance: float) -> float:
    if operator == ">=":
        if threshold == 0.0:
            return 1.0 if value >= 0.0 else 0.0
        return max(0.0, min(1.0, value / threshold))
    if operator == "<=":
        if value <= 0.0:
            return 1.0
        if threshold <= 0.0:
            return 0.0
        return max(0.0, min(1.0, threshold / value))
    return 1.0 if abs(value - threshold) <= tolerance else 0.0


def evaluate_specification(
    conn: sqlite3.Connection,
    specification_id: str,
    measurements: dict[str, float],
) -> SpecReport:
    """Evaluate every rule of `specification_id` against `measurements`."""
    rules = _load_rules(conn, specification_id)
    violations: list[ConstraintViolation] = []
    soft: list[tuple[str, float]] = []
    fom = 0.0
    hard_ok = True
    for rule in rules:
        value = measurements.get(rule.metric)
        if value is None or not math.isfinite(value):
            violations.append(
                ConstraintViolation(
                    rule_id=rule.id,
                    metric=rule.metric,
                    operator=rule.operator,
                    threshold=rule.threshold,
                    value=value,
                    message=f"metric {rule.metric!r} has no finite measurement",
                )
            )
            hard_ok = False
            continue
        if rule.kind == "hard":
            if not _hard_passes(rule.operator, value, rule.threshold, rule.tolerance):
                hard_ok = False
                violations.append(
                    ConstraintViolation(
                        rule_id=rule.id,
                        metric=rule.metric,
                        operator=rule.operator,
                        threshold=rule.threshold,
                        value=value,
                        message=(
                            f"hard constraint violated: {rule.metric}={value!r} "
                            f"not {rule.operator} {rule.threshold!r} "
                            f"(tol {rule.tolerance!r})"
                        ),
                    )
                )
        elif rule.kind == "soft":
            score = _soft_score(rule.operator, value, rule.threshold, rule.tolerance)
            soft.append((rule.id, score))
        elif rule.kind == "weighted":
            if _hard_passes(rule.operator, value, rule.threshold, rule.tolerance):
                fom += rule.weight if rule.weight is not None else 1.0
            else:
                violations.append(
                    ConstraintViolation(
                        rule_id=rule.id,
                        metric=rule.metric,
                        operator=rule.operator,
                        threshold=rule.threshold,
                        value=value,
                        message=(
                            f"weighted objective missed: {rule.metric}={value!r} "
                            f"not {rule.operator} {rule.threshold!r} "
                            f"(tol {rule.tolerance!r}); contributes 0"
                        ),
                    )
                )
        else:
            raise ValueError(f"unknown rule kind {rule.kind!r}")
    return SpecReport(
        specification_id=specification_id,
        passed=hard_ok,
        violations=tuple(violations),
        soft_scores=tuple(soft),
        figure_of_merit=float(fom),
    )
