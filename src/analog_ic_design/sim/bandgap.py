"""Bandgap PTAT/CTAT core fixture builder (R0-5, B7).

Golden fixture for the `B7` bench: two diode-connected PNPs (collectors
and bases to vss, emitters to `e1`/`e2`) at area ratio 1:8 via the PDK
`mult` parameter. The deck (runner-owned, mirror-IDC precedent) feeds
both emitters with equal ideal currents and sweeps temperature, yielding
the CTAT `Veb(T)` and PTAT `ΔVbe(T)` the runner compensates in
`metrics/tempco.py`.

PDK-quoted (Law 2), read from the pinned image:
`.../libs.ref/sky130_fd_pr/spice/sky130_fd_pr__pnp_05v5_W3p40L3p40.model.spice`
→ `.subckt sky130_fd_pr__pnp_05v5_W3p40L3p40 Collector Base Emitter`
(model name, C/B/E order, subckt kind ⇒ `X` prefix, `.param mult`).
Resistors and current feeds are ideal deck elements (documented runner
assumption); only the PNP pair is PDK-bound.
"""

from __future__ import annotations

import sqlite3

from analog_ic_design.store.schema import new_id

STAMP = "2026-09-05T00:00:00+00:00"

PNP_MODEL = "sky130_fd_pr__pnp_05v5_W3p40L3p40"
PIN_ORDER = "Collector Base Emitter"


def build_bandgap(
    conn: sqlite3.Connection,
    *,
    mult: float = 8.0,
) -> str:
    """Create project/lib/cell/symbol/tech/binding/instances/nets/ports/
    params for the two-PNP bandgap core; returns the cell id.

    Q1 unit device, Q2 `mult`× area. All geometry is the PDK-drawn
    W3p40L3p40 device; scaling is the quoted `mult` parameter (SI-pure
    float, no units).
    """
    pid, lib, cell, tech = (new_id() for _ in range(4))
    pcell, psym = new_id(), new_id()
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "bandgap_demo", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "analog_lib", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, "bandgap_core", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (pcell, lib, "pnp_model", STAMP))
    conn.execute(
        "INSERT INTO technology VALUES (?, ?, ?, ?, ?)",
        (tech, pid, "sky130A", "fd_pr@403964dc/open_pdks@1689ac3f", STAMP),
    )
    conn.execute(
        "INSERT INTO model_binding"
        " (id, technology_id, device_symbol, model_name, pin_order, kind, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (new_id(), tech, "pnp_05v5", PNP_MODEL, PIN_ORDER, "subckt", STAMP),
    )
    conn.execute("INSERT INTO symbol VALUES (?, ?, ?, ?)", (psym, pcell, "pnp_05v5", STAMP))

    q1, q2 = new_id(), new_id()
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (q1, cell, psym, "q1", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (q2, cell, psym, "q2", STAMP))
    nets: dict[str, str] = {}
    for name in ("e1", "e2", "vss"):
        nid = new_id()
        nets[name] = nid
        conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))
    hooks: tuple[tuple[str, str, str], ...] = (
        (q1, "Collector", "vss"),
        (q1, "Base", "vss"),
        (q1, "Emitter", "e1"),
        (q2, "Collector", "vss"),
        (q2, "Base", "vss"),
        (q2, "Emitter", "e2"),
    )
    for iid, term, net in hooks:
        conn.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
            (new_id(), iid, nets[net], term, STAMP),
        )
    for iid, mval in ((q1, 1.0), (q2, mult)):
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, "mult", mval, STAMP)
        )
    conn.commit()
    return cell
