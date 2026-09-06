"""CMOS inverter fixture builder (Stage 2 Commit 2H).

PROTOTYPE for the Stage 6 topology templates: hardcoded sizing for the first-
simulation checkpoint, explicit PDK citations, no pretense of generality.
Sizing (bin-verified, NOT merely plausible): NMOS W=1 µm / L=160 nm fits TT
bin `lmin=1.5e-07 lmax=1.8e-07 wmin=1.0e-06 wmax=1.26e-6`; PMOS W=2 µm /
L=160 nm fits TT bin `lmin=1.5e-07 lmax=1.8e-07 wmin=2e-06 wmax=3.0e-6`
(strictly interior — L=150 nm sits exactly on lmin where float rounding
could miss the bin).

PDK evidence (both read from the pinned image, Law 2):
- NMOS: `.../libs.ref/sky130_fd_pr/spice/sky130_fd_pr__nfet_01v8__tt.pm3.spice`
  `.subckt  sky130_fd_pr__nfet_01v8 d g s b` (subckt kind → X prefix).
- PMOS: `.../libs.ref/sky130_fd_pr/spice/sky130_fd_pr__pfet_01v8__tt.pm3.spice`
  `.subckt  sky130_fd_pr__pfet_01v8 d g s b` (subckt kind → X prefix).
Technology version mirrors the 1G convention:
`fd_pr@403964dc/open_pdks@1689ac3f` (from `/pdk-record/nodeinfo.json`).
"""

from __future__ import annotations

import sqlite3

from analog_ic_design.store.schema import new_id

STAMP = "2026-09-05T00:00:00+00:00"

NMOS_MODEL = "sky130_fd_pr__nfet_01v8"
PMOS_MODEL = "sky130_fd_pr__pfet_01v8"
PIN_ORDER = "d g s b"


def build_inverter(conn: sqlite3.Connection) -> str:
    """Create project/lib/cell/symbols/tech/bindings/instances/nets/ports/
    params for a CMOS inverter; returns the inverter cell id."""
    pid, lib, cell, tech = (new_id() for _ in range(4))
    ncell, pcell, nsym, psym = (new_id() for _ in range(4))
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "demo", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "l", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, "inverter", STAMP))
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
    nmos, pmos = new_id(), new_id()
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (nmos, cell, nsym, "m1", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (pmos, cell, psym, "m2", STAMP))
    nets: dict[str, str] = {}
    for name in ("in", "out", "vdd", "vss"):
        nid = new_id()
        nets[name] = nid
        conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))
    hooks: tuple[tuple[str, str, str], ...] = (
        (nmos, "d", "out"),
        (nmos, "g", "in"),
        (nmos, "s", "vss"),
        (nmos, "b", "vss"),
        (pmos, "d", "out"),
        (pmos, "g", "in"),
        (pmos, "s", "vdd"),
        (pmos, "b", "vdd"),
    )
    for iid, term, net in hooks:
        conn.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
            (new_id(), iid, nets[net], term, STAMP),
        )
    params: tuple[tuple[str, str, float], ...] = (
        (nmos, "W", 1e-06),
        (nmos, "L", 160e-09),
        (pmos, "W", 2e-06),
        (pmos, "L", 160e-09),
    )
    for iid, pname, pvalue in params:
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, pname, pvalue, STAMP)
        )
    conn.commit()
    return cell
