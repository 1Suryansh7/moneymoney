"""Stage 1 Commit 1F tests: the pre-simulation validation gate.

A valid generic circuit passes; every gate pillar breaks measurably with its
taxonomy category; violations persist as `error_record` rows; the
specification/constraint tables hold hard/soft/weighted contracts.
Failure taxonomy: Schema (gate) and Netlist (hookup).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator

import pytest

from analog_ic_design.circuit import (
    ValidationError,
    record_errors,
    validate,
)
from analog_ic_design.store import connect, migrate, new_id

STAMP = "2026-09-05T00:00:00+00:00"


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    pid, lib, cell, tech = (new_id() for _ in range(4))
    symcell, sym = new_id(), new_id()
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "demo", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "l", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, "amp1", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (symcell, lib, "testdev", STAMP))
    conn.execute(
        "INSERT INTO technology VALUES (?, ?, ?, ?, ?)", (tech, pid, "TEST_PDK", "0", STAMP)
    )
    conn.execute(
        "INSERT INTO model_binding VALUES (?, ?, ?, ?, ?, ?)",
        (new_id(), tech, "TEST_NMOS4", "TEST_MODEL", "d g s b", STAMP),
    )
    conn.execute("INSERT INTO symbol VALUES (?, ?, ?, ?)", (sym, symcell, "TEST_NMOS4", STAMP))
    m1 = new_id()
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (m1, cell, sym, "m1", STAMP))
    nets: dict[str, str] = {}
    for name in ("in", "out", "vss"):
        nid = new_id()
        nets[name] = nid
        conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))
    for term, net in (("d", "out"), ("g", "in"), ("s", "vss"), ("b", "vss")):
        conn.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
            (new_id(), m1, nets[net], term, STAMP),
        )
    conn.execute(
        "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), m1, "W", 2e-06, STAMP)
    )
    conn.commit()
    yield conn
    conn.close()


def _cell(db: sqlite3.Connection) -> str:
    row = db.execute("SELECT id FROM cell WHERE name = 'amp1'").fetchone()
    assert row is not None
    return str(row[0])


def test_valid_circuit_passes_with_degree_one_nets(db: sqlite3.Connection) -> None:
    report = validate(db, _cell(db))
    assert report.valid and report.violations == ()


def test_unconnected_terminal_is_netlist_violation(db: sqlite3.Connection) -> None:
    db.execute("UPDATE port SET net_id = NULL WHERE name = 'b'")
    db.commit()
    report = validate(db, _cell(db))
    assert not report.valid
    assert any(v.category == "netlist" for v in report.violations)


def test_floating_net_is_netlist_violation(db: sqlite3.Connection) -> None:
    cell = _cell(db)
    db.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (new_id(), cell, "ghost", STAMP))
    db.commit()
    report = validate(db, cell)
    assert not report.valid
    assert any("floating" in v.message for v in report.violations)


def test_text_parameter_is_schema_violation(db: sqlite3.Connection) -> None:
    # NOTE: SQLite REAL affinity erases bool (True round-trips as 1), so bool
    # rejection lives at the 1A construction boundary (proven there), not here.
    m1 = db.execute("SELECT id FROM instance WHERE name = 'm1'").fetchone()[0]
    db.execute("INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), m1, "X", "2u", STAMP))
    db.commit()
    report = validate(db, _cell(db))
    assert not report.valid
    assert sum(1 for v in report.violations if v.category == "schema") == 1


def test_missing_binding_and_technology_are_schema_violations(
    db: sqlite3.Connection,
) -> None:
    db.execute("DELETE FROM model_binding")
    db.commit()
    report = validate(db, _cell(db))
    assert not report.valid
    assert any("binding" in v.message for v in report.violations)
    db.execute("DELETE FROM technology")
    db.commit()
    report = validate(db, _cell(db))
    assert any("technology" in v.message for v in report.violations)


def test_duplicate_instance_name_is_schema_violation(db: sqlite3.Connection) -> None:
    cell = _cell(db)
    sym = db.execute("SELECT symbol_id FROM instance WHERE name = 'm1'").fetchone()[0]
    dup = new_id()
    db.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (dup, cell, sym, "m1", STAMP))
    for term, net in (("d", "out"), ("g", "in"), ("s", "vss"), ("b", "vss")):
        nid = db.execute("SELECT id FROM net WHERE name = ?", (net,)).fetchone()[0]
        db.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)", (new_id(), dup, nid, term, STAMP)
        )
    db.commit()
    report = validate(db, cell)
    assert not report.valid
    assert [v for v in report.violations if v.category == "schema"] != []


def test_unknown_cell_raises_not_reports(db: sqlite3.Connection) -> None:
    with pytest.raises(ValidationError):
        validate(db, "no-such-cell")


def test_record_errors_persists_rows(db: sqlite3.Connection) -> None:
    cell = _cell(db)
    assert record_errors(db, cell, validate(db, cell)) == ()
    db.execute("UPDATE port SET net_id = NULL WHERE name = 'b'")
    db.commit()
    report = validate(db, cell)
    ids = record_errors(db, cell, report)
    assert len(ids) == len(report.violations) == 1
    row = db.execute(
        "SELECT category, cell_id FROM error_record WHERE id = ?", (ids[0],)
    ).fetchone()
    assert (row[0], row[1]) == ("netlist", cell)


def test_error_record_rejects_unknown_category(db: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO error_record VALUES (?, ?, ?, ?, ?)",
            (new_id(), None, "vibes", "x", STAMP),
        )


def test_specification_models_three_objective_kinds(db: sqlite3.Connection) -> None:
    cell = _cell(db)
    spec = new_id()
    db.execute("INSERT INTO specification VALUES (?, ?, ?, ?)", (spec, cell, "s1", STAMP))
    rows = [
        ("hard", "gain", ">=", 60.0, 1.0, 1, None),
        ("soft", "bandwidth", ">=", 40e6, 1e6, 2, None),
        ("weighted", "fom", ">=", 1.0, 0.1, 3, 2.5),
    ]
    for kind, metric, op, thr, tol, prio, w in rows:
        db.execute(
            "INSERT INTO constraint_rule VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id(), spec, kind, metric, op, thr, tol, prio, w, STAMP),
        )
    db.commit()
    got = db.execute(
        "SELECT kind, tolerance, priority FROM constraint_rule ORDER BY priority"
    ).fetchall()
    assert [(r[0], r[1], r[2]) for r in got] == [
        ("hard", 1.0, 1),
        ("soft", 1e6, 2),
        ("weighted", 0.1, 3),
    ]
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO constraint_rule VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id(), spec, "vibes", "gain", ">=", 1.0, 0.1, 1, None, STAMP),
        )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO constraint_rule VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id(), spec, "hard", "gain", ">>", 1.0, 0.1, 1, None, STAMP),
        )


def test_validation_error_is_value_error() -> None:
    assert issubclass(ValidationError, ValueError)
