"""Stage 2 Commit 2H tests: inverter fixture chain (lib-gated execution).

Row-level assembly tests are base-safe; anything executing ngspice needs
the library (explicit skip naming the CI eda gate). Assertions check
electrical CORRECTNESS (inversion, rails) — the same properties the human
verifies visually at the checkpoint.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path

import pytest

from analog_ic_design.circuit import compile_netlist, validate
from analog_ic_design.sim.inverter import build_inverter
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


def test_assemble_exact() -> None:
    deck = assemble_transient(
        "* cell x\nMm1 a b\n.end\n",
        vdd_net="vdd",
        vdd_volts=1.8,
        pulse_net="in",
        pulse_volts=1.8,
        tstop_s=30e-9,
        libs=[(SKY130_LIB, "tt")],
    )
    assert deck == (
        "* cell x\n"
        f".lib '{SKY130_LIB}' tt\n"
        ".param mc_mm_switch=0\n"
        ".option scale=1e-6\n"
        "Mm1 a b\n"
        "VDD vdd 0 DC 1.8\n"
        "VSS vss 0 DC 0\n"
        "Vin in 0 DC 0 PULSE(0 1.8 1n 1n 1n 10n 20n)\n"
        ".tran 0.1n 3e-08\n"
        ".end\n"
    )


def test_assemble_converts_geometry_to_microns() -> None:
    """PDK boundary: SI-meter W/L emit as microns under scale=1e-6."""
    deck = assemble_transient(
        "* cell x\nXm1 out in vss vss sky130_fd_pr__nfet_01v8 L=1.6e-07 W=1e-06\n.end\n",
        libs=[(SKY130_LIB, "tt")],
    )
    assert "Xm1 out in vss vss sky130_fd_pr__nfet_01v8 L=0.16 W=1.0\n" in deck
    assert ".option scale=1e-6\n" in deck
    # Stimulus stays SI: volts/seconds are never micron-scaled.
    assert "VDD vdd 0 DC 1.8\n" in deck
    assert "VSS vss 0 DC 0\n" in deck
    assert ".tran 0.1n 3e-08\n" in deck


def test_assemble_without_end_still_terminates() -> None:
    deck = assemble_transient("* cell x\nMm1 a b\n")
    assert deck.endswith(".end\n")
    assert deck.count(".end") == 1


@pytest.fixture()
def runner(tmp_path: Path) -> Generator[JobRunner, None, None]:
    db = str(tmp_path / "inv.sqlite")
    conn = connect(db)
    migrate(conn)
    conn.close()
    jobs = JobRunner(db_path=db)
    yield jobs
    jobs.shutdown()


def _run_inverter(runner: JobRunner) -> tuple[list[float], list[float]]:
    conn = connect(runner.db_path)
    try:
        cell = build_inverter(conn)
        report = validate(conn, cell)
        assert report.valid, [v.message for v in report.violations]
        deck = assemble_transient(
            compile_netlist(conn, cell), tstop_s=30e-9, libs=[(SKY130_LIB, "tt")]
        )
    finally:
        conn.close()
    result = runner.wait(runner.submit_simulation(netlist=deck, seed=21), timeout=180)
    assert result.status == "succeeded", result.error
    assert result.result is not None
    raw = json.loads(result.result)["vectors"]
    wave = parse_transient(RawSim(vectors=dict(raw), log=""))
    vin = [float(v) for v in wave.trace("in").values]
    vout = [float(v) for v in wave.trace("out").values]
    return vin, vout


@NEEDS_LIB
def test_inverter_inverts_with_rail_swing(runner: JobRunner) -> None:
    vin, vout = _run_inverter(runner)
    assert min(vout) < 0.1
    assert max(vout) > 1.7
    high_in = [o for i, o in zip(vin, vout, strict=True) if i > 1.62]
    low_in = [o for i, o in zip(vin, vout, strict=True) if i < 0.18]
    assert high_in and all(o < 0.18 for o in high_in)
    assert low_in and all(o > 1.62 for o in low_in)


@NEEDS_LIB
def test_inverter_deterministic_across_jobs(runner: JobRunner) -> None:
    assert _run_inverter(runner) == _run_inverter(runner)
