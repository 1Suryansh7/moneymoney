"""Stage 3 Commit 3G tests: average power extraction.

Pure-function unit tests run on base image with zero skips.
Live supply-power verification on `inverter` runs under `@NEEDS_LIB`.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from analog_ic_design.circuit import compile_netlist, validate
from analog_ic_design.metrics.contract import POWER
from analog_ic_design.metrics.power import extract_power
from analog_ic_design.sim.inverter import build_inverter
from analog_ic_design.sim.ngspice import SimError, libngspice_available, run_deck
from analog_ic_design.sim.testbench import assemble_transient
from analog_ic_design.sim.waveform import Trace, Waveform, parse_transient
from analog_ic_design.store import connect, migrate
from analog_ic_design.units.quantity import Ampere, Second, Volt

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"


def _power_wave(
    times: list[float], vdd: list[float], branch: list[float]
) -> Waveform:
    """Helper: typed transient waveform with supply + branch traces."""
    return Waveform(
        time=tuple(Second(t) for t in times),
        traces=(
            Trace(name="vdd", values=tuple(Volt(v) for v in vdd)),
            Trace(name="vdd#branch", values=tuple(Ampere(i) for i in branch)),
        ),
    )


def test_power_dc_resistive_load_exact() -> None:
    # 1.8 V across an effective 1 kΩ load: P = 1.8 * 1.8e-3 = 3.24e-3 W.
    # Branch current is negative (out of circuit, into the source).
    wave = _power_wave([0.0, 1e-9, 2e-9], [1.8, 1.8, 1.8], [-1.8e-3] * 3)
    assert abs(extract_power(wave) - 3.24e-3) < 1e-12


def test_power_averages_periodic_current() -> None:
    # 1 mA DC + 0.5 mA sine over two full periods: mean is exactly 1 mA.
    n = 41
    times = [1e-9 * k for k in range(n)]
    branch = [-1e-3 + 0.5e-3 * math.sin(2.0 * math.pi * k / 20) for k in range(n)]
    wave = _power_wave(times, [1.8] * n, branch)
    assert abs(extract_power(wave) - 1.8e-3) < 1e-9


def test_power_window_subset() -> None:
    wave = _power_wave([0.0, 1e-9, 2e-9, 3e-9], [1.8] * 4, [-2e-3] * 4)
    assert abs(extract_power(wave, t_start=1e-9, t_end=2e-9) - 3.6e-3) < 1e-12


def test_power_contract_bound() -> None:
    assert POWER.metric_id == "power"
    assert POWER.units == "W"
    assert POWER.required_analysis == "tran"


def test_power_input_validation() -> None:
    wave = _power_wave([0.0, 1e-9], [1.8, 1.8], [-1e-3, -1e-3])
    with pytest.raises(SimError, match="empty time vector"):
        extract_power(Waveform(time=(), traces=()))
    with pytest.raises(SimError, match="absent from transient"):
        extract_power(wave, vdd_node="vcc")
    with pytest.raises(SimError, match="empty integration window"):
        extract_power(wave, t_start=5e-9, t_end=6e-9)
    with pytest.raises(SimError, match="empty integration window"):
        extract_power(wave, t_start=2e-9, t_end=1e-9)
    bad = Waveform(
        time=(Second(0.0), Second(1e-9)),
        traces=(
            Trace(name="vdd", values=(Volt(1.8), float("nan"))),  # type: ignore[arg-type]
            Trace(name="vdd#branch", values=(Ampere(-1e-3), Ampere(-1e-3))),
        ),
    )
    with pytest.raises(SimError, match="non-finite supply sample"):
        extract_power(bad)


@NEEDS_LIB
def test_inverter_power_live(tmp_path: Path) -> None:
    db = str(tmp_path / "pwr.sqlite")
    conn = connect(db)
    migrate(conn)
    cell = build_inverter(conn)
    report = validate(conn, cell)
    assert report.valid, [v.message for v in report.violations]
    frag = compile_netlist(conn, cell)
    conn.close()

    # Five 20 ns periods: average supply power in periodic steady state.
    deck = assemble_transient(
        frag, tstop_s=100e-9, libs=[(SKY130_LIB, "tt")]
    )
    wave = parse_transient(run_deck(lines=deck.splitlines()))
    full = extract_power(wave)
    assert isinstance(full, float) and full > 0.0
    # fF-scale 1.8 V CMOS at 50 MHz dissipates microwatts, not milliwatts.
    assert full < 1e-3
    late = extract_power(wave, t_start=40e-9)
    assert abs(full - late) / full < 0.05
