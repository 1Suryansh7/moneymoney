"""Deterministic canonicalization (Stage 1 Commit 1D).

Maps one cell's schema rows to a canonical form whose text encoding hashes
stably: same logical circuit (same names, any row order, any opaque ids) →
identical bytes → identical SHA-256. This is the identity half of
`design_identity_hash` (final_build.md section 14.1); the Stage 1E compiler
emits the normalized netlist from the same ordering rules.

Boundaries (read before extending):
- Identity is by NAME (instance/symbol/net/terminal names), never by uuid.
  Cross-session stability therefore assumes unique names — a Stage 1F
  validation rule, enforced there, assumed here.
- Parameters do not exist yet (Stage 1E adds them); the canonical form
  grows additively there, never by editing these lines' semantics.
- Encoding is LF-only, UTF-8, trailing newline. Byte-stability is asserted
  by test, not by convention.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass

from analog_ic_design.circuit.graph import build_graph


@dataclass(frozen=True)
class CanonicalDevice:
    """One instance by name: `name` instantiates template `symbol`."""

    name: str
    symbol: str


@dataclass(frozen=True)
class CanonicalTerminal:
    """One terminal hookup, all by name."""

    instance: str
    terminal: str
    net: str


@dataclass(frozen=True)
class CanonicalCell:
    """Canonical form of one cell: all sequences in sorted order."""

    cell: str
    devices: tuple[CanonicalDevice, ...]
    nets: tuple[str, ...]
    terminals: tuple[CanonicalTerminal, ...]


def canonicalize(conn: sqlite3.Connection, cell_id: str) -> CanonicalCell:
    """Build the canonical form of `cell_id` (names only, sorted).

    Raises `GraphError` if the cell does not exist.
    """
    graph = build_graph(conn, cell_id)
    row = conn.execute("SELECT name FROM cell WHERE id = ?", (cell_id,)).fetchone()
    assert row is not None  # build_graph already proved existence
    devices = tuple(
        sorted(
            (
                CanonicalDevice(name=irow[0], symbol=irow[1])
                for irow in conn.execute(
                    """
                    SELECT i.name, s.name FROM instance i
                    JOIN symbol s ON s.id = i.symbol_id
                    WHERE i.cell_id = ?
                    """,
                    (cell_id,),
                ).fetchall()
            ),
            key=lambda d: (d.name, d.symbol),
        )
    )
    net_names = sorted({n.name for n in graph.nets if n.name})
    by_net_name = {n.name: n.id for n in graph.nets if n.name}
    name_of_net = {nid: name for name, nid in by_net_name.items()}
    terminals = tuple(
        sorted(
            (
                CanonicalTerminal(
                    instance=p.instance_name or "",
                    terminal=p.name,
                    net=name_of_net.get(p.net_id or "", ""),
                )
                for n in graph.nets
                for p in n.ports
                if p.net_id is not None
            ),
            key=lambda t: (t.instance, t.terminal, t.net),
        )
    )
    loose = tuple(
        sorted(
            (
                CanonicalTerminal(instance=p.instance_name or "", terminal=p.name, net="")
                for p in graph.loose_ports
            ),
            key=lambda t: (t.instance, t.terminal),
        )
    )
    return CanonicalCell(
        cell=row[0], devices=devices, nets=tuple(net_names), terminals=terminals + loose
    )


def canonical_encode(cell: CanonicalCell) -> str:
    """Deterministic LF text encoding of the canonical form."""
    lines = [f"cell {cell.cell}"]
    lines += [f"device {d.name} {d.symbol}" for d in cell.devices]
    lines += [f"net {n}" for n in cell.nets]
    lines += [f"terminal {t.instance} {t.terminal} {t.net}".rstrip() for t in cell.terminals]
    return "\n".join(lines) + "\n"


def canonical_hash(cell: CanonicalCell) -> str:
    """SHA-256 hex of the canonical encoding (circuit identity, not a
    comparison policy — tolerances never enter here)."""
    return hashlib.sha256(canonical_encode(cell).encode("utf-8")).hexdigest()
