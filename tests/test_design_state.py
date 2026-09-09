"""Stage 7A tests: migration v9 checkpoint_registry + design_state.

Schema-only commit: tables, CHECK vocabularies, FK/cascade behavior, and
the v8 upgrade path. Writer helpers arrive with their calling features
(UI MVP checkpoint emission, workflow state transitions).
Failure taxonomy: Schema.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator

import pytest

from analog_ic_design.store import (
    MIGRATIONS,
    SCHEMA_VERSION,
    connect,
    get_schema_version,
    migrate,
    new_id,
)

STAMP = "2026-09-05T00:00:00+00:00"


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    yield conn
    conn.close()


def _cell(conn: sqlite3.Connection) -> str:
    pid, lib, cell = new_id(), new_id(), new_id()
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "demo", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "lib", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, "c", STAMP))
    conn.commit()
    return cell


def test_v9_tables_present(db: sqlite3.Connection) -> None:
    assert SCHEMA_VERSION == 9
    tables = {
        row[0]
        for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    assert {"checkpoint_registry", "design_state"} <= tables


def test_checkpoint_lifecycle_and_vocabularies(db: sqlite3.Connection) -> None:
    cid = new_id()
    db.execute(
        "INSERT INTO checkpoint_registry "
        "(id, checkpoint_key, trigger, required_evidence, verification_action,"
        " severity, reviewer, decision, decided_at, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (cid, "stage6-proposal", "AI sizing proposed", "EXP-1", "accept/reject",
         "blocking", None, "pending", None, STAMP),
    )
    db.commit()
    db.execute(
        "UPDATE checkpoint_registry SET reviewer = ?, decision = ?, decided_at = ?"
        " WHERE id = ?",
        ("human", "confirmed", STAMP, cid),
    )
    row = db.execute(
        "SELECT severity, reviewer, decision FROM checkpoint_registry WHERE id = ?",
        (cid,),
    ).fetchone()
    assert (str(row[0]), str(row[1]), str(row[2])) == ("blocking", "human", "confirmed")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO checkpoint_registry "
            "(id, checkpoint_key, trigger, required_evidence, verification_action,"
            " severity, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id(), "k", "t", "e", "v", "maybe", STAMP),
        )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO checkpoint_registry "
            "(id, checkpoint_key, trigger, required_evidence, verification_action,"
            " severity, decision, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id(), "k", "t", "e", "v", "blocking", "rubber-stamp", STAMP),
        )


def test_design_state_transitions_and_cascade(db: sqlite3.Connection) -> None:
    cell = _cell(db)
    sid = new_id()
    db.execute(
        "INSERT INTO design_state (id, cell_id, state, design_revision,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (sid, cell, "DRAFT", None, STAMP, STAMP),
    )
    db.commit()
    db.execute(
        "UPDATE design_state SET state = ?, updated_at = ? WHERE id = ?",
        ("SIMULATION_READY", STAMP, sid),
    )
    row = db.execute("SELECT state FROM design_state WHERE id = ?", (sid,)).fetchone()
    assert str(row[0]) == "SIMULATION_READY"
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO design_state (id, cell_id, state, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (new_id(), cell, "NOMINAL", STAMP, STAMP),
        )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO design_state (id, cell_id, state, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (new_id(), cell, "TAPED_OUT", STAMP, STAMP),
        )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO design_state (id, cell_id, state, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (new_id(), "no-such-cell", "DRAFT", STAMP, STAMP),
        )
    db.execute("DELETE FROM cell WHERE id = ?", (cell,))
    assert (
        db.execute("SELECT COUNT(*) FROM design_state WHERE id = ?", (sid,)).fetchone()[0]
        == 0
    )


def test_upgrade_v8_to_v9_preserves_data() -> None:
    conn = connect()
    try:
        for version, sql in MIGRATIONS:
            if version > 8:
                break
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (version, STAMP),
            )
        conn.execute("INSERT INTO project VALUES (?, ?, ?)", ("p1", "demo", STAMP))
        conn.commit()
        assert get_schema_version(conn) == 8
        assert migrate(conn) == 9
        assert get_schema_version(conn) == 9
        row = conn.execute("SELECT name FROM project WHERE id = 'p1'").fetchone()
        assert row[0] == "demo"
        tables = {
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert {"checkpoint_registry", "design_state"} <= tables
    finally:
        conn.close()
