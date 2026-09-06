"""Stage 3 Commit 3D tests: unity-gain bandwidth extraction.

Pure-function unit tests run on base image with zero skips.
Live small-signal verification on `cs_amp_nmos` (declared 1 pF load)
runs under `@NEEDS_LIB`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from analog_ic_design.circuit import compile_netlist, validate
from analog_ic_design.metrics.bandwidth import extract_bandwidth
from analog_ic_design.metrics.contract import BANDWIDTH
from analog_ic_design.sim.cs_amp import build_cs_amplifier
from analog_ic_design.sim.ngspice import RawSim, SimError, libngspice_available, run_deck
from analog_ic_design.sim.testbench import assemble_ac, assemble_dc_sweep
from analog_ic_design.sim.waveform import ACTrace, ACWaveform, parse_ac
from analog_ic_design.store import connect, migrate
from analog_ic_design.units.quantity import Hertz

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"


def _ac_wave(freqs: list[float], gains: list[float]) -> ACWaveform:
    """Synthetic AC response: unit input, real-valued output = gain."""
    return parse_ac(
        RawSim(
            vectors={"frequency": list(freqs)},
            complex_vectors={
                "in": [1.0 + 0j for _ in freqs],
                "out": [complex(g, 0.0) for g in gains],
            },
        )
    )


def test_bandwidth_exact_crossing() -> None:
    # Linear interpolation between (1 MHz, 2.0) and (2 MHz, 0.5):
    # f = 1e6 + (1 - 2) / (0.5 - 2) * 1e6 = 1.6666667e6.
    bw = extract_bandwidth(_ac_wave([1e6, 2e6], [2.0, 0.5]))
    assert abs(bw - 1.6666667e6) < 1.0


def test_bandwidth_first_downward_crossing_wins() -> None:
    # Later re-crossings are ignored: crossing between idx 1 and 2.
    bw = extract_bandwidth(_ac_wave([1e6, 2e6, 3e6, 4e6, 5e6], [3.0, 2.0, 0.5, 2.0, 0.25]))
    assert abs(bw - 2.6666667e6) < 1.0


def test_bandwidth_contract_bound() -> None:
    assert BANDWIDTH.metric_id == "bandwidth"
    assert BANDWIDTH.units == "Hz"
    assert BANDWIDTH.required_analysis == "ac"
    assert BANDWIDTH.crossing_rule is not None and "1.0" in BANDWIDTH.crossing_rule


def test_bandwidth_input_validation() -> None:
    with pytest.raises(SimError, match="starts below unity"):
        extract_bandwidth(_ac_wave([1e6, 2e6], [0.5, 0.25]))
    with pytest.raises(SimError, match="never crosses unity"):
        extract_bandwidth(_ac_wave([1e6, 2e6], [2.0, 3.0]))
    with pytest.raises(SimError, match="empty frequency"):
        extract_bandwidth(parse_ac(RawSim(vectors={"frequency": []}, complex_vectors={})))
    with pytest.raises(SimError, match="not strictly increasing"):
        extract_bandwidth(_ac_wave([2e6, 1e6], [2.0, 0.5]))
    with pytest.raises(SimError, match="non-finite"):
        extract_bandwidth(_ac_wave([1e6, 2e6], [2.0, float("nan")]))
    with pytest.raises(SimError, match="not positive"):
        raw = RawSim(
            vectors={"frequency": [1e6, 2e6]},
            complex_vectors={"in": [0.0 + 0j, 1.0 + 0j], "out": [2.0 + 0j, 0.5 + 0j]},
        )
        extract_bandwidth(parse_ac(raw))
    ragged = ACWaveform(
        frequency=(Hertz(1e6),),
        traces=(
            ACTrace(name="in", values=(1.0 + 0j, 1.0 + 0j)),
            ACTrace(name="out", values=(2.0 + 0j,)),
        ),
    )
    with pytest.raises(SimError, match="ragged"):
        extract_bandwidth(ragged)


@NEEDS_LIB
def test_cs_amp_bandwidth_live(tmp_path: Path) -> None:
    db = str(tmp_path / "bw.sqlite")
    conn = connect(db)
    migrate(conn)
    cell = build_cs_amplifier(conn)
    report = validate(conn, cell)
    assert report.valid, [v.message for v in report.violations]
    frag = compile_netlist(conn, cell)
    conn.close()

    # Operating-point bias at maximum DC slope (same discovery as gain test).
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
    vin, vout = raw_dc.vectors["in"], raw_dc.vectors["out"]
    slopes = [abs((vout[i + 1] - vout[i]) / (vin[i + 1] - vin[i])) for i in range(len(vin) - 1)]
    v_bias = vin[slopes.index(max(slopes))]

    # Declared 1 pF output load: the unloaded fixture pole sits beyond the
    # sweep (near-zero diffusion area), so bandwidth is only defined loaded.
    ac_deck = assemble_ac(
        frag,
        in_net="in",
        v_bias=v_bias,
        ac_mag=1.0,
        f_start=1.0,
        f_stop=1e10,
        points_per_decade=10,
        extra_lines=["Vbias vbias 0 DC 0.9", "Cload out 0 1p"],
        libs=[(SKY130_LIB, "tt")],
    )
    wave = parse_ac(run_deck(lines=ac_deck.splitlines()))
    bw = extract_bandwidth(wave)
    assert isinstance(bw, float) and bw > 0.0
    # Plausibility window for a 130 nm common-source stage under 1 pF load
    # (observed 2.07e7 Hz; 20x margin each side).
    assert 1e6 < bw < 1e9
