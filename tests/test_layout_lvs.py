"""Stage 8 LVS closure tests: drawn PCell vs schematic golden (EDA only).

Full loop, all real tools: PCell OASIS (emitter) -> GDS (pya) -> Magic
extract + ext2spice -> Netgen LVS against the 1G NMOS golden fragment
under `sky130A_setup.tcl`. Two pinned claims: (1) extraction
recognizes one nfet with W/L matching the drawn device in Magic lambda
units (w=200 l=30 for W=1.0um/L=0.15um at 5nm lambda, quoted by the
`.option scale=5m` Magic itself emits); (2) Netgen reports "Circuits
match uniquely" with schematic W/L converted to the same lambda units
(the PDK setup compares w/l at 1% and deletes ad/as/pd/ps/mult —
verified in the deck, so no wrapper games beyond unit conversion).
Base skips everything (no binaries/PDK in the base image).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from analog_ic_design.layout.pcells import LAYERS, PIN_LAYERS, mos_labels, nmos_rects

EMIT = Path(__file__).resolve().parent.parent / "scripts" / "layout_pcell_emit.py"
EXTRACT_TCL = Path(__file__).resolve().parent.parent / "scripts" / "magic_extract.tcl"
GOLDEN = Path(__file__).resolve().parent / "golden" / "nmos.cir"
SKY130_TECH = "/usr/local/share/pdk/sky130A/libs.tech/magic/sky130A.tech"
SKY130_SETUP = "/usr/local/share/pdk/sky130A/libs.tech/netgen/sky130A_setup.tcl"
# Magic lambda for sky130A, quoted by the `.option scale=5m` line Magic
# ext2spice emits for this technology.
MAGIC_LAMBDA_M = 5e-9

NEEDS_LVS_TOOLS = pytest.mark.skipif(
    shutil.which("klayout") is None
    or shutil.which("magic") is None
    or shutil.which("netgen") is None
    or not Path(SKY130_TECH).is_file(),
    reason="layout toolchain absent (base image); covered by CI eda job",
)


def _emit(tmp_path: Path) -> None:
    rects = nmos_rects(w_m=1e-6, l_m=0.15e-6, fingers=1)
    labels = mos_labels(w_m=1e-6, l_m=0.15e-6, fingers=1)
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


def _extracted_device_line(tmp_path: Path) -> str:
    magic = subprocess.run(
        ["magic", "-dnull", "-noconsole", "-T", SKY130_TECH],
        input=(EXTRACT_TCL.read_text(encoding="utf-8")),
        capture_output=True,
        text=True,
        timeout=600,
        cwd=tmp_path,
    )
    assert magic.returncode == 0, magic.stderr[-2000:]
    spice = tmp_path / "pcell_nmos.spice"
    assert spice.is_file()
    lines = [
        text for text in spice.read_text(encoding="utf-8").splitlines() if text.startswith("X")
    ]
    assert len(lines) == 1
    return lines[0]


@NEEDS_LVS_TOOLS
def test_extraction_recognizes_drawn_device(tmp_path: Path) -> None:
    _emit(tmp_path)
    line = _extracted_device_line(tmp_path)
    assert "sky130_fd_pr__nfet_01v8" in line
    assert "w=200" in line and "l=30" in line
    for net in ("drain", "gate", "source"):
        assert net in line


@NEEDS_LVS_TOOLS
def test_lvs_drawn_matches_schematic_golden(tmp_path: Path) -> None:
    _emit(tmp_path)
    line = _extracted_device_line(tmp_path)

    def to_lambda(match: re.Match[str]) -> str:
        return str(float(match.group(1)) / MAGIC_LAMBDA_M)

    schem = []
    for text in GOLDEN.read_text(encoding="utf-8").splitlines():
        if text.startswith("* cell"):
            continue
        text = re.sub(r"L=([0-9.eE+-]+)", lambda m: "l=" + to_lambda(m), text)
        text = re.sub(r"W=([0-9.eE+-]+)", lambda m: "w=" + to_lambda(m), text)
        schem.append(text)
    (tmp_path / "schem.spice").write_text(
        ".subckt nmos_golden drain gate source vss\n" + "\n".join(schem) + "\n.ends\n",
        encoding="utf-8",
    )
    layout_line = line.replace(" SUB", " vss")
    (tmp_path / "layout.spice").write_text(
        ".subckt pcell_nmos drain gate source vss\n" + layout_line + "\n.ends\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        ["netgen", "-batch", "lvs",
         f"{tmp_path / 'layout.spice'} pcell_nmos",
         f"{tmp_path / 'schem.spice'} nmos_golden", SKY130_SETUP],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=tmp_path,
    )
    assert proc.returncode == 0
    assert "Circuits match uniquely." in proc.stdout
