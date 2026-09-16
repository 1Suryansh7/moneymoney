"""Stage 9 PEX tests: coupled parasitics from drawn geometry.

Base (pure): suffix goldens, per-net budget math, fail-closed
rejections. EDA (live): emit -> Magic coupled extraction -> parse, then
the scaling proof — a 2×-wider device carries strictly more extracted
capacitance on its signal nets. Per-net totals are conservative budgets
(full value on both terminals, documented in `layout/pex.py`).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from analog_ic_design.layout.pcells import LAYERS, PIN_LAYERS, mos_labels, nmos_rects
from analog_ic_design.layout.pex import parse_capacitance_farads, per_net_capacitance
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


def _extract_totals(tmp_path: Path, w_m: float) -> dict[str, float]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    rects = nmos_rects(w_m=w_m, l_m=0.15e-6, fingers=1)
    labels = mos_labels(w_m=w_m, l_m=0.15e-6, fingers=1)
    spec = {
        "layers": {name: list(lv) for name, lv in LAYERS.items()},
        "pin_layers": {name: list(lv) for name, lv in PIN_LAYERS.items()},
        "rects": {name: [list(r) for r in boxes] for name, boxes in rects.items()},
        "labels": [list(label) for label in labels],
    }
    (tmp_path / "rects.json").write_text(json.dumps(spec), encoding="utf-8")
    emit = subprocess.run(
        ["klayout", "-b", "-r", str(EMIT)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=tmp_path,
    )
    assert emit.returncode == 0, emit.stderr[-2000:]
    magic = subprocess.run(
        ["magic", "-dnull", "-noconsole", "-T", SKY130_TECH],
        input=PEX_TCL.read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        timeout=600,
        cwd=tmp_path,
    )
    assert magic.returncode == 0, magic.stderr[-2000:]
    spice = tmp_path / "pcell_nmos.spice"
    assert spice.is_file()
    return per_net_capacitance(spice.read_text(encoding="utf-8"))


@NEEDS_PEX_TOOLS
def test_pex_totals_scale_with_width(tmp_path: Path) -> None:
    narrow = _extract_totals(tmp_path / "w1", w_m=1e-6)
    wide = _extract_totals(tmp_path / "w2", w_m=2e-6)
    for net in ("drain", "gate", "source"):
        assert narrow[net] > 0.0
        assert wide[net] > narrow[net]
        assert wide[net] / narrow[net] < 4.0
