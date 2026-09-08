"""Stage 3 Commit 3E tests: phase-margin extraction from loop gain.

Pure-function unit tests run on base image with zero skips.
Live Tian loop-gain verification on `cs_amp_nmos` (declared 1 pF load)
runs under `@NEEDS_LIB`.
"""

from __future__ import annotations

import cmath
import math
from pathlib import Path

import pytest

from analog_ic_design.circuit import compile_netlist, validate
from analog_ic_design.metrics.contract import PHASE_MARGIN
from analog_ic_design.metrics.phase_margin import (
    StabilityClassification,
    classify_stability,
    extract_phase_margin,
    extract_phase_margin_detailed,
    unwrap_phase_degrees,
)
from analog_ic_design.sim.cs_amp import build_cs_amplifier
from analog_ic_design.sim.ngspice import RawSim, SimError, libngspice_available, run_deck
from analog_ic_design.sim.testbench import assemble_dc_sweep, assemble_loop_gain
from analog_ic_design.sim.waveform import ACTrace, ACWaveform, parse_ac
from analog_ic_design.store import connect, migrate
from analog_ic_design.units.quantity import Hertz

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"


def _loop_wave(freqs: list[float], ratios: list[complex]) -> ACWaveform:
    """Synthetic Tian response: unit injection, complex loop ratio on out."""
    return parse_ac(
        RawSim(
            vectors={"frequency": list(freqs)},
            complex_vectors={
                "in": [1.0 + 0j for _ in freqs],
                "out": list(ratios),
            },
        )
    )


def _rect(mag: float, deg: float) -> complex:
    """Phasor helper: exact principal-value construction for synthetic waves."""
    return cmath.rect(mag, math.radians(deg))


def test_phase_margin_negative_real_unity_reports_full_margin() -> None:
    # Ratios pinned on the negative-real axis (-2.0 -> -0.5): zero lag
    # accumulated from the DC phasor, so PM = 180. Under the M = G(s)
    # convention this is NOT oscillation (classical loop gain is +2 -> +0.5,
    # positive-real, never near -1). The old expectation 0.0 came from
    # 180 - |180| and is corrected here per VERIFY-PM-001 / ADR-027.
    pm = extract_phase_margin(_loop_wave([1e6, 2e6], [-2.0 + 0j, -0.5 + 0j]))
    assert abs(pm - 180.0) < 1e-6


def test_phase_margin_interpolated_signed() -> None:
    # Crossing at f=1.6667e6, unwrapped phase 180 -> 120 (lag 60 from DC):
    # PM = 180 - 60 = 120 (STABLE). The old expectation 60.0 came from
    # 180 - |120|; corrected per VERIFY-PM-001 / ADR-027.
    pm = extract_phase_margin(_loop_wave([1e6, 2e6], [-2.0 + 0j, 0.5j]))
    assert abs(pm - 120.0) < 1e-6


def test_phase_margin_single_pole_stable() -> None:
    # No wrap on this deck: unwrapped [180, 120, 103.33], lag 76.67.
    # Old and new formulas agree here (backward-compat proof).
    pm = extract_phase_margin(
        _loop_wave(
            [1e6, 2e6, 4e6],
            [-10.0 + 0j, _rect(2.0, 120.0), _rect(0.5, 95.0)],
        )
    )
    assert abs(pm - 103.3333333) < 1e-3


def test_adversarial_wrapped_phase_reports_unstable() -> None:
    # Stage 6F bug replication: true lag 343.64 deg (principal readings
    # [160, 20, -120, +100] wrap past -180). Old code lerped principals
    # (-120 -> +100 through 0) and reported a fake PM = +160.
    # Correct: PM = 180 - 343.6364 = -163.6364, UNSTABLE.
    pm = extract_phase_margin(
        _loop_wave(
            [1e6, 2e6, 4e6, 8e6],
            [
                _rect(8.0, 160.0),
                _rect(4.0, 20.0),
                _rect(1.5, -120.0),
                _rect(0.4, 100.0),
            ],
        )
    )
    assert abs(pm + 163.6363636) < 1e-3
    assert pm < 0.0


def test_branch_cut_bracket_unwraps_continuously() -> None:
    # Principals [-170, +170] must unwrap to [-170, -190] (continuous lag),
    # never lerp through 0 (naive gives PM = 123.33; correct is 166.67).
    pm = extract_phase_margin(
        _loop_wave([1e6, 2e6], [_rect(2.0, -170.0), _rect(0.5, 170.0)])
    )
    assert abs(pm - 166.6666667) < 1e-3


def test_multi_pole_unstable_without_wrap() -> None:
    # No branch crossing, yet lag 266.36 deg at unity: PM = -86.36.
    # Old code returned +83.64 (fake stable) via 180 - |-96.36|.
    pm = extract_phase_margin(
        _loop_wave(
            [1e6, 2e6, 4e6, 8e6],
            [
                _rect(6.0, 170.0),
                _rect(3.0, 60.0),
                _rect(1.5, -60.0),
                _rect(0.4, -140.0),
            ],
        )
    )
    assert abs(pm + 86.3636364) < 1e-3
    assert pm < 0.0


def test_marginal_band_classification() -> None:
    # Lag 142.22 deg at unity: PM = 37.78, MARGINAL (rings, not robust).
    wave = _loop_wave(
        [1e6, 2e6, 4e6],
        [-3.0 + 0j, _rect(1.5, 60.0), _rect(0.6, 20.0)],
    )
    data = extract_phase_margin_detailed(wave)
    assert abs(data.phase_margin_deg - 37.7777778) < 1e-3
    assert data.stability == StabilityClassification.MARGINAL
    assert data.unity_gain_freq_hz > 0.0


def test_detailed_telemetry_and_classification_bounds() -> None:
    stable = extract_phase_margin_detailed(
        _loop_wave([1e6, 2e6], [-2.0 + 0j, 0.5j])
    )
    assert stable.stability == StabilityClassification.STABLE
    assert abs(stable.phase_at_ugb_deg - 120.0) < 1e-6
    assert isinstance(extract_phase_margin(_loop_wave([1e6, 2e6], [-2.0 + 0j, 0.5j])), float)

    assert classify_stability(45.0) == StabilityClassification.STABLE
    assert classify_stability(0.0) == StabilityClassification.MARGINAL
    assert classify_stability(-0.1) == StabilityClassification.UNSTABLE

    assert unwrap_phase_degrees([]) == []
    assert unwrap_phase_degrees([170.0, -170.0]) == [170.0, 190.0]
    assert unwrap_phase_degrees([-170.0, 170.0]) == [-170.0, -190.0]
    assert unwrap_phase_degrees([10.0, 20.0, 30.0]) == [10.0, 20.0, 30.0]


def test_phase_margin_contract_bound() -> None:
    assert PHASE_MARGIN.metric_id == "phase_margin"
    assert PHASE_MARGIN.units == "deg"
    assert PHASE_MARGIN.required_analysis == "ac"
    assert PHASE_MARGIN.crossing_rule is not None and "1.0" in PHASE_MARGIN.crossing_rule


def test_phase_margin_input_validation() -> None:
    with pytest.raises(SimError, match="starts below unity"):
        extract_phase_margin(_loop_wave([1e6, 2e6], [0.5 + 0j, 0.25 + 0j]))
    with pytest.raises(SimError, match="never crosses unity"):
        extract_phase_margin(_loop_wave([1e6, 2e6], [2.0 + 0j, 3.0 + 0j]))
    with pytest.raises(SimError, match="empty frequency"):
        extract_phase_margin(parse_ac(RawSim(vectors={"frequency": []}, complex_vectors={})))
    with pytest.raises(SimError, match="not strictly increasing"):
        extract_phase_margin(_loop_wave([2e6, 1e6], [-2.0 + 0j, -0.5 + 0j]))
    with pytest.raises(SimError, match="non-finite"):
        extract_phase_margin(_loop_wave([1e6, 2e6], [-2.0 + 0j, complex(float("nan"), 0.0)]))
    with pytest.raises(SimError, match="zero loop-injection"):
        raw = RawSim(
            vectors={"frequency": [1e6, 2e6]},
            complex_vectors={"in": [0.0 + 0j, 1.0 + 0j], "out": [-2.0 + 0j, -0.5 + 0j]},
        )
        extract_phase_margin(parse_ac(raw))
    ragged = ACWaveform(
        frequency=(Hertz(1e6),),
        traces=(
            ACTrace(name="in", values=(1.0 + 0j, 1.0 + 0j)),
            ACTrace(name="out", values=(-2.0 + 0j,)),
        ),
    )
    with pytest.raises(SimError, match="ragged"):
        extract_phase_margin(ragged)


@NEEDS_LIB
def test_cs_amp_phase_margin_live(tmp_path: Path) -> None:
    db = str(tmp_path / "pm.sqlite")
    conn = connect(db)
    migrate(conn)
    cell = build_cs_amplifier(conn)
    report = validate(conn, cell)
    assert report.valid, [v.message for v in report.violations]
    frag = compile_netlist(conn, cell)
    conn.close()

    # Declared 1 pF output load: the unloaded loop pole sits beyond the
    # sweep, so phase margin is only defined loaded (bandwidth precedent).
    ac_deck = assemble_loop_gain(
        frag,
        f_start=1.0,
        f_stop=1e10,
        points_per_decade=10,
        extra_lines=["Vbias vbias 0 DC 0.9", "Cload out 0 1p"],
        libs=[(SKY130_LIB, "tt")],
    )
    wave = parse_ac(run_deck(lines=ac_deck.splitlines()))
    pm = extract_phase_margin(wave)
    assert isinstance(pm, float)
    # Dominant-pole loop: near 90 deg, pulled down by higher-order lag.
    assert 45.0 < pm < 135.0

    # Same-operating-point equivalence: loop |M| at f_min must equal the DC
    # transfer slope at the trip point (closed by the 0 V injection source).
    dc_deck = assemble_dc_sweep(
        frag,
        sweep_net="in",
        v_start=0.4,
        v_stop=1.2,
        v_step=0.002,
        extra_lines=["Vbias vbias 0 DC 0.9"],
        libs=[(SKY130_LIB, "tt")],
    )
    raw_dc = run_deck(lines=dc_deck.splitlines())
    vin, vout = raw_dc.vectors["in"], raw_dc.vectors["out"]
    trip = min(range(len(vin)), key=lambda i: abs(vin[i] - vout[i]))
    j = max(1, min(trip, len(vin) - 3))
    trip_slope = abs((vout[j + 2] - vout[j - 1]) / (vin[j + 2] - vin[j - 1]))
    loop_gain_dc = wave.trace("out").magnitude()[0] / wave.trace("in").magnitude()[0]
    assert abs(trip_slope - loop_gain_dc) / trip_slope < 0.05
