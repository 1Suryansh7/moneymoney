"""Differential-pair benchmark fixture builder (Stage 3 Commit 3H).

Golden fixture for the `OFFSET` contract (`diff_pair_nmos`): NMOS input
pair M1/M2 with PMOS mirror load M3/M4 (M3 diode-connected) and NMOS tail
source M5. Symmetric sizing gives near-zero systematic offset (mismatch
models off by default); intentional W/L imbalance produces a predictable
nonzero offset. Nets: inp, inn, outp, outn, tail, vbias, vdd, vss.
"""

from __future__ import annotations

import sqlite3

from analog_ic_design.store.schema import new_id

STAMP = "2026-09-05T00:00:00+00:00"

NMOS_MODEL = "sky130_fd_pr__nfet_01v8"
PMOS_MODEL = "sky130_fd_pr__pfet_01v8"
PIN_ORDER = "d g s b"


def build_diff_pair(
    conn: sqlite3.Connection,
    *,
    w1: float = 1e-06,
    w2: float = 1e-06,
) -> str:
    """Create project/lib/cell/symbols/tech/bindings/instances/nets/ports/
    params for an NMOS differential pair; returns the cell id.

    `w1`/`w2` size the M1/M2 input pair (intentional mismatch knob).
    All lengths 160 nm; PMOS load 2 µm; tail 1 µm (all SI meters).
    """
    pid, lib, cell, tech = (new_id() for _ in range(4))
    ncell, pcell, nsym, psym = (new_id() for _ in range(4))
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "diff_demo", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "analog_lib", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, "diff_pair_nmos", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (ncell, lib, "nfet_model", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (pcell, lib, "pfet_model", STAMP))
    conn.execute(
        "INSERT INTO technology VALUES (?, ?, ?, ?, ?)",
        (tech, pid, "sky130A", "fd_pr@403964dc/open_pdks@1689ac3f", STAMP),
    )
    conn.execute(
        "INSERT INTO model_binding"
        " (id, technology_id, device_symbol, model_name, pin_order, kind, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (new_id(), tech, "nfet_01v8", NMOS_MODEL, PIN_ORDER, "subckt", STAMP),
    )
    conn.execute(
        "INSERT INTO model_binding"
        " (id, technology_id, device_symbol, model_name, pin_order, kind, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (new_id(), tech, "pfet_01v8", PMOS_MODEL, PIN_ORDER, "subckt", STAMP),
    )
    conn.execute("INSERT INTO symbol VALUES (?, ?, ?, ?)", (nsym, ncell, "nfet_01v8", STAMP))
    conn.execute("INSERT INTO symbol VALUES (?, ?, ?, ?)", (psym, pcell, "pfet_01v8", STAMP))

    m1, m2, m3, m4, m5 = (new_id() for _ in range(5))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (m1, cell, nsym, "m1", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (m2, cell, nsym, "m2", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (m3, cell, psym, "m3", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (m4, cell, psym, "m4", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (m5, cell, nsym, "m5", STAMP))
    nets: dict[str, str] = {}
    for name in ("inp", "inn", "outp", "outn", "tail", "vbias", "vdd", "vss"):
        nid = new_id()
        nets[name] = nid
        conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))
    hooks: tuple[tuple[str, str, str], ...] = (
        (m1, "d", "outp"),
        (m1, "g", "inp"),
        (m1, "s", "tail"),
        (m1, "b", "vss"),
        (m2, "d", "outn"),
        (m2, "g", "inn"),
        (m2, "s", "tail"),
        (m2, "b", "vss"),
        (m3, "d", "outp"),
        (m3, "g", "outp"),
        (m3, "s", "vdd"),
        (m3, "b", "vdd"),
        (m4, "d", "outn"),
        (m4, "g", "outp"),
        (m4, "s", "vdd"),
        (m4, "b", "vdd"),
        (m5, "d", "tail"),
        (m5, "g", "vbias"),
        (m5, "s", "vss"),
        (m5, "b", "vss"),
    )
    for iid, term, net in hooks:
        conn.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
            (new_id(), iid, nets[net], term, STAMP),
        )
    params: tuple[tuple[str, str, float], ...] = (
        (m1, "W", w1),
        (m1, "L", 160e-09),
        (m2, "W", w2),
        (m2, "L", 160e-09),
        (m3, "W", 2e-06),
        (m3, "L", 160e-09),
        (m4, "W", 2e-06),
        (m4, "L", 160e-09),
        (m5, "W", 1e-06),
        (m5, "L", 160e-09),
    )
    for iid, pname, pvalue in params:
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, pname, pvalue, STAMP)
        )
    conn.commit()
    return cell
