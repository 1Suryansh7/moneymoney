"""Stage 3 Commit 3F tests: slew rate extraction.

Pure-function unit tests run on base image with zero skips.
Live step-response verification on `inverter` runs under `@NEEDS_LIB`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from analog_ic_design.circuit import compile_netlist, validate
from analog_ic_design.metrics.contract import SLEW_RATE
from analog_ic_design.metrics.slew_rate import (
    extract_falling_slew_rate,
    extract_rising_slew_rate,
    extract_slew_rate,
)
from analog_ic_design.sim.inverter import build_inverter
from analog_ic_design.sim.ngspice import SimError, libngspice_available, run_deck
from analog_ic_design.sim.testbench import assemble_step_response
from analog_ic_design.sim.waveform import Trace, Waveform, parse_transient
from analog_ic_design.store import connect, migrate
from analog_ic_design.units.quantity import Second, Volt

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"


def _make_transient_wave(times: list[float], voltages: list[float]) -> Waveform:
    """Helper to create a typed Waveform from float lists."""
    return Waveform(
        time=tuple(Second(t) for t in times),
        traces=(Trace(name="out", values=tuple(Volt(v) for v in voltages)),),
    )


def test_slew_rate_contract_bound() -> None:
    assert SLEW_RATE.metric_id == "slew_rate"
    assert SLEW_RATE.units == "V/s"
    assert SLEW_RATE.required_analysis == "tran"
    assert SLEW_RATE.reference_condition is not None and "20%" in SLEW_RATE.reference_condition


def test_slew_rate_exact_rising() -> None:
    # 0 to 1.8 V ramp over 1 ns (slope = 1.8e9 V/s).
    # 20% is at 0.36 V, t = 1.2 ns. 80% is at 1.44 V, t = 1.8 ns.
    # dt = 0.6 ns, dv = 1.08 V -> sr = 1.8e9 V/s.
    t = [0.0, 1e-9, 1.5e-9, 2e-9, 3e-9]
    v = [0.0, 0.0, 0.9, 1.8, 1.8]
    wave = _make_transient_wave(t, v)

    sr_rise = extract_rising_slew_rate(wave, out_node="out")
    assert abs(sr_rise - 1.8e9) < 1e3

    sr = extract_slew_rate(wave, out_node="out", edge="rising")
    assert abs(sr - 1.8e9) < 1e3


def test_slew_rate_exact_falling() -> None:
    # 1.8 to 0 V ramp over 1 ns (slope = 1.8e9 V/s).
    # 80% is at 1.44 V, t = 1.2 ns. 20% is at 0.36 V, t = 1.8 ns.
    # dt = 0.6 ns, dv = 1.08 V -> sr = 1.8e9 V/s.
    t = [0.0, 1e-9, 1.5e-9, 2e-9, 3e-9]
    v = [1.8, 1.8, 0.9, 0.0, 0.0]
    wave = _make_transient_wave(t, v)

    sr_fall = extract_falling_slew_rate(wave, out_node="out")
    assert abs(sr_fall - 1.8e9) < 1e3

    sr = extract_slew_rate(wave, out_node="out", edge="falling")
    assert abs(sr - 1.8e9) < 1e3


def test_slew_rate_both_edges_returns_min() -> None:
    # Fast rise (0.5 ns -> 3.6e9 V/s), slow fall (2.0 ns -> 0.9e9 V/s).
    # Expected min = 0.9e9 V/s.
    t = [0.0, 1e-9, 1.5e-9, 3e-9, 5e-9, 6e-9]
    v = [0.0, 0.0, 1.8, 1.8, 0.0, 0.0]
    wave = _make_transient_wave(t, v)

    sr = extract_slew_rate(wave, out_node="out", edge="both")
    assert abs(sr - 0.9e9) < 1e3


def test_slew_rate_input_validation() -> None:
    # Empty time
    empty_wave = Waveform(time=(), traces=())
    with pytest.raises(SimError, match="empty time vector"):
        extract_slew_rate(empty_wave)

    # Non-monotonic time
    bad_time = Waveform(
        time=(Second(2.0), Second(1.0)),
        traces=(Trace(name="out", values=(Volt(0.0), Volt(1.0))),),
    )
    with pytest.raises(SimError, match="not strictly increasing"):
        extract_slew_rate(bad_time)

    # Missing node
    wave = _make_transient_wave([0.0, 1.0], [0.0, 1.8])
    with pytest.raises(SimError, match="absent from transient"):
        extract_slew_rate(wave, out_node="nonexistent")

    # Swing negligible
    flat_wave = _make_transient_wave([0.0, 1.0, 2.0], [1.0, 1.02, 1.01])
    with pytest.raises(SimError, match="swing negligible"):
        extract_slew_rate(flat_wave)

    # Does not complete transition to 80% of 1.8V step (reaches only 0.5V)
    partial_wave = _make_transient_wave([0.0, 1.0, 2.0], [0.0, 0.5, 0.5])
    with pytest.raises(SimError, match="does not reach 80%"):
        extract_rising_slew_rate(partial_wave, v_start=0.0, v_stop=1.8)



@NEEDS_LIB
def test_inverter_slew_rate_live(tmp_path: Path) -> None:
    db = str(tmp_path / "sr.sqlite")
    conn = connect(db)
    migrate(conn)
    cell = build_inverter(conn)
    report = validate(conn, cell)
    assert report.valid, [v.message for v in report.violations]
    frag = compile_netlist(conn, cell)
    conn.close()

    # Apply fast rail-to-rail step at t=1ns with 10ps edge
    step_deck = assemble_step_response(
        frag,
        v_start=0.0,
        v_stop=1.8,
        t_delay=1e-9,
        t_edge=10e-12,
        t_stop=3e-9,
        t_step=1e-12,
        libs=[(SKY130_LIB, "tt")],
    )
    raw = run_deck(lines=step_deck.splitlines())
    wave = parse_transient(raw)

    # When Vin steps 0 -> 1.8V, Vout falls 1.8 -> 0V
    sr_fall = extract_falling_slew_rate(wave, out_node="out")
    assert isinstance(sr_fall, float) and sr_fall > 0.0

    # Physical sanity for 130 nm CMOS inverter:
    # Unloaded submicron gate switches in single-digit picoseconds:
    # Slew rate in 1e9 to 1e12 V/s range (1 to 1000 V/ns; observed 4.88e11 V/s).
    assert 1e9 < sr_fall < 1e12

    # Loaded test: with declared 50 fF load, slew rate scales predictably
    step_deck_loaded = assemble_step_response(
        frag,
        v_start=0.0,
        v_stop=1.8,
        t_delay=1e-9,
        t_edge=10e-12,
        t_stop=3e-9,
        t_step=1e-12,
        extra_lines=["Cload out 0 50f"],
        libs=[(SKY130_LIB, "tt")],
    )
    wave_loaded = parse_transient(run_deck(lines=step_deck_loaded.splitlines()))
    sr_loaded = extract_falling_slew_rate(wave_loaded, out_node="out")
    # Loaded slew rate must be slower than unloaded due to capacitive charging
    assert sr_loaded < sr_fall
    assert 1e9 < sr_loaded < 1e11

