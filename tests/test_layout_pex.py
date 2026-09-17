"""Stage 9 PEX tests: coupled parasitics from drawn geometry.

Base (pure): suffix goldens, per-net budget math, fail-closed
rejections. EDA (live): emit -> Magic coupled extraction -> parse, then
the scaling proof — a 2×-wider device carries strictly more extracted
capacitance on its signal nets. Per-net totals are conservative budgets
(full value on both terminals, documented in `layout/pex.py`).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from analog_ic_design.layout.pcells import LAYERS, PIN_LAYERS, mos_labels, nmos_rects
from analog_ic_design.layout.pex import (
    parse_capacitance_farads,
    per_net_capacitance,
    to_schematic_subckt,
)
from analog_ic_design.sim.ngspice import SimError

EMIT = Path(__file__).resolve().parent.parent / "scripts" / "layout_pcell_emit.py"
PEX_TCL = Path(__file__).resolve().parent.parent / "scripts" / "magic_pex.tcl"
SKY130_TECH = "/usr/local/share/pdk/sky130A/libs.tech/magic/sky130A.tech"

NEEDS_PEX_TOOLS = pytest.mark.skipif(
    shutil.which("klayout") is None
    or shutil.which("magic") is None
    or not Path(SKY130_TECH).is_file(),
    reason="layout toolchain absent (base image); covered by CI eda job",
)

_SYNTH = """\
* extracted smoke
X0 drain gate source SUB sky130_fd_pr__nfet_01v8 w=200 l=30
C0 gate drain 0.01646f
C1 source drain 0.08438f
C6 drain SUB 0.15801f
"""


def test_suffix_goldens() -> None:
    assert parse_capacitance_farads("0.01646f") == pytest.approx(1.646e-17)
    assert parse_capacitance_farads("2.0p") == pytest.approx(2.0e-12)
    assert parse_capacitance_farads("1.5") == pytest.approx(1.5)
    assert parse_capacitance_farads("3k") == pytest.approx(3000.0)
    assert parse_capacitance_farads("1meg") == pytest.approx(1e6)


def test_per_net_budget_math() -> None:
    totals = per_net_capacitance(_SYNTH)
    # Full value on both terminals: gate sees C0 only.
    assert totals["gate"] == pytest.approx(1.646e-17)
    assert totals["drain"] == pytest.approx(1.646e-17 + 8.438e-17 + 1.5801e-16)
    assert totals["source"] == pytest.approx(8.438e-17)
    assert totals["SUB"] == pytest.approx(1.5801e-16)


def test_parser_rejects() -> None:
    with pytest.raises(SimError, match="unparsable"):
        parse_capacitance_farads("abc")
    with pytest.raises(SimError, match="suffix"):
        parse_capacitance_farads("1.0x")
    with pytest.raises(SimError, match="non-physical"):
        parse_capacitance_farads("-1.0f")
    with pytest.raises(SimError, match="no capacitors"):
        per_net_capacitance("* empty\nX0 a b c d model\n")


_EXT_DEV = """\
* SPICE3 file created from pcell_nmos.ext - technology: sky130A
.option scale=5m
X0 drain gate source SUB sky130_fd_pr__nfet_01v8 ad=22.8n pd=0.628m as=22.8n ps=0.628m w=200 l=30
C0 gate drain 0.01646f
"""


def _param(subckt: str, name: str) -> float:
    match = re.search(rf"(?:^|\s){name}=([0-9.eE+-]+)", subckt)
    assert match is not None
    return float(match.group(1))


def test_to_schematic_subckt_si_roundtrip() -> None:
    subckt = to_schematic_subckt(_EXT_DEV, subckt_name="pex_nmos")
    assert subckt.startswith(".subckt pex_nmos drain gate source SUB\n")
    assert subckt.endswith(".ends\n")
    assert ".option" not in subckt
    assert _param(subckt, "w") == pytest.approx(1e-6)
    assert _param(subckt, "l") == pytest.approx(150e-9)
    assert _param(subckt, "ad") == pytest.approx(22.8e-9 * 25e-18)
    assert _param(subckt, "pd") == pytest.approx(0.628e-3 * 5e-9)
    # Capacitors pass through untouched (already absolute Farads).
    assert "C0 gate drain 0.01646f" in subckt


def test_to_schematic_subckt_rejects() -> None:
    with pytest.raises(SimError, match="non-empty"):
        to_schematic_subckt(_EXT_DEV, subckt_name="  ")
    with pytest.raises(SimError, match="exactly one device"):
        to_schematic_subckt("* nothing here\n", subckt_name="pex_nmos")


def _pex_spice_path(workdir: Path, w_m: float) -> Path:
    """Emit + coupled-extract one device; return the ext SPICE path."""
    workdir.mkdir(parents=True, exist_ok=True)
    rects = nmos_rects(w_m=w_m, l_m=0.15e-6, fingers=1)
    labels = mos_labels(w_m=w_m, l_m=0.15e-6, fingers=1)
    spec = {
        "layers": {name: list(lv) for name, lv in LAYERS.items()},
        "pin_layers": {name: list(lv) for name, lv in PIN_LAYERS.items()},
        "rects": {name: [list(r) for r in boxes] for name, boxes in rects.items()},
        "labels": [list(label) for label in labels],
    }
    (workdir / "rects.json").write_text(json.dumps(spec), encoding="utf-8")
    emit = subprocess.run(
        ["klayout", "-b", "-r", str(EMIT)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=workdir,
    )
    assert emit.returncode == 0, emit.stderr[-2000:]
    magic = subprocess.run(
        ["magic", "-dnull", "-noconsole", "-T", SKY130_TECH],
        input=PEX_TCL.read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        timeout=600,
        cwd=workdir,
    )
    assert magic.returncode == 0, magic.stderr[-2000:]
    spice = workdir / "pcell_nmos.spice"
    assert spice.is_file()
    return spice


def _extract_totals(tmp_path: Path, w_m: float) -> dict[str, float]:
    spice = _pex_spice_path(tmp_path, w_m)
    return per_net_capacitance(spice.read_text(encoding="utf-8"))


def _extract_spice(tmp_path: Path) -> str:
    """Raw ext SPICE text for the canonical W=1 device (closed-loop input)."""
    return _pex_spice_path(tmp_path, 1e-6).read_text(encoding="utf-8")


@NEEDS_PEX_TOOLS
def test_pex_totals_scale_with_width(tmp_path: Path) -> None:
    narrow = _extract_totals(tmp_path / "w1", w_m=1e-6)
    wide = _extract_totals(tmp_path / "w2", w_m=2e-6)
    for net in ("drain", "gate", "source"):
        assert narrow[net] > 0.0
        assert wide[net] > narrow[net]
        assert wide[net] / narrow[net] < 4.0


@NEEDS_PEX_TOOLS
def test_postlayout_degrades_ugb_with_dc_control(tmp_path: Path) -> None:
    """Closed loop: extracted-SI M1 in the B3 CS fixture vs schematic M1.

    DC gain must agree (caps don't move DC — control); UGB must drop
    (layout caps load the output — headline). Declared 2fF AC load puts
    the pole in-sweep; unloaded it sits past 10GHz on both (measured).
    """
    import json

    from analog_ic_design.engine.engine_v01 import EngineV01
    from analog_ic_design.metrics.bandwidth import extract_bandwidth
    from analog_ic_design.metrics.gain import extract_ac_gain, extract_dc_gain
    from analog_ic_design.sim.cs_amp import build_cs_amplifier
    from analog_ic_design.sim.ngspice import RawSim
    from analog_ic_design.sim.testbench import assemble_ac, assemble_dc_sweep
    from analog_ic_design.sim.waveform import parse_ac
    from analog_ic_design.store.schema import connect, migrate

    lib = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
    extra = ["Vbias vbias 0 DC 0.9"]

    db = str(tmp_path / "prepost.sqlite")
    setup = connect(db)
    try:
        migrate(setup)
        cell = build_cs_amplifier(setup)
    finally:
        setup.close()
    eng = EngineV01(db_path=db)
    try:
        frag = eng.netlist(cell_id=cell)

        def characterize(deck_frag: str) -> tuple[float, float, float]:
            eng.simulate(
                netlist=assemble_dc_sweep(
                    deck_frag, sweep_net="in", v_start=0.4, v_stop=1.2,
                    v_step=0.005, extra_lines=extra, libs=[(lib, "tt")],
                ),
                seed=21,
            )
            jobs = eng.list_jobs()
            vecs = json.loads(
                str(eng.job_result(job_id=jobs[0]["job_id"])["result"]
            ))["vectors"]
            vin = [float(v) for v in vecs["in"]]
            vout = [float(v) for v in vecs["out"]]
            dc = extract_dc_gain(vin, vout)
            slopes = [
                abs((vout[i + 1] - vout[i]) / (vin[i + 1] - vin[i]))
                for i in range(len(vin) - 1)
            ]
            trip = vin[slopes.index(max(slopes))]
            eng.simulate(
                netlist=assemble_ac(
                    deck_frag, in_net="in", v_bias=trip,
                    extra_lines=extra + ["Cload2 out 0 2f"], libs=[(lib, "tt")],
                ),
                seed=21,
            )
            jobs = eng.list_jobs()
            payload = json.loads(
                str(eng.job_result(job_id=jobs[0]["job_id"])["result"])
            )
            cx = {
                k: [complex(p[0], p[1]) for p in v]
                for k, v in payload.get("complex_vectors", {}).items()
            }
            wave = parse_ac(
                RawSim(vectors=payload["vectors"], complex_vectors=cx, log="")
            )
            ac = extract_ac_gain(wave, in_node="in", out_node="out")
            ugb = extract_bandwidth(wave, in_node="in", out_node="out")
            return dc, ac, ugb

        pre = characterize(frag)
        ext = _extract_spice(tmp_path)
        sub = to_schematic_subckt(ext, subckt_name="pex_nmos")
        lines = frag.splitlines()
        m1 = next(text for text in lines[1:] if re.match(r"^Xm1\s", text))
        nets = m1.split()[1:5]
        body = [
            text for text in lines[1:]
            if not re.match(r"^Xm1\s", text) and text.strip().lower() != ".end"
        ]
        post_frag = (
            lines[0] + "\n" + sub + "\n".join(body)
            + "\n" + f"Xpex1 {' '.join(nets)} pex_nmos" + "\n.end\n"
        )
        post = characterize(post_frag)
    finally:
        eng.close()
    # Control: DC (and LF AC) agree — parasitics don't move the bias point.
    assert abs(post[0] - pre[0]) / pre[0] < 0.05
    assert abs(post[1] - pre[1]) / pre[1] < 0.05
    # Headline: layout caps cost UGB (measured 12.6% at 2fF declared load).
    assert 0.05 < (pre[2] - post[2]) / pre[2] < 0.30
