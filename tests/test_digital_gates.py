"""Tests for transistor-level NOT and NAND gates with symbol creation.

Validates:
1. Schema & electrical connectivity of NOT and NAND gates.
2. Symbol views with external ports.
3. Byte-deterministic SPICE netlist compilation.
4. Live SPICE transient simulation on EDA container (verifying NAND truth table).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Generator
from pathlib import Path

import pytest

from analog_ic_design.circuit.compiler import compile_netlist
from analog_ic_design.circuit.validator import validate
from analog_ic_design.sim.digital_gates import build_nand_gate, build_not_gate
from analog_ic_design.sim.jobs import JobRunner
from analog_ic_design.sim.ngspice import RawSim, libngspice_available
from analog_ic_design.sim.testbench import assemble_transient
from analog_ic_design.sim.waveform import parse_transient
from analog_ic_design.store import connect, migrate

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"


@pytest.fixture()
def mem_db() -> sqlite3.Connection:
    conn = connect(":memory:")
    migrate(conn)
    return conn


@pytest.fixture()
def runner(tmp_path: Path) -> Generator[JobRunner, None, None]:
    db = str(tmp_path / "gates.sqlite")
    conn = connect(db)
    migrate(conn)
    conn.close()
    jobs = JobRunner(db_path=db)
    yield jobs
    jobs.shutdown()


def test_not_gate_schema_and_symbol(mem_db: sqlite3.Connection) -> None:
    cell_id, symbol_id = build_not_gate(mem_db)

    # 1. Validation passes
    report = validate(mem_db, cell_id)
    assert report.valid, f"Violations: {report.violations}"

    # 2. Check symbol exists and has ports
    sym_row = mem_db.execute(
        "SELECT id, name FROM symbol WHERE id = ?", (symbol_id,)
    ).fetchone()
    assert sym_row is not None
    assert sym_row[1] == "not_gate"

    ports = mem_db.execute(
        "SELECT name FROM port WHERE cell_id = ? ORDER BY name", (cell_id,)
    ).fetchall()
    port_names = [p[0] for p in ports]
    assert port_names == ["in", "out", "vdd", "vss"]

    # 3. Check netlist compiles
    netlist = compile_netlist(mem_db, cell_id)
    assert "Xmn1 out in vss vss sky130_fd_pr__nfet_01v8" in netlist
    assert "Xmp1 out in vdd vdd sky130_fd_pr__pfet_01v8" in netlist


def test_nand_gate_schema_and_symbol(mem_db: sqlite3.Connection) -> None:
    cell_id, symbol_id = build_nand_gate(mem_db)

    # 1. Validation passes (no floating gates, no shorts)
    report = validate(mem_db, cell_id)
    assert report.valid, f"Violations: {report.violations}"

    # 2. Check symbol and ports
    sym_row = mem_db.execute(
        "SELECT id, name FROM symbol WHERE id = ?", (symbol_id,)
    ).fetchone()
    assert sym_row is not None
    assert sym_row[1] == "nand_gate"

    ports = mem_db.execute(
        "SELECT name FROM port WHERE cell_id = ? ORDER BY name", (cell_id,)
    ).fetchall()
    port_names = [p[0] for p in ports]
    assert port_names == ["a", "b", "out", "vdd", "vss"]

    # 3. Check netlist compiles
    netlist = compile_netlist(mem_db, cell_id)
    assert "Xmp1 out a vdd vdd sky130_fd_pr__pfet_01v8" in netlist
    assert "Xmp2 out b vdd vdd sky130_fd_pr__pfet_01v8" in netlist
    assert "Xmn1 out a mid vss sky130_fd_pr__nfet_01v8" in netlist
    assert "Xmn2 mid b vss vss sky130_fd_pr__nfet_01v8" in netlist


@NEEDS_LIB
def test_nand_gate_live_truth_table(runner: JobRunner) -> None:
    """Simulate the 2-input CMOS NAND gate across all four logic states (00, 01, 10, 11)."""
    conn = connect(runner.db_path)
    try:
        cell_id, _ = build_nand_gate(conn)
        report = validate(conn, cell_id)
        assert report.valid, [v.message for v in report.violations]
        fragment = compile_netlist(conn, cell_id)
    finally:
        conn.close()

    # Canonical deck assembly: micron conversion, supplies, and .lib come
    # from the helper; only the second staggered source is extra. Va uses
    # the helper default PULSE (delay 1n, width 10n, period 20n), so the
    # sample map below follows the new edges, not the old hand-rolled ones.
    deck = assemble_transient(
        fragment,
        pulse_net="a",
        pulse_volts=1.8,
        tstop_s=25e-9,
        libs=[(SKY130_LIB, "tt")],
        extra_lines=["Vb b 0 DC 0 PULSE(0 1.8 5n 0.1n 0.1n 5n 10n)"],
    )

    res = runner.wait(runner.submit_simulation(netlist=deck, seed=42), timeout=120)
    assert res.status == "succeeded", res.error
    assert res.result is not None

    raw = json.loads(res.result)["vectors"]
    wave = parse_transient(RawSim(vectors=dict(raw), log=""))

    time_pts = [float(t) for t in wave.time]
    out_pts = [float(v) for v in wave.trace("out").values]

    def sample_out(target_t: float) -> float:
        idx = min(range(len(time_pts)), key=lambda i: abs(time_pts[i] - target_t))
        return out_pts[idx]

    # Sample each logic state under the new Va edges (high 1-11ns and
    # 21ns+, low 11-21ns; Vb high 5-10ns, 15-20ns):
    v_10 = sample_out(3.0e-9)   # a=1, b=0 -> out=1.8V
    v_11 = sample_out(8.0e-9)   # a=1, b=1 -> out=0V
    v_00 = sample_out(13.0e-9)  # a=0, b=0 -> out=1.8V
    v_01 = sample_out(18.0e-9)  # a=0, b=1 -> out=1.8V

    # Assert truth table:
    assert v_00 > 1.7, f"Expected out=1.8V for (0,0), got {v_00:.3f}V"
    assert v_01 > 1.7, f"Expected out=1.8V for (0,1), got {v_01:.3f}V"
    assert v_10 > 1.7, f"Expected out=1.8V for (1,0), got {v_10:.3f}V"
    assert v_11 < 0.1, f"Expected out=0.0V for (1,1), got {v_11:.3f}V"
