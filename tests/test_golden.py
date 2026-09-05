"""Stage 1 Commit 1G: NMOS golden fixture (BLOCKING human checkpoint open).

READ-ONLY GOLDEN REFERENCE: `tests/golden/nmos.cir` is ground truth. Never
edit it to make a test pass — a failing comparison means the compiler (or
the fixture) is wrong. Changing the golden requires a separate,
human-authored commit after re-verification (see the checkpoint below).

PDK ANTI-HALLUCINATION RECORD (AGENTS.md section 14.4): no Sky130 syntax
below comes from memory. Source file (on disk in the pinned EDA image):
  /usr/local/share/pdk/sky130A/libs.ref/sky130_fd_pr/spice/sky130_fd_pr__nfet_01v8__tt.pm3.spice
Quoted verbatim (subckt definition block; wrapped here for line length only):
  .subckt  sky130_fd_pr__nfet_01v8 d g s b
  .param  l = 1 w = 1 nf = 1.0 ad = 0 as = 0 pd = 0 ps = 0 nrd = 0
    nrs = 0 sa = 0 sb = 0 sd = 0 mult = 1
  msky130_fd_pr__nfet_01v8 d g s b sky130_fd_pr__nfet_01v8__model ...
Verified FROM that file: model name `sky130_fd_pr__nfet_01v8`, pin order
d/g/s/b, subckt kind (hence `X` prefix, not `M`).
AUTHOR-CHOSEN (NOT PDK-quoted, for the human plausibility check): W=1e-6 m,
L=150e-9 m, net names, cell/instance names, technology version string
(fd_pr@403964dc/open_pdks@1689ac3f from /pdk-record/nodeinfo.json).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest

from analog_ic_design.circuit import CompilerError, compile_netlist, validate
from analog_ic_design.store import connect, migrate, new_id

STAMP = "2026-09-05T00:00:00+00:00"
GOLDEN = Path(__file__).resolve().parent / "golden" / "nmos.cir"


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    pid, lib, cell, tech = (new_id() for _ in range(4))
    symcell, sym = new_id(), new_id()
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "demo", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "l", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, "nmos_golden", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (symcell, lib, "models", STAMP))
    conn.execute(
        "INSERT INTO technology VALUES (?, ?, ?, ?, ?)",
        (tech, pid, "sky130A", "fd_pr@403964dc/open_pdks@1689ac3f", STAMP),
    )
    conn.execute(
        "INSERT INTO model_binding"
        " (id, technology_id, device_symbol, model_name, pin_order, kind, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (new_id(), tech, "nfet_01v8", "sky130_fd_pr__nfet_01v8", "d g s b", "subckt", STAMP),
    )
    conn.execute("INSERT INTO symbol VALUES (?, ?, ?, ?)", (sym, symcell, "nfet_01v8", STAMP))
    m1 = new_id()
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (m1, cell, sym, "m1", STAMP))
    nets: dict[str, str] = {}
    for name in ("drain", "gate", "source", "vss"):
        nid = new_id()
        nets[name] = nid
        conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))
    for term, net in (("d", "drain"), ("g", "gate"), ("s", "source"), ("b", "vss")):
        conn.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
            (new_id(), m1, nets[net], term, STAMP),
        )
    conn.execute(
        "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), m1, "W", 1e-06, STAMP)
    )
    conn.execute(
        "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), m1, "L", 150e-09, STAMP)
    )
    conn.commit()
    yield conn
    conn.close()


def _cell(db: sqlite3.Connection) -> str:
    row = db.execute("SELECT id FROM cell WHERE name = 'nmos_golden'").fetchone()
    assert row is not None
    return str(row[0])


def test_golden_nmos_byte_identical(db: sqlite3.Connection) -> None:
    raw = GOLDEN.read_bytes()
    assert b"\r" not in raw and raw.endswith(b"\n")
    assert compile_netlist(db, _cell(db)) == raw.decode("utf-8")


def test_fixture_passes_validation_gate(db: sqlite3.Connection) -> None:
    assert validate(db, _cell(db)).valid


def test_undeclared_model_kind_fails_closed(db: sqlite3.Connection) -> None:
    db.execute("UPDATE model_binding SET kind = NULL")
    db.commit()
    with pytest.raises(CompilerError):
        compile_netlist(db, _cell(db))


def test_swapped_terminals_still_compiles_checkpoint_necessity(
    db: sqlite3.Connection,
) -> None:
    """Adversarial: swapping d/s nets stays structurally valid and compiles
    to a DIFFERENT (wrong) netlist. No structural check can catch this —
    it is exactly what the 1G human checkpoint exists to rule out."""
    d_id = db.execute("SELECT id FROM net WHERE name = 'drain'").fetchone()[0]
    s_id = db.execute("SELECT id FROM net WHERE name = 'source'").fetchone()[0]
    db.execute("UPDATE port SET net_id = ? WHERE name = 'd'", (s_id,))
    db.execute("UPDATE port SET net_id = ? WHERE name = 's'", (d_id,))
    db.commit()
    swapped = compile_netlist(db, _cell(db))
    assert swapped != GOLDEN.read_text(encoding="utf-8")
    assert "Xm1 source gate drain vss" in swapped
