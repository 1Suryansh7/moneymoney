"""Pre-simulation validation gate (Stage 1 Commit 1F) — Law 3, zero bypass.

`validate()` audits one cell across the four gate pillars and returns a
report; NOTHING reaches the compiler or any simulator without a passing
report. Category mapping (the taxonomy has no connectivity/model-binding
entries of their own): structural/model problems -> `schema`; hookup and
compilability problems -> `netlist`. Degree-1 nets are NOT violations:
supplies legitimately fan in off-cell (proven in 1C test data); degree-0
nets and NULL-hooked ports are. Geometry domain rules (W/L at or above the
PDK bin minima in `pdk_limits`, Law-2-grounded ingestion) are enforced here
as `schema` violations; unknown device symbols are unchecked (no invented
limits). Anything else beyond finiteness stays out of the unit layer
(see 1A limits).

`record_errors()` persists a failing report as `error_record` rows —
explicitly, never as a side effect of `validate()` (pure check). Spec
EVALUATION (hard/soft/weighted scoring) is Stage 3 scope; 1F only proves the
specification/constraint tables hold their contract.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass

from analog_ic_design.circuit.graph import build_graph
from analog_ic_design.circuit.pdk_limits import DEVICE_MINIMA, GEOMETRY_PARAMS
from analog_ic_design.store.schema import new_id, utcnow_iso


class ValidationError(ValueError):
    """Validation itself is impossible (e.g. unknown cell). Taxonomy: Schema."""


@dataclass(frozen=True)
class Violation:
    """One gate breach: taxonomy `category` plus a human-actionable message."""

    category: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    """Gate verdict: `valid` iff `violations` is empty."""

    cell_id: str
    valid: bool
    violations: tuple[Violation, ...]


def _v(category: str, message: str) -> Violation:
    return Violation(category=category, message=message)


def validate(conn: sqlite3.Connection, cell_id: str) -> ValidationReport:
    """Audit `cell_id` across schema/connectivity/units/model-binding pillars."""
    row = conn.execute("SELECT name, library_id FROM cell WHERE id = ?", (cell_id,)).fetchone()
    if row is None:
        raise ValidationError(f"Schema: unknown cell {cell_id!r}")
    cell_name = str(row[0])
    found: list[Violation] = []
    if not cell_name:
        found.append(_v("schema", "cell name is empty"))
    project = conn.execute(
        "SELECT l.project_id FROM library l JOIN cell c ON c.library_id = l.id"
        " WHERE c.id = ?",
        (cell_id,),
    ).fetchone()
    project_id = str(project[0]) if project else ""
    tech = conn.execute(
        "SELECT id FROM technology WHERE project_id = ?", (project_id,)
    ).fetchone()
    if tech is None:
        found.append(_v("schema", "project has no technology binding"))
        technology_id = ""
    else:
        technology_id = str(tech[0])
    instances = conn.execute(
        "SELECT i.id, i.name, s.name FROM instance i JOIN symbol s ON s.id = i.symbol_id"
        " WHERE i.cell_id = ?",
        (cell_id,),
    ).fetchall()
    seen: set[str] = set()
    for _iid, iname, _s in instances:
        if not iname:
            found.append(_v("schema", "instance with empty name"))
        if iname in seen:
            found.append(_v("schema", f"duplicate instance name {iname!r}"))
        seen.add(str(iname))
    bindings: dict[str, tuple[str, ...]] = {}
    for _iid, _iname, sname in instances:
        if technology_id and str(sname) not in bindings:
            brow = conn.execute(
                "SELECT pin_order FROM model_binding WHERE technology_id = ? AND device_symbol = ?",
                (technology_id, str(sname)),
            ).fetchone()
            if brow is None:
                found.append(_v("schema", f"no model binding for symbol {str(sname)!r}"))
                bindings[str(sname)] = ()
            else:
                pins = tuple(str(brow[0]).split())
                if not pins:
                    found.append(_v("schema", f"empty pin_order for symbol {str(sname)!r}"))
                bindings[str(sname)] = pins
    graph = build_graph(conn, cell_id)
    hooked: dict[str, dict[str, str | None]] = {}
    for net in graph.nets:
        for port in net.ports:
            if port.instance_id is not None:
                hooked.setdefault(port.instance_id, {})[port.name] = port.net_id
    for iid, iname, sname in instances:
        want = bindings.get(str(sname), ())
        have = hooked.get(str(iid), {})
        for pin in want:
            if pin not in have:
                found.append(_v("netlist", f"{iname!r} terminal {pin!r} has no port row"))
            elif have[pin] is None:
                found.append(_v("netlist", f"{iname!r} terminal {pin!r} is unconnected"))
        for pin in sorted(set(have) - set(want)):
            found.append(_v("netlist", f"{iname!r} terminal {pin!r} not in pin_order"))
    for port in graph.loose_ports:
        # Instance loose ports are already reported per-pin above; only
        # dangling cell-boundary pins remain here.
        if port.instance_id is None:
            found.append(_v("netlist", f"cell port {port.name!r} is unconnected"))
    for net in graph.nets:
        if not net.name:
            found.append(_v("schema", "net with empty name"))
        if len(net.ports) == 0:
            found.append(_v("netlist", f"net {net.name!r} is floating (degree 0)"))
    for iname, pname, pvalue in conn.execute(
        "SELECT i.name, p.name, p.value FROM parameter p"
        " JOIN instance i ON i.id = p.instance_id WHERE i.cell_id = ?",
        (cell_id,),
    ).fetchall():
        if (
            isinstance(pvalue, bool)
            or not isinstance(pvalue, (int, float))
            or not math.isfinite(float(pvalue))
        ):
            found.append(
                _v("schema", f"parameter {pname!r} of {iname!r} is not a finite SI number")
            )
    if technology_id:
        # Convention shared with the compiler: an instance's symbol name
        # resolves to `model_binding.device_symbol` for its technology.
        # Symbols absent from DEVICE_MINIMA are unchecked (no invented limits).
        rows = conn.execute(
            "SELECT i.name, s.name, p.name, p.value FROM parameter p"
            " JOIN instance i ON i.id = p.instance_id"
            " JOIN symbol s ON s.id = i.symbol_id WHERE i.cell_id = ?",
            (cell_id,),
        ).fetchall()
        for iname, sname, pname, pvalue in rows:
            limits = DEVICE_MINIMA.get(str(sname))
            if limits is None:
                continue
            key = str(pname).upper()
            if key not in GEOMETRY_PARAMS:
                continue
            if (
                isinstance(pvalue, bool)
                or not isinstance(pvalue, (int, float))
                or not math.isfinite(float(pvalue))
            ):
                continue  # already reported as non-finite above
            minimum = limits[0] if key == "W" else limits[1]
            if float(pvalue) < minimum:
                found.append(
                    _v(
                        "schema",
                        f"parameter {pname!r} of {iname!r} ({sname}) is"
                        f" {float(pvalue)!r} m below PDK minimum {minimum!r} m",
                    )
                )
    return ValidationReport(cell_id=cell_id, valid=not found, violations=tuple(found))


def record_errors(
    conn: sqlite3.Connection, cell_id: str, report: ValidationReport
) -> tuple[str, ...]:
    """Persist each violation as an `error_record` row; returns the row ids."""
    ids: list[str] = []
    for violation in report.violations:
        eid = new_id()
        conn.execute(
            "INSERT INTO error_record (id, cell_id, category, message, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (eid, cell_id, violation.category, violation.message, utcnow_iso()),
        )
        ids.append(eid)
    conn.commit()
    return tuple(ids)
