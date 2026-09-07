"""Common-Source amplifier benchmark fixture builder (Stage 3 Commit 3C).

Golden fixture for `DC_GAIN`, `AC_GAIN`, and `BANDWIDTH` contracts (`cs_amp_nmos`).
Consists of:
- NMOS input transistor M1 (`sky130_fd_pr__nfet_01v8`, W=1 µm, L=160 nm)
- PMOS active load M2 (`sky130_fd_pr__pfet_01v8`, W=2 µm, L=160 nm)
Nets: in, out, vbias, vdd, vss.
When `vbias` is biased at fixed DC (or diode-connected to `out`), the circuit operates
as a canonical small-signal common-source amplifier.
"""

from __future__ import annotations

import sqlite3

from analog_ic_design.store.schema import new_id

STAMP = "2026-09-05T00:00:00+00:00"

NMOS_MODEL = "sky130_fd_pr__nfet_01v8"
PMOS_MODEL = "sky130_fd_pr__pfet_01v8"
PIN_ORDER = "d g s b"


def build_cs_amplifier(
    conn: sqlite3.Connection,
    *,
    w_n: float = 1e-06,
    l_n: float = 160e-09,
    w_p: float = 2e-06,
    l_p: float = 160e-09,
) -> str:
    """Create project/lib/cell/symbols/tech/bindings/instances/nets/ports/params
    for a Common-Source amplifier; returns the cell id.

    Geometry in SI meters (defaults reproduce the Stage 3C prototype).
    Stage 4 sizes `w_n`/`w_p` through these knobs; validator-enforced PDK
    minima still apply (no bypass at this layer)."""
    pid, lib, cell, tech = (new_id() for _ in range(4))
    ncell, pcell, nsym, psym = (new_id() for _ in range(4))
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "cs_amp_demo", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "analog_lib", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, "cs_amp_nmos", STAMP))
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
    for name in ("in", "out", "vbias", "vdd", "vss"):
        nid = new_id()
        nets[name] = nid
        conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))

    hooks: tuple[tuple[str, str, str], ...] = (
        (nmos, "d", "out"),
        (nmos, "g", "in"),
        (nmos, "s", "vss"),
        (nmos, "b", "vss"),
        (pmos, "d", "out"),
        (pmos, "g", "vbias"),
        (pmos, "s", "vdd"),
        (pmos, "b", "vdd"),
    )
    for iid, term, net in hooks:
        conn.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
            (new_id(), iid, nets[net], term, STAMP),
        )

    params: tuple[tuple[str, str, float], ...] = (
        (nmos, "W", w_n),
        (nmos, "L", l_n),
        (pmos, "W", w_p),
        (pmos, "L", l_p),
    )
    for iid, pname, pvalue in params:
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, pname, pvalue, STAMP)
        )

    conn.commit()
    return cell
