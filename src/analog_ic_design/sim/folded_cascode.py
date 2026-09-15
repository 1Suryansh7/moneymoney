"""Folded-cascode OTA benchmark fixture builder (R0-4 Track A, B5).

Golden fixture for the `B5` bench, hand-built in the `sim/` convention
(independent of the `folded_cascode` topology template so template and
fixture cross-check each other): PMOS tail M0, PMOS input pair M1/M2,
NMOS current sinks M3/M4, NMOS cascodes M5/M6, PMOS cascode load M7/M8.
Nets: vip, vin, out, vbias_tail, vbias_n1, vbias_n2, vbias_p, vdd, vss
plus internals tail, fold_p, fold_n, casc_mirror. The folded structure
folds the input pair current into the NMOS cascode branch, giving OTA
gain with a PMOS-pair input common-mode range down to Vss.
"""

from __future__ import annotations

import sqlite3

from analog_ic_design.store.schema import new_id

STAMP = "2026-09-05T00:00:00+00:00"

NMOS_MODEL = "sky130_fd_pr__nfet_01v8"
PMOS_MODEL = "sky130_fd_pr__pfet_01v8"
PIN_ORDER = "d g s b"


def build_folded_cascode(
    conn: sqlite3.Connection,
    *,
    w_in: float = 5e-06,
    l_in: float = 0.5e-06,
    w_tail: float = 5e-06,
    l_tail: float = 0.5e-06,
    w_casc_n: float = 3e-06,
    l_casc_n: float = 0.5e-06,
    w_load_p: float = 6e-06,
    l_load_p: float = 0.5e-06,
) -> str:
    """Create project/lib/cell/symbols/tech/bindings/instances/nets/ports/
    params for a folded-cascode OTA; returns the cell id.

    Geometry in SI meters (template defaults: 0.5 um lengths for OTA
    matching headroom, not the 160 nm digital-bin convention).
    """
    pid, lib, cell, tech = (new_id() for _ in range(4))
    ncell, pcell, nsym, psym = (new_id() for _ in range(4))
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, "folded_cascode_demo", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "analog_lib", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell, lib, "folded_cascode_ota", STAMP))
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

    names = ("m0", "m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8")
    inst = {name: new_id() for name in names}
    for name in ("m0", "m1", "m2", "m7", "m8"):
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (inst[name], cell, psym, name, STAMP),
        )
    for name in ("m3", "m4", "m5", "m6"):
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (inst[name], cell, nsym, name, STAMP),
        )
    nets: dict[str, str] = {}
    for name in (
        "vip",
        "vin",
        "out",
        "vbias_tail",
        "vbias_n1",
        "vbias_n2",
        "vbias_p",
        "vdd",
        "vss",
        "tail",
        "fold_p",
        "fold_n",
        "casc_mirror",
    ):
        nid = new_id()
        nets[name] = nid
        conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell, name, STAMP))
    hooks: tuple[tuple[str, str, str], ...] = (
        (inst["m0"], "d", "tail"),
        (inst["m0"], "g", "vbias_tail"),
        (inst["m0"], "s", "vdd"),
        (inst["m0"], "b", "vdd"),
        (inst["m1"], "d", "fold_p"),
        (inst["m1"], "g", "vip"),
        (inst["m1"], "s", "tail"),
        (inst["m1"], "b", "vdd"),
        (inst["m2"], "d", "fold_n"),
        (inst["m2"], "g", "vin"),
        (inst["m2"], "s", "tail"),
        (inst["m2"], "b", "vdd"),
        (inst["m3"], "d", "fold_p"),
        (inst["m3"], "g", "vbias_n1"),
        (inst["m3"], "s", "vss"),
        (inst["m3"], "b", "vss"),
        (inst["m4"], "d", "fold_n"),
        (inst["m4"], "g", "vbias_n1"),
        (inst["m4"], "s", "vss"),
        (inst["m4"], "b", "vss"),
        (inst["m5"], "d", "casc_mirror"),
        (inst["m5"], "g", "vbias_n2"),
        (inst["m5"], "s", "fold_p"),
        (inst["m5"], "b", "vss"),
        (inst["m6"], "d", "out"),
        (inst["m6"], "g", "vbias_n2"),
        (inst["m6"], "s", "fold_n"),
        (inst["m6"], "b", "vss"),
        (inst["m7"], "d", "casc_mirror"),
        (inst["m7"], "g", "vbias_p"),
        (inst["m7"], "s", "vdd"),
        (inst["m7"], "b", "vdd"),
        (inst["m8"], "d", "out"),
        (inst["m8"], "g", "vbias_p"),
        (inst["m8"], "s", "vdd"),
        (inst["m8"], "b", "vdd"),
    )
    for iid, term, net in hooks:
        conn.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
            (new_id(), iid, nets[net], term, STAMP),
        )
    sizes: tuple[tuple[str, float, float], ...] = (
        (inst["m0"], w_tail, l_tail),
        (inst["m1"], w_in, l_in),
        (inst["m2"], w_in, l_in),
        (inst["m3"], w_casc_n, l_casc_n),
        (inst["m4"], w_casc_n, l_casc_n),
        (inst["m5"], w_casc_n, l_casc_n),
        (inst["m6"], w_casc_n, l_casc_n),
        (inst["m7"], w_load_p, l_load_p),
        (inst["m8"], w_load_p, l_load_p),
    )
    for iid, w_val, l_val in sizes:
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, "W", w_val, STAMP)
        )
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)", (new_id(), iid, "L", l_val, STAMP)
        )
    conn.commit()
    return cell
