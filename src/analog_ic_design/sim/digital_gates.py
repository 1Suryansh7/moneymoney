"""Transistor-level CMOS digital logic gates with symbols (NOT and NAND).

Constructs canonical CMOS logic gates using SkyWater 130nm primitives:
1. not_gate: 1 NMOS + 1 PMOS inverter with symbol (in, out, vdd, vss)
2. nand_gate: 2 PMOS parallel + 2 NMOS series with symbol (a, b, out, vdd, vss)

Strict SI physical units: transistor widths and lengths are meters.
Every gate creates both its transistor schematic view and its external symbol view.
"""

from __future__ import annotations

import sqlite3
from typing import Final

from analog_ic_design.store.schema import new_id

STAMP: Final = "2026-09-10T00:00:00+00:00"
NMOS_MODEL: Final = "sky130_fd_pr__nfet_01v8"
PMOS_MODEL: Final = "sky130_fd_pr__pfet_01v8"
PIN_ORDER: Final = "d g s b"


def _ensure_project_and_tech(
    conn: sqlite3.Connection, project_name: str = "digital_logic"
) -> tuple[str, str, str]:
    """Get or create project, library, and sky130 technology bindings."""
    row = conn.execute(
        "SELECT p.id, l.id, t.id FROM project p "
        "JOIN library l ON l.project_id = p.id "
        "JOIN technology t ON t.project_id = p.id "
        "WHERE p.name = ?",
        (project_name,),
    ).fetchone()
    if row is not None:
        return str(row[0]), str(row[1]), str(row[2])

    pid, lib, tech = new_id(), new_id(), new_id()
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (pid, project_name, STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (lib, pid, "logic_cells", STAMP))
    conn.execute(
        "INSERT INTO technology VALUES (?, ?, ?, ?, ?)",
        (tech, pid, "sky130A", "fd_pr@403964dc/open_pdks@1689ac3f", STAMP),
    )
    # Register primitive device model bindings
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
    return pid, lib, tech


def _get_or_create_device_symbol(
    conn: sqlite3.Connection, lib_id: str, name: str
) -> str:
    """Get or create primitive device symbol definition."""
    row = conn.execute(
        "SELECT s.id FROM symbol s JOIN cell c ON c.id = s.cell_id "
        "WHERE c.library_id = ? AND s.name = ?",
        (lib_id, name),
    ).fetchone()
    if row is not None:
        return str(row[0])
    cell_id, sym_id = new_id(), new_id()
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell_id, lib_id, f"{name}_model", STAMP))
    conn.execute("INSERT INTO symbol VALUES (?, ?, ?, ?)", (sym_id, cell_id, name, STAMP))
    return sym_id


def build_not_gate(
    conn: sqlite3.Connection,
    *,
    w_n: float = 1.0e-06,
    l_n: float = 0.15e-06,
    w_p: float = 2.0e-06,
    l_p: float = 0.15e-06,
    project_name: str = "digital_logic",
    cell_name: str = "not_gate",
) -> tuple[str, str]:
    """Build a CMOS Inverter (NOT gate) schematic + symbol view.

    Returns:
        (cell_id, symbol_id)
    """
    _, lib_id, _ = _ensure_project_and_tech(conn, project_name)
    nsym = _get_or_create_device_symbol(conn, lib_id, "nfet_01v8")
    psym = _get_or_create_device_symbol(conn, lib_id, "pfet_01v8")

    cell_id = new_id()
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell_id, lib_id, cell_name, STAMP))

    # Transistor instances
    mn, mp = new_id(), new_id()
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (mn, cell_id, nsym, "mn1", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (mp, cell_id, psym, "mp1", STAMP))

    # Nets: in, out, vdd, vss
    nets: dict[str, str] = {}
    for name in ("in", "out", "vdd", "vss"):
        nid = new_id()
        nets[name] = nid
        conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell_id, name, STAMP))

    # Transistor terminal connections
    hooks: tuple[tuple[str, str, str], ...] = (
        (mn, "d", "out"),
        (mn, "g", "in"),
        (mn, "s", "vss"),
        (mn, "b", "vss"),
        (mp, "d", "out"),
        (mp, "g", "in"),
        (mp, "s", "vdd"),
        (mp, "b", "vdd"),
    )
    for iid, term, net in hooks:
        conn.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
            (new_id(), iid, nets[net], term, STAMP),
        )

    # Device parameters (SI units: meters)
    params: tuple[tuple[str, str, float], ...] = (
        (mn, "W", w_n),
        (mn, "L", l_n),
        (mp, "W", w_p),
        (mp, "L", l_p),
    )
    for iid, pname, pvalue in params:
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)",
            (new_id(), iid, pname, pvalue, STAMP),
        )

    # --- Create Cell Symbol View ---
    symbol_id = new_id()
    conn.execute("INSERT INTO symbol VALUES (?, ?, ?, ?)", (symbol_id, cell_id, cell_name, STAMP))

    # External symbol ports (cell_id not null, instance_id is null)
    for pin in ("in", "out", "vdd", "vss"):
        conn.execute(
            "INSERT INTO port VALUES (?, ?, NULL, ?, ?, ?)",
            (new_id(), cell_id, nets[pin], pin, STAMP),
        )

    conn.commit()
    return cell_id, symbol_id


def build_nand_gate(
    conn: sqlite3.Connection,
    *,
    w_n: float = 1.0e-06,
    l_n: float = 0.15e-06,
    w_p: float = 2.0e-06,
    l_p: float = 0.15e-06,
    project_name: str = "digital_logic",
    cell_name: str = "nand_gate",
) -> tuple[str, str]:
    """Build a 2-input CMOS NAND gate schematic + symbol view.

    Circuit topology:
    - 2 PMOS in parallel between vdd and out (gates: a, b)
    - 2 NMOS in series between out and vss (gates: a, b, internal node: mid)

    Returns:
        (cell_id, symbol_id)
    """
    _, lib_id, _ = _ensure_project_and_tech(conn, project_name)
    nsym = _get_or_create_device_symbol(conn, lib_id, "nfet_01v8")
    psym = _get_or_create_device_symbol(conn, lib_id, "pfet_01v8")

    cell_id = new_id()
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (cell_id, lib_id, cell_name, STAMP))

    # 4 MOSFET instances
    mp1, mp2 = new_id(), new_id()
    mn1, mn2 = new_id(), new_id()
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (mp1, cell_id, psym, "mp1", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (mp2, cell_id, psym, "mp2", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (mn1, cell_id, nsym, "mn1", STAMP))
    conn.execute("INSERT INTO instance VALUES (?, ?, ?, ?, ?)", (mn2, cell_id, nsym, "mn2", STAMP))

    # Nets: a, b, out, mid, vdd, vss
    nets: dict[str, str] = {}
    for name in ("a", "b", "out", "mid", "vdd", "vss"):
        nid = new_id()
        nets[name] = nid
        conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nid, cell_id, name, STAMP))

    # Connections
    hooks: tuple[tuple[str, str, str], ...] = (
        # PMOS 1: gate a, drain out, source vdd, bulk vdd
        (mp1, "d", "out"),
        (mp1, "g", "a"),
        (mp1, "s", "vdd"),
        (mp1, "b", "vdd"),
        # PMOS 2: gate b, drain out, source vdd, bulk vdd
        (mp2, "d", "out"),
        (mp2, "g", "b"),
        (mp2, "s", "vdd"),
        (mp2, "b", "vdd"),
        # NMOS 1: gate a, drain out, source mid, bulk vss
        (mn1, "d", "out"),
        (mn1, "g", "a"),
        (mn1, "s", "mid"),
        (mn1, "b", "vss"),
        # NMOS 2: gate b, drain mid, source vss, bulk vss
        (mn2, "d", "mid"),
        (mn2, "g", "b"),
        (mn2, "s", "vss"),
        (mn2, "b", "vss"),
    )
    for iid, term, net in hooks:
        conn.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
            (new_id(), iid, nets[net], term, STAMP),
        )

    # Parameters
    for iid, w, l_val in (
        (mp1, w_p, l_p),
        (mp2, w_p, l_p),
        (mn1, w_n, l_n),
        (mn2, w_n, l_n),
    ):
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)",
            (new_id(), iid, "W", w, STAMP),
        )
        conn.execute(
            "INSERT INTO parameter VALUES (?, ?, ?, ?, ?)",
            (new_id(), iid, "L", l_val, STAMP),
        )

    # --- Create Cell Symbol View ---
    symbol_id = new_id()
    conn.execute("INSERT INTO symbol VALUES (?, ?, ?, ?)", (symbol_id, cell_id, cell_name, STAMP))

    # External symbol ports
    for pin in ("a", "b", "out", "vdd", "vss"):
        conn.execute(
            "INSERT INTO port VALUES (?, ?, NULL, ?, ?, ?)",
            (new_id(), cell_id, nets[pin], pin, STAMP),
        )

    conn.commit()
    return cell_id, symbol_id
