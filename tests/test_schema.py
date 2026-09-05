"""Stage 1 Commit 1B tests: migration framework + structural schema contract.

Proves versioning/idempotence, FK enforcement, the port single-parent CHECK,
cascade behavior, and the deliberate split (behavior-owned tables are ABSENT
until their owning commits). Failure taxonomy: Schema.
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
STRUCTURAL = ("project", "library", "cell", "symbol", "instance", "port", "net")
EXISTENCE = ("design_revision", "artifact")
DEFERRED = (
    "job",
    "testbench",
    "analysis",
    "measurement",
    "experiment",
)


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    yield conn
    conn.close()


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def _hierarchy(conn: sqlite3.Connection) -> dict[str, str]:
    ids = {k: new_id() for k in ("p", "l", "c", "s", "i", "n")}
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (ids["p"], "demo", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (ids["l"], ids["p"], "lib", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (ids["c"], ids["l"], "inv", STAMP))
    conn.execute("INSERT INTO symbol VALUES (?, ?, ?, ?)", (ids["s"], ids["c"], "inv_sym", STAMP))
    conn.execute(
        "INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (ids["i"], ids["c"], ids["s"], "m1", STAMP)
    )
    conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (ids["n"], ids["c"], "vdd", STAMP))
    conn.commit()
    return ids


def test_migrate_lands_current_version_and_is_idempotent(db: sqlite3.Connection) -> None:
    assert SCHEMA_VERSION == 3
    assert get_schema_version(db) == SCHEMA_VERSION
    assert migrate(db) == SCHEMA_VERSION
    assert get_schema_version(db) == SCHEMA_VERSION


def test_upgrade_preserves_v1_data() -> None:
    conn = connect()
    conn.executescript(MIGRATIONS[0][1])
    conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (1, ?)", (STAMP,))
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", ("p1", "demo", STAMP))
    conn.commit()
    assert get_schema_version(conn) == 1
    assert migrate(conn) == SCHEMA_VERSION
    row = conn.execute("SELECT name FROM project WHERE id = 'p1'").fetchone()
    assert row[0] == "demo"
    conn.close()


def test_structural_and_existence_tables_present(db: sqlite3.Connection) -> None:
    tables = _tables(db)
    assert set(STRUCTURAL) | set(EXISTENCE) | {"schema_version"} <= tables


def test_deferred_tables_absent_until_owning_commits(db: sqlite3.Connection) -> None:
    assert not (set(DEFERRED) & _tables(db))


def test_foreign_keys_enforced(db: sqlite3.Connection) -> None:
    assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (new_id(), "no-such-lib", "x", STAMP))


def test_hierarchy_and_port_hookup(db: sqlite3.Connection) -> None:
    ids = _hierarchy(db)
    db.execute(
        "INSERT INTO port VALUES (?, ?, NULL, ?, ?, ?)",
        (new_id(), ids["c"], ids["n"], "vdd_pin", STAMP),
    )
    db.execute(
        "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
        (new_id(), ids["i"], ids["n"], "drain", STAMP),
    )
    db.commit()
    count = db.execute("SELECT COUNT(*) FROM port WHERE net_id = ?", (ids["n"],)).fetchone()[0]
    assert count == 2


def test_port_rejects_orphan_and_double_parent(db: sqlite3.Connection) -> None:
    ids = _hierarchy(db)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO port VALUES (?, NULL, NULL, ?, ?, ?)", (new_id(), ids["n"], "o", STAMP)
        )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO port VALUES (?, ?, ?, ?, ?, ?)",
            (new_id(), ids["c"], ids["i"], ids["n"], "both", STAMP),
        )


def test_cascade_and_set_null(db: sqlite3.Connection) -> None:
    ids = _hierarchy(db)
    pid = new_id()
    db.execute(
        "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)", (pid, ids["i"], ids["n"], "d", STAMP)
    )
    db.execute("DELETE FROM net WHERE id = ?", (ids["n"],))
    assert db.execute("SELECT COUNT(*) FROM net").fetchone()[0] == 0
    row = db.execute("SELECT net_id FROM port WHERE id = ?", (pid,)).fetchone()
    assert row[0] is None
    db.execute("DELETE FROM project WHERE id = ?", (ids["p"],))
    for table in ("library", "cell", "symbol", "instance", "port"):
        assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_new_id_format_and_uniqueness() -> None:
    ids = {new_id() for _ in range(200)}
    assert len(ids) == 200
    assert all(len(i) == 32 and all(c in "0123456789abcdef" for c in i) for i in ids)


def test_revision_chain_and_artifact_link(db: sqlite3.Connection) -> None:
    r1, r2, a1 = new_id(), new_id(), new_id()
    db.execute("INSERT INTO design_revision VALUES (?, NULL, ?, ?)", (r1, "init", STAMP))
    db.execute("INSERT INTO design_revision VALUES (?, ?, ?, ?)", (r2, r1, "tweak", STAMP))
    db.execute("INSERT INTO artifact VALUES (?, ?, ?, ?)", (a1, r2, "netlists/inv.cir", STAMP))
    row = db.execute(
        "SELECT parent_id FROM design_revision WHERE id = ?", (r2,)
    ).fetchone()
    assert row[0] == r1
    row = db.execute("SELECT design_revision_id FROM artifact WHERE id = ?", (a1,)).fetchone()
    assert row[0] == r2
