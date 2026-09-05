"""Schema → SPICE netlist compiler (Stage 1 Commit 1E).

Emits one cell as deterministic SPICE text: title line, one device line per
instance in canonical (name-sorted) order, `.end`. Netlists are byte-stable
for identical logical circuits — the byte-identity half of the 1G golden
comparison (simulator OUTPUT stays tolerance-based; only netlists compare
byte-identical).

Non-negotiable rules:
- NOTHING is invented. Terminal order comes from the declared
  `model_binding.pin_order` for the instance's symbol; parameter values come
  from `parameter` rows; a missing binding, pin, connection, or non-numeric
  value is a fail-closed `CompilerError`, never a guess.
- Pin ORDER is PDK truth: 1G hand-verifies each stored `pin_order` against
  the PDK docs. This module only consumes it. Generic fixtures here use
  obviously-non-PDK names (`TEST_*`) so no PDK syntax is implied.
- Net names emit verbatim (no `gnd`→`0` magic); testbench concerns belong
  to Stage 2. Floats format via `repr` (shortest round-trip, deterministic).
"""

from __future__ import annotations

import sqlite3


class CompilerError(ValueError):
    """Netlist cannot be compiled from schema. Failure taxonomy: Netlist."""


def _cell_project(conn: sqlite3.Connection, cell_id: str) -> tuple[str, str]:
    row = conn.execute(
        "SELECT c.name, l.project_id FROM cell c JOIN library l ON l.id = c.library_id"
        " WHERE c.id = ?",
        (cell_id,),
    ).fetchone()
    if row is None:
        raise CompilerError(f"Netlist: unknown cell {cell_id!r}")
    return str(row[0]), str(row[1])


def _binding(
    conn: sqlite3.Connection, technology_id: str, symbol: str
) -> tuple[str, tuple[str, ...]]:
    row = conn.execute(
        "SELECT model_name, pin_order FROM model_binding"
        " WHERE technology_id = ? AND device_symbol = ?",
        (technology_id, symbol),
    ).fetchone()
    if row is None:
        raise CompilerError(f"Netlist: no model binding for symbol {symbol!r}")
    pins = tuple(str(row[1]).split())
    if not pins:
        raise CompilerError(f"Netlist: empty pin_order for symbol {symbol!r}")
    return str(row[0]), pins


def _si_float(value: object, instance: str, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CompilerError(
            f"Netlist: parameter {name!r} of {instance!r} is not a numeric SI value"
        )
    return float(value)


def compile_netlist(conn: sqlite3.Connection, cell_id: str) -> str:
    """Compile `cell_id` to deterministic SPICE text (LF, trailing newline)."""
    cell_name, project_id = _cell_project(conn, cell_id)
    tech = conn.execute(
        "SELECT id FROM technology WHERE project_id = ?", (project_id,)
    ).fetchone()
    if tech is None:
        raise CompilerError("Netlist: project has no technology binding")
    technology_id = str(tech[0])
    instances = conn.execute(
        "SELECT i.id, i.name, s.name FROM instance i JOIN symbol s ON s.id = i.symbol_id"
        " WHERE i.cell_id = ? ORDER BY i.name, i.id",
        (cell_id,),
    ).fetchall()
    net_of = {
        str(nid): str(nname)
        for (nid, nname) in conn.execute("SELECT id, name FROM net WHERE cell_id = ?", (cell_id,))
    }
    pins_of: dict[str, dict[str, str | None]] = {}
    for iid, pname, pnet in conn.execute(
        "SELECT p.instance_id, p.name, p.net_id FROM port p"
        " WHERE p.instance_id IN (SELECT id FROM instance WHERE cell_id = ?)",
        (cell_id,),
    ).fetchall():
        pins_of.setdefault(str(iid), {})[str(pname)] = (
            net_of.get(str(pnet)) if pnet is not None else None
        )
    params_of: dict[str, dict[str, float]] = {}
    for iid, iname, pname, pvalue in conn.execute(
        "SELECT p.instance_id, i.name, p.name, p.value FROM parameter p"
        " JOIN instance i ON i.id = p.instance_id WHERE i.cell_id = ?",
        (cell_id,),
    ).fetchall():
        params_of.setdefault(str(iid), {})[str(pname)] = _si_float(
            pvalue, str(iname), str(pname)
        )
    lines = [f"* cell {cell_name}"]
    for iid, iname, sname in instances:
        model, pins = _binding(conn, technology_id, str(sname))
        hooked = pins_of.get(str(iid), {})
        nodes: list[str] = []
        for pin in pins:
            if pin not in hooked:
                raise CompilerError(f"Netlist: {iname!r} terminal {pin!r} has no port row")
            node = hooked[pin]
            if node is None:
                raise CompilerError(f"Netlist: {iname!r} terminal {pin!r} is unconnected")
            nodes.append(node)
        extra = sorted(set(hooked) - set(pins))
        if extra:
            raise CompilerError(f"Netlist: {iname!r} terminals {extra} not in pin_order")
        params = params_of.get(str(iid), {})
        attrs = "".join(f" {k}={params[k]!r}" for k in sorted(params))
        lines.append(f"M{iname} {' '.join(nodes)} {model}{attrs}")
    lines.append(".end")
    return "\n".join(lines) + "\n"
