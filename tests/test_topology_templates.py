"""Tests for Canonical Topology Template Library (Stage 6 Commit 6A).

Verifies:
1. Registry contains all 6 canonical analog topology templates.
2. Instantiation into SQLite creates valid relational IR without orphan references.
3. Strict physical units: strings or non-positive values are rejected.
4. All 6 compiled template circuits pass the pre-simulation validation gate.
5. SPICE netlist compilation produces deterministic text for all 6 templates.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Generator

import pytest

from analog_ic_design.circuit.compiler import compile_netlist
from analog_ic_design.circuit.validator import validate
from analog_ic_design.store.schema import connect, migrate
from analog_ic_design.topology import (
    REGISTERED_TEMPLATES,
    get_template,
    instantiate_template,
    list_templates,
)

EXPECTED_TEMPLATES = {
    "current_mirror",
    "diff_pair",
    "common_source",
    "cascode",
    "folded_cascode",
    "two_stage_miller",
}


@pytest.fixture()
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect()
    migrate(conn)
    yield conn
    conn.close()


def test_template_registry_completeness() -> None:
    assert set(list_templates()) == EXPECTED_TEMPLATES
    assert len(REGISTERED_TEMPLATES) == 6
    for tid in EXPECTED_TEMPLATES:
        t = get_template(tid)
        assert t.template_id == tid
        assert len(t.display_name) > 0
        assert len(t.ports) > 0
        assert len(t.default_parameters) > 0
        assert len(t.tradeoffs.strengths) > 0
        assert len(t.tradeoffs.weaknesses) > 0


def test_template_units_and_type_enforcement(db: sqlite3.Connection) -> None:
    t = get_template("common_source")
    with pytest.raises(ValueError, match="unknown parameter"):
        t.validate_parameters({"bogus": 1.0})
    with pytest.raises(ValueError, match="must be a numeric SI value"):
        t.validate_parameters({"w_n": "1.0u"})  # type: ignore[dict-item]
    with pytest.raises(ValueError, match="must be a numeric SI value"):
        t.validate_parameters({"w_n": True})
    with pytest.raises(ValueError, match="must be positive"):
        t.validate_parameters({"w_n": -1e-6})
    with pytest.raises(ValueError, match="must be positive"):
        t.validate_parameters({"w_n": 0.0})


@pytest.mark.parametrize("template_id", sorted(EXPECTED_TEMPLATES))
def test_all_templates_instantiate_and_pass_validation_gate(
    db: sqlite3.Connection, template_id: str
) -> None:
    cell_id = instantiate_template(db, template_id, cell_name=f"test_{template_id}")
    assert cell_id is not None and len(cell_id) == 32

    # Verify rows exist in SQLite
    inst_count = db.execute(
        "SELECT COUNT(*) FROM instance WHERE cell_id = ?", (cell_id,)
    ).fetchone()[0]
    assert inst_count > 0

    net_count = db.execute("SELECT COUNT(*) FROM net WHERE cell_id = ?", (cell_id,)).fetchone()[0]
    assert net_count > 0

    # Law 3: Zero bypass pre-simulation validation gate
    report = validate(db, cell_id)
    assert report.valid is True, f"Template {template_id} failed validation: {report.violations}"
    assert report.violations == ()


@pytest.mark.parametrize("template_id", sorted(EXPECTED_TEMPLATES))
def test_all_templates_compile_to_deterministic_netlist(
    db: sqlite3.Connection, template_id: str
) -> None:
    cell_id = instantiate_template(db, template_id, cell_name=f"netlist_{template_id}")
    netlist1 = compile_netlist(db, cell_id)
    netlist2 = compile_netlist(db, cell_id)

    # Netlists must be byte-identical
    assert netlist1 == netlist2
    assert netlist1.startswith(f"* cell netlist_{template_id}\n")
    assert netlist1.endswith(".end\n")

    # Transistors must have prefix M or X
    lines = [line for line in netlist1.splitlines() if line and not line.startswith(("*", "."))]
    assert len(lines) > 0
    for line in lines:
        assert line[0] in ("M", "X"), f"Device line must start with M or X: {line}"


def test_two_stage_miller_sizing_knobs_and_connectivity(db: sqlite3.Connection) -> None:
    custom_params = {
        "w_in": 8.0e-06,
        "l_in": 0.5e-06,
        "w_load": 4.0e-06,
        "l_load": 0.5e-06,
        "w_out": 25.0e-06,
        "l_out": 0.5e-06,
        "cc": 1.5e-12,
        "rz": 2000.0,
    }
    cell_id = instantiate_template(
        db, "two_stage_miller", params=custom_params, cell_name="miller_custom"
    )
    report = validate(db, cell_id)
    assert report.valid is True

    # Check that custom parameters reached the parameter table
    w_out_val = db.execute(
        "SELECT p.value FROM parameter p JOIN instance i ON i.id = p.instance_id"
        " WHERE i.cell_id = ? AND i.name = 'm6' AND p.name = 'W'",
        (cell_id,),
    ).fetchone()[0]
    assert float(w_out_val) == pytest.approx(25.0e-06)

    cc_val = db.execute(
        "SELECT p.value FROM parameter p JOIN instance i ON i.id = p.instance_id"
        " WHERE i.cell_id = ? AND i.name = 'cc' AND p.name = 'c'",
        (cell_id,),
    ).fetchone()[0]
    assert float(cc_val) == pytest.approx(1.5e-12)
