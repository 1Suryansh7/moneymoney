"""Stage 3 Commit 3J tests: specification evaluation.

Pure-logic unit tests (SQLite-backed rules, no simulator): run on base
image with zero skips.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator

import pytest

from analog_ic_design.metrics.evaluator import (
    _hard_passes,
    _soft_score,
    evaluate_specification,
)
from analog_ic_design.store import connect, migrate, new_id

STAMP = "2026-09-05T00:00:00+00:00"


@pytest.fixture()
def spec_db() -> Generator[tuple[sqlite3.Connection, str], None, None]:
    conn = connect()
    migrate(conn)
    pid, lib, cell, spec = (new_id() for _ in range(4))
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "demo", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "l", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, "amp", STAMP))
    conn.execute("INSERT INTO specification VALUES (?, ?, ?, ?)", (spec, cell, "s1", STAMP))

    def add(
        kind: str,
        metric: str,
        op: str,
        thr: float,
        tol: float,
        prio: int,
        weight: float | None = None,
    ) -> str:
        rid = new_id()
        conn.execute(
            "INSERT INTO constraint_rule VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (rid, spec, kind, metric, op, thr, tol, prio, weight, STAMP),
        )
        return rid

    add("hard", "dc_gain", ">=", 8.0, 0.1, 1)
    add("hard", "power", "<=", 1e-3, 1e-6, 2)
    add("soft", "bandwidth", ">=", 10e6, 1e6, 3)
    add("weighted", "slew_rate", ">=", 1e9, 1e7, 4, 2.0)
    conn.commit()
    yield conn, spec
    conn.close()


def test_all_pass(spec_db: tuple[sqlite3.Connection, str]) -> None:
    conn, spec = spec_db
    report = evaluate_specification(
        conn, spec, {"dc_gain": 9.1, "power": 5e-7, "bandwidth": 20e6, "slew_rate": 8e9}
    )
    assert report.passed and report.violations == ()
    assert report.figure_of_merit == 2.0
    assert dict(report.soft_scores) != {}


def test_hard_failure_and_tolerance_edge(spec_db: tuple[sqlite3.Connection, str]) -> None:
    conn, spec = spec_db
    report = evaluate_specification(
        conn, spec, {"dc_gain": 7.5, "power": 5e-7, "bandwidth": 20e6, "slew_rate": 8e9}
    )
    assert not report.passed
    assert any(v.metric == "dc_gain" and "8.0" in v.message for v in report.violations)
    # Tolerance edge: 8.0 - 0.1 = 7.9 passes.
    edge = evaluate_specification(
        conn, spec, {"dc_gain": 7.9, "power": 5e-7, "bandwidth": 20e6, "slew_rate": 8e9}
    )
    assert edge.passed


def test_soft_scores_and_weighted_miss(spec_db: tuple[sqlite3.Connection, str]) -> None:
    conn, spec = spec_db
    report = evaluate_specification(
        conn, spec, {"dc_gain": 9.1, "power": 5e-7, "bandwidth": 5e6, "slew_rate": 1e6}
    )
    assert report.passed  # soft/weighted misses alone never fail the spec
    assert [s for _, s in report.soft_scores] == [pytest.approx(0.5)]
    assert report.figure_of_merit == 0.0
    assert any(v.metric == "slew_rate" for v in report.violations)


def test_missing_measurement_fails_closed(spec_db: tuple[sqlite3.Connection, str]) -> None:
    conn, spec = spec_db
    report = evaluate_specification(conn, spec, {"dc_gain": 9.1})
    assert not report.passed
    assert any("no finite measurement" in v.message for v in report.violations)


def test_unknown_specification_raises(spec_db: tuple[sqlite3.Connection, str]) -> None:
    conn, _spec = spec_db
    with pytest.raises(ValueError, match="unknown specification"):
        evaluate_specification(conn, "no-such-spec", {})


def test_helpers_cover_branches() -> None:
    assert _hard_passes(">=", 1.0, 1.0, 0.0)
    assert _hard_passes("<=", 1.0, 1.0, 0.0)
    assert _hard_passes("=", 1.0, 1.0 + 1e-9, 1e-6)
    assert not _hard_passes("=", 1.0, 2.0, 1e-6)
    with pytest.raises(ValueError, match="unknown operator"):
        _hard_passes(">>", 1.0, 1.0, 0.0)
    assert _soft_score(">=", 2.0, 1.0, 0.1) == 1.0
    assert _soft_score("<=", 0.5, 1.0, 0.1) == 1.0
    assert _soft_score("=", 1.0, 1.0, 0.1) == 1.0
    assert _soft_score("=", 5.0, 1.0, 0.1) == 0.0
