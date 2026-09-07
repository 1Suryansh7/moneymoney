"""Stage 3 Commit 3H tests: input-offset extraction.

Pure-function unit tests run on base image with zero skips.
Live differential verification on `diff_pair_nmos` runs under `@NEEDS_LIB`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from analog_ic_design.circuit import compile_netlist, validate
from analog_ic_design.metrics.contract import OFFSET
from analog_ic_design.metrics.offset import extract_offset
from analog_ic_design.sim.diff_pair import build_diff_pair
from analog_ic_design.sim.ngspice import SimError, libngspice_available, run_deck
from analog_ic_design.sim.testbench import assemble_dc_sweep
from analog_ic_design.store import connect, migrate

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
VCM = 0.9


def _sweep_offset(tmp_path: Path, tag: str, w1: float, w2: float) -> float:
    """Build fixture, sweep inp around VCM, return extracted Vos."""
    db = str(tmp_path / f"os_{tag}.sqlite")
    conn = connect(db)
    migrate(conn)
    cell = build_diff_pair(conn, w1=w1, w2=w2)
    report = validate(conn, cell)
    assert report.valid, [v.message for v in report.violations]
    frag = compile_netlist(conn, cell)
    conn.close()
    deck = assemble_dc_sweep(
        frag,
        sweep_net="inp",
        v_start=0.7,
        v_stop=1.1,
        v_step=0.002,
        extra_lines=[f"Vinn inn 0 DC {VCM}", "Vbias vbias 0 DC 0.9"],
        libs=[(SKY130_LIB, "tt")],
    )
    raw = run_deck(lines=deck.splitlines())
    return extract_offset(
        raw.vectors["inp"],
        raw.vectors["inn"],
        raw.vectors["outp"],
        raw.vectors["outn"],
    )


def test_offset_exact_crossing() -> None:
    # Vod = 10 * (Vid - 0.003): zero at Vid = 3 mV.
    vid = [-0.01 + 0.001 * i for i in range(21)]
    inp = [VCM + v for v in vid]
    inn = [VCM] * 21
    outp = [10.0 * (v - 0.003) for v in vid]
    outn = [0.0] * 21
    assert abs(extract_offset(inp, inn, outp, outn) - 0.003) < 1e-12


def test_offset_contract_bound() -> None:
    assert OFFSET.metric_id == "offset"
    assert OFFSET.units == "V"
    assert OFFSET.required_analysis == "dc"


def test_offset_input_validation() -> None:
    with pytest.raises(SimError, match="ragged"):
        extract_offset([0.0], [0.0], [0.0], [0.0, 1.0])
    with pytest.raises(SimError, match="fewer than 2 points"):
        extract_offset([0.0], [0.0], [0.0], [0.0])
    with pytest.raises(SimError, match="non-finite"):
        extract_offset([0.0, 1.0], [0.0, 0.0], [0.0, float("nan")], [0.0, 0.0])
    with pytest.raises(SimError, match="not strictly monotonic"):
        extract_offset([0.0, 1.0, 0.5], [0.0, 0.0, 0.0], [1.0, 0.5, 0.0], [0.0, 0.0, 0.0])
    with pytest.raises(SimError, match="never crosses zero"):
        extract_offset([0.0, 1.0], [0.0, 0.0], [1.0, 2.0], [0.0, 0.0])


@NEEDS_LIB
def test_diff_pair_offset_live(tmp_path: Path) -> None:
    # Symmetric geometry: systematic offset at the numerical floor.
    vos_sym = _sweep_offset(tmp_path, "sym", 1e-06, 1e-06)
    assert abs(vos_sym) < 1e-3
    # 2:1 input mismatch: nonzero offset, negative sign (larger M1 sinks
    # more at Vid=0, pulling Vod negative; probed live).
    vos_mm = _sweep_offset(tmp_path, "mm", 2e-06, 1e-06)
    assert -0.5 < vos_mm < -0.01
