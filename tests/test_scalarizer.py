"""Scalarizer unit tests (R0-5 Commit 1, RFC-001 verdict 4).

Pure math, no simulator: the gradient ordering is the load-bearing
claim (19 dB near-miss outscores 2 dB disaster), plus operator
directions, the zero-threshold guard, fail-closed missing/NaN, and
the positive FOM product.
"""

from __future__ import annotations

import math

import pytest

from analog_ic_design.optimize.scalarizer import (
    TIMEOUT_PENALTY,
    relative_violation,
    score_trial,
)

RULES = [("dc_gain", ">=", 20.0), ("bandwidth", ">=", 10.0e6)]


def test_satisfied_rules_score_positive_fom() -> None:
    score = score_trial({"dc_gain": 25.0, "bandwidth": 20.0e6}, RULES)
    assert score == 25.0 * 20.0e6
    assert score > 0.0


def test_gradient_points_at_feasibility() -> None:
    near = score_trial({"dc_gain": 19.0, "bandwidth": 20.0e6}, RULES)
    far = score_trial({"dc_gain": 2.0, "bandwidth": 20.0e6}, RULES)
    assert far < near < 0.0


def test_operator_directions() -> None:
    assert relative_violation(metric="g", operator=">=", threshold=20.0, value=25.0) == 0.0
    assert relative_violation(metric="g", operator=">=", threshold=20.0, value=10.0) == 0.5
    assert relative_violation(metric="p", operator="<=", threshold=5.0, value=3.0) == 0.0
    assert relative_violation(metric="p", operator="<=", threshold=5.0, value=10.0) == 1.0
    assert relative_violation(metric="x", operator="=", threshold=4.0, value=4.0) == 0.0
    assert relative_violation(metric="x", operator="=", threshold=4.0, value=5.0) == 0.25
    with pytest.raises(ValueError, match="unknown operator"):
        relative_violation(metric="x", operator="!=", threshold=1.0, value=1.0)


def test_zero_threshold_guards_division() -> None:
    assert relative_violation(metric="x", operator="=", threshold=0.0, value=0.0) == 0.0
    assert relative_violation(metric="x", operator="=", threshold=0.0, value=2.0) == 2.0


def test_missing_or_nan_metrics_fail_closed() -> None:
    assert score_trial({"dc_gain": 25.0}, RULES) == TIMEOUT_PENALTY
    assert score_trial({"dc_gain": 25.0, "bandwidth": math.nan}, RULES) == TIMEOUT_PENALTY


def test_penalty_formula_exact() -> None:
    # gain short by half, bandwidth satisfied: -(1000 * (1 + 0.5)).
    assert score_trial({"dc_gain": 10.0, "bandwidth": 10.0e6}, RULES) == -1500.0
