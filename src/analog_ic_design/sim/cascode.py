"""Telescopic-cascode benchmark fixture builder (R0-3 Commit B4).

Golden fixture for the `B4` bench: NMOS input device M1 (source to vss),
NMOS cascode device M2 (source to M1 drain at `mid`, gate to `vbcas`),
PMOS current-source load M3 (drain to `out`, gate to `vbias_p`).
Nets: in, out, mid, vbcas, vbias_p, vdd, vss. Cascode action raises the
output impedance (and hence the gain) far above the plain common-source
stage built from the same-size input device — the physical claim B4 checks.
"""

from __future__ import annotations

import sqlite3

from analog_ic_design.store.schema import new_id

STAMP = "2026-09-05T00:00:00+00:00"

NMOS_MODEL = "sky130_fd_pr__nfet_01v8"
PMOS_MODEL = "sky130_fd_pr__pfet_01v8"
PIN_ORDER = "d g s b"


def build_cascode(
    conn: sqlite3.Connection,
    *,
    w_n: float = 1e-06,
    w_p: float = 2e-06,
) -> str:
    """Create project/lib/cell/symbols/tech/bindings/instances/nets/ports/
    params for a telescopic cascode gain stage; returns the cell id.

    Geometry in SI meters (all lengths 160 nm, 1G bin convention).
    `w_n` sizes both NMOS devices; `w_p` sizes the PMOS load.
    """
    pid, lib, cell, tech = (new_id() for _ in range(4))
    ncell, pcell, nsym, psym = (new_id() for _ in range(4))
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "cascode_demo", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "analog_lib", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, "cascode_nmos", STAMP))
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

    m1, m2, m3 = new_id(), new_id(), new_id()
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (m1, cell, nsym, "m1", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (m2, cell, nsym, "m2", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (m3, cell, psym, "m3", STAMP))
    nets: dict[str, str] = {}
    for name in ("in", "out", "mid", "vbcas", "vbias_p", "vdd", "vss"):
        nid = new_id()
        nets[name] = nid
        conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))
    hooks: tuple[tuple[str, str, str], ...] = (
        (m1, "d", "mid"),
        (m1, "g", "in"),
        (m1, "s", "vss"),
        (m1, "b", "vss"),
        (m2, "d", "out"),
        (m2, "g", "vbcas"),
        (m2, "s", "mid"),
        (m2, "b", "vss"),
        (m3, "d", "out"),
        (m3, "g", "vbias_p"),
        (m3, "s", "vdd"),
        (m3, "b", "vdd"),
    )
    for iid, term, net in hooks:
        conn.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
            (new_id(), iid, nets[net], term, STAMP),
        )
    params: tuple[tuple[str, str, float], ...] = (
        (m1, "W", w_n),
        (m1, "L", 160e-09),
        (m2, "W", w_n),
        (m2, "L", 160e-09),
        (m3, "W", w_p),
        (m3, "L", 160e-09),
    )
    for iid, pname, pvalue in params:
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, pname, pvalue, STAMP)
        )
    conn.commit()
    return cell
