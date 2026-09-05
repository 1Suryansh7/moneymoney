"""Stage 1 Commit 1C tests: connectivity graph facts.

Builds a two-transistor cell in SQLite and proves the graph reports degrees,
hookups, loose ports, and sparse nets — the facts Stage 1F will judge.
Failure taxonomy: Schema.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator

import pytest

from analog_ic_design.circuit import GraphError, build_graph
from analog_ic_design.store import connect, migrate, new_id

STAMP = "2026-09-05T00:00:00+00:00"
Wired = tuple[sqlite3.Connection, dict[str, str]]


@pytest.fixture()
def wired() -> Generator[Wired, None, None]:
    conn = connect()
    migrate(conn)
    ids = {k: new_id() for k in ("p", "l", "pdk", "amp", "nfet", "sym", "m1", "m2")}
    nets = {k: new_id() for k in ("in", "out", "vdd", "vss", "floaty", "single")}
    conn.execute("INSERT INTO project VALUES (?, ?, ?)", (ids["p"], "demo", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (ids["l"], ids["p"], "lib", STAMP))
    conn.execute("INSERT INTO library VALUES (?, ?, ?, ?)", (ids["pdk"], ids["p"], "pdk", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (ids["amp"], ids["l"], "amp", STAMP))
    conn.execute("INSERT INTO cell VALUES (?, ?, ?, ?)", (ids["nfet"], ids["pdk"], "nfet", STAMP))
    conn.execute("INSERT INTO symbol VALUES (?, ?, ?, ?)", (ids["sym"], ids["nfet"], "nf", STAMP))
    for key in ("m1", "m2"):
        conn.execute(
            "INSERT INTO instance VALUES (?, ?, ?, ?, ?)",
            (ids[key], ids["amp"], ids["sym"], key, STAMP),
        )
    for name in ("in", "out", "vdd", "vss"):
        conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nets[name], ids["amp"], name, STAMP))
        conn.execute(
            "INSERT INTO port VALUES (?, ?, NULL, ?, ?, ?)",
            (new_id(), ids["amp"], nets[name], name, STAMP),
        )
    conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nets["floaty"], ids["amp"], "fl", STAMP))
    conn.execute("INSERT INTO net VALUES (?, ?, ?, ?)", (nets["single"], ids["amp"], "sg", STAMP))
    terms: tuple[tuple[str, str, str | None], ...] = (
        ("m1", "d", "out"),
        ("m1", "g", "in"),
        ("m1", "s", "vss"),
        ("m1", "b", None),
        ("m2", "d", "out"),
        ("m2", "g", "out"),
        ("m2", "s", "vss"),
        ("m2", "b", "single"),
    )
    for inst, term, net in terms:
        conn.execute(
            "INSERT INTO port VALUES (?, NULL, ?, ?, ?, ?)",
            (new_id(), ids[inst], nets[net] if net else None, term, STAMP),
        )
    conn.commit()
    yield conn, {"cell": ids["amp"], **nets}
    conn.close()


def test_graph_reports_degrees(wired: Wired) -> None:
    conn, ids = wired
    graph = build_graph(conn, ids["cell"])
    assert graph.degree(ids["out"]) == 4
    assert graph.degree(ids["vss"]) == 3
    assert graph.degree(ids["in"]) == 2
    assert graph.degree(ids["floaty"]) == 0
    assert graph.degree(ids["single"]) == 1


def test_sparse_nets_and_loose_port(wired: Wired) -> None:
    conn, ids = wired
    graph = build_graph(conn, ids["cell"])
    # NOTE: vdd is degree-1 cell-locally (its supply connects off-cell).
    # Sparseness is a fact; treating supplies as violations is 1F's call.
    assert {n.id for n in graph.sparse_nets()} == {ids["floaty"], ids["single"], ids["vdd"]}
    assert {n.id for n in graph.sparse_nets(minimum=1)} == {ids["floaty"]}
    loose = graph.unconnected_ports()
    assert len(loose) == 1 and loose[0].name == "b" and loose[0].instance_name == "m1"


def test_cell_interface_ports_have_no_instance(wired: Wired) -> None:
    conn, ids = wired
    graph = build_graph(conn, ids["cell"])
    vdd = [p for p in graph.ports_on(ids["vdd"]) if p.instance_id is None]
    assert len(vdd) == 1 and vdd[0].name == "vdd"


def test_unknown_cell_and_net_raise_graph_error(wired: Wired) -> None:
    conn, ids = wired
    with pytest.raises(GraphError):
        build_graph(conn, "no-such-cell")
    graph = build_graph(conn, ids["cell"])
    with pytest.raises(GraphError):
        graph.ports_on("no-such-net")


def test_graph_error_is_value_error() -> None:
    assert issubclass(GraphError, ValueError)
