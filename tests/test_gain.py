"""Stage 3 Commit 3C tests: DC and AC gain metric contracts and extraction.

Pure-function unit tests run on base image with zero skips.
Live SPICE small-signal verification on `cs_amp_nmos` runs under `@NEEDS_LIB`.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from analog_ic_design.circuit import compile_netlist, validate
from analog_ic_design.metrics.contract import AC_GAIN, DC_GAIN
from analog_ic_design.metrics.gain import extract_ac_gain, extract_ac_gain_db, extract_dc_gain
from analog_ic_design.sim.cs_amp import build_cs_amplifier
from analog_ic_design.sim.ngspice import RawSim, SimError, libngspice_available, run_deck
from analog_ic_design.sim.testbench import assemble_ac, assemble_dc_sweep
from analog_ic_design.sim.waveform import parse_ac
from analog_ic_design.store import connect, migrate

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"


def test_dc_gain_linear_ramp() -> None:
    # y = -5 * x + 1.0 -> |slope| = 5.0
    vin = [0.0, 0.1, 0.2, 0.3, 0.4]
    vout = [1.0, 0.5, 0.0, -0.5, -1.0]
    gain = extract_dc_gain(vin, vout)
    assert abs(gain - 5.0) < 1e-9


def test_dc_gain_sigmoid_peak_slope() -> None:
    # Sigmoid transition centered at vin=0.9
    vin = [0.80 + 0.01 * i for i in range(21)]
    # Steeper transition around 0.90
    vout = [1.8 / (1.0 + math.exp(20.0 * (v - 0.90))) for v in vin]
    gain = extract_dc_gain(vin, vout)
    # Peak analytical derivative of 1.8 / (1 + exp(k(x - x0))) at x=x0 is:
    # 1.8 * k / 4 = 1.8 * 20 / 4 = 9.0
    assert abs(gain - 9.0) < 0.2


def test_dc_gain_input_validation() -> None:
    with pytest.raises(SimError, match="ragged"):
        extract_dc_gain([0.0, 1.0], [1.0])
    with pytest.raises(SimError, match="fewer than 2 points"):
        extract_dc_gain([0.0], [1.0])
    with pytest.raises(SimError, match="non-finite"):
        extract_dc_gain([0.0, 1.0], [0.0, float("nan")])
    with pytest.raises(SimError, match="not strictly monotonic"):
        extract_dc_gain([0.0, 1.0, 0.5], [1.0, 0.5, 0.0])


def test_ac_gain_ideal_complex() -> None:
    # 20 dB gain = 10.0 V/V at f_min
    raw = RawSim(
        vectors={"frequency": [1.0, 10.0]},
        complex_vectors={
            "in": [1.0 + 0j, 1.0 + 0j],
            "out": [0.0 - 10.0j, 0.0 - 8.0j],
        },
    )
    ac = parse_ac(raw)
    gain = extract_ac_gain(ac)
    assert abs(gain - 10.0) < 1e-9
    assert abs(extract_ac_gain_db(ac) - 20.0) < 1e-6


def test_ac_gain_validation() -> None:
    raw_zero_in = RawSim(
        vectors={"frequency": [1.0]},
        complex_vectors={"in": [0.0 + 0j], "out": [1.0 + 0j]},
    )
    with pytest.raises(SimError, match="zero or negative"):
        extract_ac_gain(parse_ac(raw_zero_in))

    raw_non_finite = RawSim(
        vectors={"frequency": [1.0]},
        complex_vectors={"in": [1.0 + 0j], "out": [float("nan") + 0j]},
    )
    with pytest.raises(SimError, match="non-finite"):
        extract_ac_gain(parse_ac(raw_non_finite))


def test_contracts_bound() -> None:
    assert DC_GAIN.metric_id == "dc_gain"
    assert DC_GAIN.units == "V/V"
    assert DC_GAIN.required_analysis == "dc"
    assert AC_GAIN.metric_id == "ac_gain"
    assert AC_GAIN.units == "V/V"
    assert AC_GAIN.required_analysis == "ac"


@NEEDS_LIB
def test_cs_amp_gain_simulation_and_equivalence(tmp_path: Path) -> None:
    db = str(tmp_path / "cs_amp.sqlite")
    conn = connect(db)
    migrate(conn)
    cell = build_cs_amplifier(conn)
    rep = validate(conn, cell)
    assert rep.valid, [v.message for v in rep.violations]
    frag = compile_netlist(conn, cell)
    conn.close()

    # 1. DC transfer sweep
    dc_deck = assemble_dc_sweep(
        frag,
        sweep_net="in",
        v_start=0.4,
        v_stop=1.2,
        v_step=0.005,
        extra_lines=["Vbias vbias 0 DC 0.9"],
        libs=[(SKY130_LIB, "tt")],
    )
    raw_dc = run_deck(lines=dc_deck.splitlines())
    vin = raw_dc.vectors["in"]
    vout = raw_dc.vectors["out"]
    dc_gain = extract_dc_gain(vin, vout)

    assert dc_gain > 5.0  # Common-source active load has Av > 5 V/V
    assert min(vout) < 0.1  # Swings near rail
    assert max(vout) > 1.7

    # Find bias point corresponding to max slope
    slopes = [abs((vout[i + 1] - vout[i]) / (vin[i + 1] - vin[i])) for i in range(len(vin) - 1)]
    max_idx = slopes.index(max(slopes))
    v_in_bias = vin[max_idx]

    # 2. AC small-signal simulation at exact operating point
    ac_deck = assemble_ac(
        frag,
        in_net="in",
        v_bias=v_in_bias,
        ac_mag=1.0,
        f_start=1.0,
        f_stop=1e8,
        points_per_decade=5,
        extra_lines=["Vbias vbias 0 DC 0.9"],
        libs=[(SKY130_LIB, "tt")],
    )
    raw_ac = run_deck(lines=ac_deck.splitlines())
    ac = parse_ac(raw_ac)
    ac_gain = extract_ac_gain(ac)

    # 3. Equivalence: DC small-signal slope == AC low-frequency transfer function
    rel_diff = abs(dc_gain - ac_gain) / dc_gain
    assert rel_diff < 0.05  # Within 5% per MetricContract comparison policy
