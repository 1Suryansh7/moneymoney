"""Electrical connectivity graph (Stage 1 Commit 1C).

Builds an immutable in-memory graph FROM the 1B structural tables for one
cell: nets as nodes, instance/cell ports as terminals attached to nets.
No schema change, no simulation, no judgment — this module reports FACTS
(degrees, hookups, unconnected ports). The Stage 1F validator decides what
is a violation (floating net, short, missing bulk tie) using these facts.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


class GraphError(ValueError):
    """Connectivity cannot be built or queried. Failure taxonomy: Schema."""


@dataclass(frozen=True)
class PortRef:
    """One terminal: a cell interface port (`instance_id` None) or an
    instance terminal (`cell_id` None). `net_id` None means unhooked."""

    id: str
    name: str
    cell_id: str | None
    instance_id: str | None
    instance_name: str | None
    net_id: str | None


@dataclass(frozen=True)
class NetNode:
    """One net with its attached terminals (possibly zero)."""

    id: str
    name: str
    ports: tuple[PortRef, ...]


@dataclass(frozen=True)
class ConnectivityGraph:
    """Immutable connectivity snapshot for one cell."""

    cell_id: str
    nets: tuple[NetNode, ...]
    loose_ports: tuple[PortRef, ...] = ()

    def net_ids(self) -> tuple[str, ...]:
        """Ids of all nets in the cell."""
        return tuple(n.id for n in self.nets)

    def ports_on(self, net_id: str) -> tuple[PortRef, ...]:
        """Terminals attached to `net_id`; `GraphError` if unknown."""
        for net in self.nets:
            if net.id == net_id:
                return net.ports
        raise GraphError(f"Schema: unknown net {net_id!r} in cell {self.cell_id!r}")

    def degree(self, net_id: str) -> int:
        """Number of terminals attached to `net_id`."""
        return len(self.ports_on(net_id))

    def unconnected_ports(self) -> tuple[PortRef, ...]:
        """All cell and instance ports with no net (hookup omissions)."""
        return self.loose_ports

    def sparse_nets(self, minimum: int = 2) -> tuple[NetNode, ...]:
        """Nets with fewer than `minimum` terminals (floating/dangling facts)."""
        return tuple(n for n in self.nets if len(n.ports) < minimum)


def build_graph(conn: sqlite3.Connection, cell_id: str) -> ConnectivityGraph:
    """Read 1B rows for `cell_id` into a `ConnectivityGraph`.

    Raises `GraphError` if the cell does not exist. Ports with `net_id`
    NULL are returned by `unconnected_ports`, never silently dropped.
    """
    row = conn.execute("SELECT id FROM cell WHERE id = ?", (cell_id,)).fetchone()
    if row is None:
        raise GraphError(f"Schema: unknown cell {cell_id!r}")
    net_rows = conn.execute(
        "SELECT id, name FROM net WHERE cell_id = ? ORDER BY id", (cell_id,)
    ).fetchall()
    port_rows = conn.execute(
        """
        SELECT p.id, p.name, p.cell_id, p.instance_id, i.name, p.net_id
        FROM port p LEFT JOIN instance i ON i.id = p.instance_id
        WHERE p.cell_id = ? OR p.instance_id IN (SELECT id FROM instance WHERE cell_id = ?)
        ORDER BY p.id
        """,
        (cell_id, cell_id),
    ).fetchall()
    by_net: dict[str | None, list[PortRef]] = {}
    for pid, pname, pcid, piid, piname, pnet in port_rows:
        by_net.setdefault(pnet, []).append(
            PortRef(id=pid, name=pname, cell_id=pcid, instance_id=piid,
                    instance_name=piname, net_id=pnet)
        )
    nets = tuple(
        NetNode(id=nid, name=nname, ports=tuple(by_net.get(nid, ())))
        for nid, nname in net_rows
    )
    return ConnectivityGraph(cell_id=cell_id, nets=nets, loose_ports=tuple(by_net.get(None, ())))
