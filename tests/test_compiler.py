"""Stage 1 Commit 1E tests: deterministic netlist compiler.

Byte-identical expectation on a generic (non-PDK) fixture, determinism
across row order, and fail-closed `CompilerError` for every missing piece.
Failure taxonomy: Netlist.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator

import pytest

from analog_ic_design.circuit import CompilerError, compile_netlist
from analog_ic_design.store import connect, migrate, new_id

STAMP = "2026-09-05T00:00:00+00:00"
EXPECTED = "* cell amp1\nMm1 out in vss vss TEST_NMOS_MODEL L=5e-07 W=2e-06\n.end\n"


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    pid, lib, cell, tech, bind = (new_id() for _ in range(5))
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
        (bind, tech, "TEST_NMOS4", "TEST_NMOS_MODEL", "d g s b", STAMP),
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
    conn.execute("INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), m1, "W", 2e-06, STAMP))
    conn.execute("INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), m1, "L", 5e-07, STAMP))
    conn.commit()
    yield conn
    conn.close()


def test_expected_netlist_byte_identical(db: sqlite3.Connection) -> None:
    cell = db.execute("SELECT id FROM cell WHERE name = 'amp1'").fetchone()[0]
    assert compile_netlist(db, cell) == EXPECTED


def test_compile_is_deterministic(db: sqlite3.Connection) -> None:
    cell = db.execute("SELECT id FROM cell WHERE name = 'amp1'").fetchone()[0]
    assert compile_netlist(db, cell) == compile_netlist(db, cell)


def test_unknown_cell_raises(db: sqlite3.Connection) -> None:
    with pytest.raises(CompilerError):
        compile_netlist(db, "no-such-cell")


def test_missing_technology_raises(db: sqlite3.Connection) -> None:
    db.execute("DELETE FROM technology")
    db.commit()
    cell = db.execute("SELECT id FROM cell WHERE name = 'amp1'").fetchone()[0]
    with pytest.raises(CompilerError):
        compile_netlist(db, cell)


def test_missing_binding_raises(db: sqlite3.Connection) -> None:
    db.execute("DELETE FROM model_binding")
    db.commit()
    cell = db.execute("SELECT id FROM cell WHERE name = 'amp1'").fetchone()[0]
    with pytest.raises(CompilerError):
        compile_netlist(db, cell)


def test_unconnected_terminal_raises(db: sqlite3.Connection) -> None:
    db.execute("UPDATE port SET net_id = NULL WHERE name = 'b'")
    db.commit()
    cell = db.execute("SELECT id FROM cell WHERE name = 'amp1'").fetchone()[0]
    with pytest.raises(CompilerError):
        compile_netlist(db, cell)


def test_missing_port_row_raises(db: sqlite3.Connection) -> None:
    db.execute("DELETE FROM port WHERE name = 'b'")
    db.commit()
    cell = db.execute("SELECT id FROM cell WHERE name = 'amp1'").fetchone()[0]
    with pytest.raises(CompilerError):
        compile_netlist(db, cell)


def test_extra_terminal_outside_pin_order_raises(db: sqlite3.Connection) -> None:
    m1 = db.execute("SELECT id FROM instance WHERE name = 'm1'").fetchone()[0]
    vss = db.execute("SELECT id FROM net WHERE name = 'vss'").fetchone()[0]
    db.execute(
        "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)", (new_id(), m1, vss, "extra", STAMP)
    )
    db.commit()
    cell = db.execute("SELECT id FROM cell WHERE name = 'amp1'").fetchone()[0]
    with pytest.raises(CompilerError):
        compile_netlist(db, cell)


def test_text_parameter_rejected(db: sqlite3.Connection) -> None:
    m1 = db.execute("SELECT id FROM instance WHERE name = 'm1'").fetchone()[0]
    db.execute("INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), m1, "W", "2u", STAMP))
    db.commit()
    cell = db.execute("SELECT id FROM cell WHERE name = 'amp1'").fetchone()[0]
    with pytest.raises(CompilerError):
        compile_netlist(db, cell)


def test_compiler_error_is_value_error() -> None:
    assert issubclass(CompilerError, ValueError)
