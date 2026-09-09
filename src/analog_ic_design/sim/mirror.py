"""NMOS current-mirror benchmark fixture builder (R0-2 Commit B1).

Golden fixture for the `B1` bench: matched NMOS pair M1 (diode-connected)
+ M2, same W/L, common source/bulk. Nets: in_ref, out_mirror, vdd, vss.
Reference current enters via an ideal IDC source in the testbench;
the output branch is held by the sweep voltage source, whose branch
current is the measured mirror output.
"""

from __future__ import annotations

import sqlite3

from analog_ic_design.store.schema import new_id

STAMP = "2026-09-05T00:00:00+00:00"

NMOS_MODEL = "sky130_fd_pr__nfet_01v8"
PIN_ORDER = "d g s b"


def build_mirror(
    conn: sqlite3.Connection,
    *,
    w: float = 1e-06,
) -> str:
    """Create project/lib/cell/symbols/tech/bindings/instances/nets/ports/
    params for a matched NMOS current mirror; returns the cell id.

    `w` sizes both M1 and M2 (matched by construction). Length 160 nm,
    following the 1G bin-verified convention. All values SI meters.
    """
    pid, lib, cell, tech = (new_id() for _ in range(4))
    ncell, nsym = new_id(), new_id()
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "mirror_demo", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "analog_lib", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, "mirror_nmos", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (ncell, lib, "nfet_model", STAMP))
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
    conn.execute("INSERT INTO symbol VALUES (?, ?, ?, ?)", (nsym, ncell, "nfet_01v8", STAMP))

    m1, m2 = new_id(), new_id()
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (m1, cell, nsym, "m1", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (m2, cell, nsym, "m2", STAMP))
    # No vdd net: this NMOS-only core has no supply connection. The testbench
    # pushes the reference current from its own VDD rail (Iref vdd->in_ref);
    # pulling it to ground instead starves the diode and parks both devices
    # OFF (observed live: ~1e-12 A output). See bench B1 docstring.
    nets: dict[str, str] = {}
    for name in ("in_ref", "out_mirror", "vss"):
        nid = new_id()
        nets[name] = nid
        conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))
    hooks: tuple[tuple[str, str, str], ...] = (
        (m1, "d", "in_ref"),
        (m1, "g", "in_ref"),
        (m1, "s", "vss"),
        (m1, "b", "vss"),
        (m2, "d", "out_mirror"),
        (m2, "g", "in_ref"),
        (m2, "s", "vss"),
        (m2, "b", "vss"),
    )
    for iid, term, net in hooks:
        conn.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
            (new_id(), iid, nets[net], term, STAMP),
        )
    params: tuple[tuple[str, str, float], ...] = (
        (m1, "W", w),
        (m1, "L", 160e-09),
        (m2, "W", w),
        (m2, "L", 160e-09),
    )
    for iid, pname, pvalue in params:
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, pname, pvalue, STAMP)
        )
    conn.commit()
    return cell
