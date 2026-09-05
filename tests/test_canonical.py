"""Stage 1 Commit 1D tests: canonical identity.

The money test: the same logical circuit, entered with different opaque ids
and different row order, canonicalizes to identical bytes and hash. Plus
mutation sensitivity, exact-encoding byte stability, and the empty cell.
Failure taxonomy: Schema.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator

import pytest

from analog_ic_design.circuit import (
    GraphError,
    canonical_encode,
    canonical_hash,
    canonicalize,
)
from analog_ic_design.store import connect, migrate, new_id

STAMP = "2026-09-05T00:00:00+00:00"


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    yield conn
    conn.close()


def _enter(conn: sqlite3.Connection, flip: bool) -> str:
    """Enter the same logical inverter twice; `flip` swaps sibling row order
    (nets, ports) with fresh uuids. Parents always precede children (FKs)."""
    pid, lib, cell, sym, m1 = (new_id() for _ in range(5))
    n_out, n_in = new_id(), new_id()
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "d", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "l", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, "inv", STAMP))
    conn.execute("INSERT INTO symbol VALUES (?, ?, ?, ?)", (sym, cell, "nf", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (m1, cell, sym, "m1", STAMP))
    nets = (("out", n_out), ("in", n_in))
    if flip:
        nets = (("in", n_in), ("out", n_out))
    for name, nid in nets:
        conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))
    terms = (("d", n_out), ("g", n_in))
    if flip:
        terms = (("g", n_in), ("d", n_out))
    for term, nid in terms:
        conn.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)", (new_id(), m1, nid, term, STAMP)
        )
    conn.commit()
    return cell


def test_same_circuit_different_ids_and_order_one_hash(db: sqlite3.Connection) -> None:
    c1 = _enter(db, flip=False)
    h1 = canonical_hash(canonicalize(db, c1))
    e1 = canonical_encode(canonicalize(db, c1))
    c2 = _enter(db, flip=True)
    assert c1 != c2
    assert canonical_encode(canonicalize(db, c2)) == e1
    assert canonical_hash(canonicalize(db, c2)) == h1


def test_exact_encoding_is_byte_stable(db: sqlite3.Connection) -> None:
    cell = _enter(db, flip=False)
    assert canonical_encode(canonicalize(db, cell)) == (
        "cell inv\n"
        "device m1 nf\n"
        "net in\n"
        "net out\n"
        "terminal m1 d out\n"
        "terminal m1 g in\n"
    )


def test_mutations_change_the_hash(db: sqlite3.Connection) -> None:
    cell = _enter(db, flip=False)
    before = canonical_hash(canonicalize(db, cell))
    db.execute("UPDATE net SET name = ? WHERE name = ?", ("out2", "out"))
    db.commit()
    assert canonical_hash(canonicalize(db, cell)) != before


def test_empty_cell_hash_is_deterministic(db: sqlite3.Connection) -> None:
    pid, lib = new_id(), new_id()
    db.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "d", STAMP))
    db.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "l", STAMP))
    c1, c2 = new_id(), new_id()
    for cid in (c1, c2):
        db.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cid, lib, "empty", STAMP))
    db.commit()
    assert canonical_encode(canonicalize(db, c1)) == "cell empty\n"
    assert canonical_hash(canonicalize(db, c1)) == canonical_hash(canonicalize(db, c2))
    assert len(canonical_hash(canonicalize(db, c1))) == 64


def test_unknown_cell_raises(db: sqlite3.Connection) -> None:
    with pytest.raises(GraphError):
        canonicalize(db, "no-such-cell")
