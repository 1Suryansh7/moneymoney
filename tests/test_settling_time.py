"""Stage 3 Commit 3I tests: settling-time extraction.

Pure-function unit tests run on base image with zero skips.
Live closed-loop step verification on `cs_amp_nmos` runs under `@NEEDS_LIB`.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from analog_ic_design.circuit import compile_netlist, validate
from analog_ic_design.metrics.contract import SETTLING_TIME
from analog_ic_design.metrics.settling_time import extract_settling_time
from analog_ic_design.sim.cs_amp import build_cs_amplifier
from analog_ic_design.sim.ngspice import SimError, libngspice_available, run_deck
from analog_ic_design.sim.testbench import assemble_closed_loop_step
from analog_ic_design.sim.waveform import Trace, Waveform, parse_transient
from analog_ic_design.store import connect, migrate
from analog_ic_design.units.quantity import Second, Volt

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"


def _step_wave(times: list[float], voltages: list[float]) -> Waveform:
    """Helper: typed transient waveform from float lists."""
    return Waveform(
        time=tuple(Second(t) for t in times),
        traces=(Trace(name="out", values=tuple(Volt(v) for v in voltages)),),
    )


def test_settling_time_exponential_exact() -> None:
    # V(t) = 1 - exp(-(t-t0)/tau), t0=1ns, tau=1ns, 1% band:
    # last violation at dt = tau * ln(100) = 4.6052 ns.
    dt, stop = 0.01e-9, 20e-9
    n = int(stop / dt) + 1
    times = [dt * k for k in range(n)]
    voltages = [0.0 if t < 1e-9 else 1.0 - math.exp(-(t - 1e-9) / 1e-9) for t in times]
    ts = extract_settling_time(_step_wave(times, voltages), out_node="out", t0=1e-9)
    assert abs(ts - 4.6052e-9) < 0.02e-9


def test_settling_time_staying_condition() -> None:
    # Mid-window spike after settling pushes t_settle out to the spike.
    dt = 0.1e-9
    times = [dt * k for k in range(101)]
    voltages = [1.0 - math.exp(-max(0.0, t - 1e-9) / 1e-9) if t >= 1e-9 else 0.0 for t in times]
    voltages[80] = 0.5
    ts = extract_settling_time(_step_wave(times, voltages), out_node="out", t0=1e-9)
    assert abs(ts - (8e-9 - 1e-9)) < 1e-12


def test_settling_time_contract_bound() -> None:
    assert SETTLING_TIME.metric_id == "settling_time"
    assert SETTLING_TIME.units == "s"
    assert SETTLING_TIME.required_analysis == "tran"


def test_settling_time_input_validation() -> None:
    wave = _step_wave([0.0, 1e-9, 2e-9], [0.0, 0.5, 1.0])
    with pytest.raises(SimError, match="empty time vector"):
        extract_settling_time(Waveform(time=(), traces=()), out_node="out", t0=0.0)
    with pytest.raises(SimError, match="absent from transient"):
        extract_settling_time(wave, out_node="missing", t0=0.0)
    with pytest.raises(SimError, match="no samples at or after t0"):
        extract_settling_time(wave, out_node="out", t0=5.0)
    with pytest.raises(SimError, match="zero-height step"):
        extract_settling_time(
            _step_wave([0.0, 1e-9], [1.0, 1.0]), out_node="out", t0=0.0
        )
    with pytest.raises(SimError, match="ends outside the error band"):
        tail_dev = [1.0] * 98 + [0.5] * 3
        extract_settling_time(
            _step_wave([1e-9 * k for k in range(101)], tail_dev),
            out_node="out",
            t0=0.0,
        )
    with pytest.raises(SimError, match="not a positive fraction"):
        extract_settling_time(wave, out_node="out", t0=0.0, band=0.0)


@NEEDS_LIB
def test_closed_loop_settling_live(tmp_path: Path) -> None:
    db = str(tmp_path / "st.sqlite")
    conn = connect(db)
    migrate(conn)
    cell = build_cs_amplifier(conn)
    report = validate(conn, cell)
    assert report.valid, [v.message for v in report.violations]
    frag = compile_netlist(conn, cell)
    conn.close()

    # Declared 1 pF output load: unloaded, the step settles through
    # source feedthrough in ~20 ps (no loop dynamics exercised); loaded,
    # the loop exhibits genuine ~ns-scale exponential settling.
    deck = assemble_closed_loop_step(
        frag,
        v_step=0.05,
        t_delay=5e-9,
        t_stop=200e-9,
        extra_lines=["Vbias vbias 0 DC 0.9", "Cload out 0 1p"],
        libs=[(SKY130_LIB, "tt")],
    )
    wave = parse_transient(run_deck(lines=deck.splitlines()))
    ts = extract_settling_time(wave, out_node="out", t0=5e-9)
    assert isinstance(ts, float) and ts > 0.0
    # Loop with ~20 MHz unity-gain frequency settles far inside 200 ns.
    assert ts < 100e-9
