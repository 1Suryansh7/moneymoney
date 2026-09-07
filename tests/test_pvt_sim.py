"""Stage 4.5 Commit 4.5A tests: live PVT corner matrix on cs_amp_nmos.

Runs the validated fixture across FAST_5_CORNER_ENVELOPE (DC bias
discovery + AC UGB per corner), records one `experiment` row per corner,
and asserts the physical monotonicity UGB_FF > UGB_SS.
Runs under `@NEEDS_LIB`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from analog_ic_design.circuit import compile_netlist, validate
from analog_ic_design.metrics.bandwidth import extract_bandwidth
from analog_ic_design.metrics.gain import extract_dc_gain
from analog_ic_design.robust import FAST_5_CORNER_ENVELOPE, Corner
from analog_ic_design.sim.cs_amp import build_cs_amplifier
from analog_ic_design.sim.ngspice import libngspice_available, run_deck
from analog_ic_design.sim.reproduce import design_identity_hash
from analog_ic_design.sim.testbench import assemble_ac, assemble_dc_sweep
from analog_ic_design.sim.waveform import parse_ac
from analog_ic_design.store import connect, migrate, new_id, utcnow_iso

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"


def _corner_ugb(frag: str, corner: Corner) -> tuple[float, float, str]:
    """DC bias discovery + AC UGB at one corner; returns (dc_gain, ugb)."""
    dc_deck = assemble_dc_sweep(
        frag,
        sweep_net="in",
        v_start=0.4,
        v_stop=1.2,
        v_step=0.005,
        extra_lines=["Vbias vbias 0 DC 0.9"],
        libs=[(SKY130_LIB, "tt")],
        corner=corner,
    )
    raw_dc = run_deck(lines=dc_deck.splitlines())
    vin, vout = raw_dc.vectors["in"], raw_dc.vectors["out"]
    dc_gain = extract_dc_gain(vin, vout)
    slopes = [abs((vout[i + 1] - vout[i]) / (vin[i + 1] - vin[i])) for i in range(len(vin) - 1)]
    bias = vin[slopes.index(max(slopes))]
    ac_deck = assemble_ac(
        frag,
        in_net="in",
        v_bias=bias,
        ac_mag=1.0,
        f_start=1.0,
        f_stop=1e10,
        points_per_decade=10,
        extra_lines=["Vbias vbias 0 DC 0.9", "Cload out 0 1p"],
        libs=[(SKY130_LIB, "tt")],
        corner=corner,
    )
    wave = parse_ac(run_deck(lines=ac_deck.splitlines()))
    repro = design_identity_hash(netlist=ac_deck, sim_config={"corner": corner.name})
    return dc_gain, extract_bandwidth(wave), repro


@NEEDS_LIB
def test_pvt_envelope_monotonic_and_recorded(tmp_path: Path) -> None:
    db_path = str(tmp_path / "pvt.sqlite")
    conn = connect(db_path)
    migrate(conn)
    cell = build_cs_amplifier(conn)
    report = validate(conn, cell)
    assert report.valid, [v.message for v in report.violations]
    frag = compile_netlist(conn, cell)
    stamp = utcnow_iso()
    ugbs: dict[str, float] = {}
    for trial, corner in enumerate(FAST_5_CORNER_ENVELOPE):
        dc_gain, ugb, repro = _corner_ugb(frag, corner)
        assert ugb > 0.0
        ugbs[corner.name] = ugb
        jid = new_id()
        conn.execute(
            "INSERT INTO job VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (jid, "characterize", "succeeded",
             json.dumps({"corner": corner.name}, sort_keys=True),
             json.dumps({"dc_gain": dc_gain, "bandwidth": ugb}, sort_keys=True),
             None, stamp, stamp),
        )
        conn.execute(
            "INSERT INTO experiment VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id(), "pvt_envelope", trial, "trial", "succeeded", corner.name,
             json.dumps({"corner": corner.name}, sort_keys=True),
             json.dumps({"dc_gain": dc_gain, "bandwidth": ugb}, sort_keys=True),
             "pass", repro, 0, jid, stamp),
        )
        conn.commit()
        print(f"corner={corner.name} dc_gain={dc_gain:.3f} ugb={ugb:.4e}")
    rows = conn.execute(
        "SELECT DISTINCT corner FROM experiment WHERE study = 'pvt_envelope'"
    ).fetchall()
    assert {r[0] for r in rows} == {c.name for c in FAST_5_CORNER_ENVELOPE}
    ff = next(v for k, v in ugbs.items() if k.startswith("ff_"))
    ss = next(v for k, v in ugbs.items() if k.startswith("ss_"))
    assert ff > ss
    conn.close()
