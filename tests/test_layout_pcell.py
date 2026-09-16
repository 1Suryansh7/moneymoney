"""Stage 8 PCell tests: pure geometry model (base) + OASIS emission (EDA).

`nmos_rects` is tool-free: counts, symmetry, extents, and scaling pin
on base. The emitter round trip runs under `klayout -b -r` on EDA and
must reproduce the model's counts exactly. Geometry grade stays honest
DRC-dirty demo (vias omitted, minimum-rule blind) — parameterization,
not rule compliance, is the claim.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from analog_ic_design.layout.pcells import (
    LAYERS,
    PIN_LAYERS,
    mos_labels,
    nmos_rects,
    pmos_rects,
    rect_areas,
)

EMIT = Path(__file__).resolve().parent.parent / "scripts" / "layout_pcell_emit.py"
SKY130_DRC_DECK = (
    "/usr/local/share/pdk/sky130A/libs.tech/klayout/drc/sky130A.lydrc"
)
NEEDS_KLAYOUT = pytest.mark.skipif(
    shutil.which("klayout") is None,
    reason="klayout binary absent (base image); covered by CI eda job",
)
NEEDS_DRC_DECK = pytest.mark.skipif(
    not Path(SKY130_DRC_DECK).is_file(),
    reason="Sky130 DRC deck absent (base image); covered by CI eda job",
)


def test_single_finger_counts() -> None:
    rects = nmos_rects(w_m=1e-6, l_m=0.15e-6, fingers=1)
    assert set(rects) == set(LAYERS)
    counts = {name: len(v) for name, v in rects.items()}
    assert counts == {
        "diff": 1,
        "tap": 1,
        "poly": 1,
        "licon1": 5,
        "li1": 3,
        "mcon": 4,
        "met1": 2,
        "nsdm": 1,
        "psdm": 0,
        "nwell": 0,
    }


def test_counts_scale_with_fingers() -> None:
    rects = nmos_rects(w_m=1e-6, l_m=0.15e-6, fingers=4)
    counts = {name: len(v) for name, v in rects.items()}
    assert counts["poly"] == 4
    assert counts["licon1"] == 2 * 5 + 1
    assert counts["mcon"] == 2 * 5
    assert counts["li1"] == 5 + 1
    assert counts["met1"] == 5
    assert counts["diff"] == counts["nsdm"] == counts["tap"] == 1


def test_extents_track_w_and_l() -> None:
    narrow = nmos_rects(w_m=1e-6, l_m=0.15e-6, fingers=2)
    wide = nmos_rects(w_m=2e-6, l_m=0.15e-6, fingers=2)
    # Width direction grows with W: diff Y span is W + 2 × margin.
    for name in ("diff", "nsdm"):
        n_lo = min(r[1] for r in narrow[name])
        n_hi = max(r[3] for r in narrow[name])
        w_lo = min(r[1] for r in wide[name])
        w_hi = max(r[3] for r in wide[name])
        assert (w_hi - w_lo) == pytest.approx((n_hi - n_lo) + 1.0)
    # Length direction grows with L: gate stripe width equals L exactly.
    for rect in narrow["poly"]:
        assert rect[2] - rect[0] == pytest.approx(0.15)


def _mirrored(boxes: list[tuple[float, float, float, float]]) -> bool:
    """Every box has an x-mirror partner within float dust (1e-9 µm)."""
    for x0, y0, x1, y1 in boxes:
        if not any(
            abs(-x1 - a) < 1e-9
            and abs(y0 - b) < 1e-9
            and abs(-x0 - c) < 1e-9
            and abs(y1 - d) < 1e-9
            for a, b, c, d in boxes
        ):
            return False
    return True


def test_x_symmetry_and_positive_area() -> None:
    rects = nmos_rects(w_m=1e-6, l_m=0.2e-6, fingers=3)
    for boxes in rects.values():
        for x0, y0, x1, y1 in boxes:
            assert x1 > x0 and y1 > y0
        assert _mirrored(boxes)
    assert rect_areas(rects["poly"]) == pytest.approx(3 * 0.2 * 1.86)


def test_rejects_nonsense() -> None:
    with pytest.raises(ValueError, match="positive"):
        nmos_rects(w_m=-1e-6, l_m=0.15e-6)
    with pytest.raises(ValueError, match="positive"):
        nmos_rects(w_m=1e-6, l_m=0.0)
    with pytest.raises(ValueError, match="fingers"):
        nmos_rects(w_m=1e-6, l_m=0.15e-6, fingers=0)
    with pytest.raises(ValueError, match="fingers"):
        mos_labels(w_m=1e-6, l_m=0.15e-6, fingers=0)


def _inside(x: float, y: float, boxes: list[tuple[float, float, float, float]]) -> bool:
    return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in boxes)


def test_labels_nets_alternate_and_sit_inside_shapes() -> None:
    rects = nmos_rects(w_m=1e-6, l_m=0.15e-6, fingers=2)
    labels = mos_labels(w_m=1e-6, l_m=0.15e-6, fingers=2)
    assert [text for _, _, _, text in labels] == ["g", "s", "d", "s", "b"]
    assert all(pin in PIN_LAYERS for _, _, pin, _ in labels)
    by_net = {text: (x, y, pin) for x, y, pin, text in labels}
    gx, gy, gpin = by_net["g"]
    assert gpin == "poly.pin" and _inside(gx, gy, rects["poly"])
    bx, by, bpin = by_net["b"]
    assert bpin == "tap.pin" and _inside(bx, by, rects["tap"])
    for x, y, pin, text in labels:
        if text in ("s", "d"):
            assert pin == "met1.pin" and _inside(x, y, rects["met1"])


def test_pmos_mirrors_nmos_plus_well() -> None:
    nmos = nmos_rects(w_m=2e-6, l_m=0.15e-6, fingers=2)
    pmos = pmos_rects(w_m=2e-6, l_m=0.15e-6, fingers=2)
    for name in ("diff", "tap", "poly", "licon1", "li1", "mcon", "met1"):
        assert pmos[name] == nmos[name]
    assert pmos["psdm"] == nmos["nsdm"]
    assert pmos["nsdm"] == []
    assert len(pmos["nwell"]) == 1
    wx0, wy0, wx1, wy1 = pmos["nwell"][0]
    assert wx1 - wx0 >= 0.84 and wy1 - wy0 >= 0.84
    # Well strictly contains device + tap.
    assert wx0 < min(r[0] for r in pmos["diff"])
    assert wy0 < min(r[1] for r in pmos["tap"])


@NEEDS_KLAYOUT
def test_emitter_roundtrip_reproduces_model_counts(tmp_path: Path) -> None:
    rects = nmos_rects(w_m=1e-6, l_m=0.15e-6, fingers=2)
    labels = mos_labels(w_m=1e-6, l_m=0.15e-6, fingers=2)
    spec = {
        "layers": {name: list(lv) for name, lv in LAYERS.items()},
        "pin_layers": {name: list(lv) for name, lv in PIN_LAYERS.items()},
        "rects": {name: [list(r) for r in boxes] for name, boxes in rects.items()},
        "labels": [list(label) for label in labels],
    }
    (tmp_path / "rects.json").write_text(json.dumps(spec), encoding="utf-8")
    proc = subprocess.run(
        ["klayout", "-b", "-r", str(EMIT)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert (tmp_path / "pcell.oas").is_file()
    rep = {}
    for line in proc.stdout.splitlines():
        if line.startswith("REPORT "):
            key, _, value = line[len("REPORT "):].partition("=")
            rep[key] = value
    assert rep["layers"] == "10"
    assert rep["boxes_total"] == str(sum(len(v) for v in rects.values()))
    assert rep["texts_total"] == str(len(labels))
    assert rep["roundtrip_ok"] == "True"


@NEEDS_KLAYOUT
@NEEDS_DRC_DECK
@pytest.mark.parametrize("polarity", ["nmos", "pmos"])
def test_pcell_drc_clean(tmp_path: Path, polarity: str) -> None:
    """FEOL+BEOL DRC deck reports zero violations on the canonical device.

    The deck copy enables FEOL (upstream default is BEOL-only); the PDK
    deck itself is never modified. Seconds per polarity on EDA.
    """
    import xml.etree.ElementTree as ET

    make = pmos_rects if polarity == "pmos" else nmos_rects
    w_m = 2e-6 if polarity == "pmos" else 1e-6
    rects = make(w_m=w_m, l_m=0.15e-6, fingers=1)
    spec = {
        "layers": {name: list(lv) for name, lv in LAYERS.items()},
        "rects": {name: [list(r) for r in boxes] for name, boxes in rects.items()},
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
    deck_text = Path(SKY130_DRC_DECK).read_text(encoding="utf-8")
    assert "FEOL    = false" in deck_text
    (tmp_path / "sky130A_feol.lydrc").write_text(
        deck_text.replace("FEOL    = false", "FEOL    = true", 1), encoding="utf-8"
    )
    drc = subprocess.run(
        [
            "klayout", "-b",
            "-rd", f"input={tmp_path / 'pcell.oas'}",
            "-rd", f"report={tmp_path / 'drc.txt'}",
            "-r", str(tmp_path / "sky130A_feol.lydrc"),
        ],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=tmp_path,
    )
    assert drc.returncode == 0, drc.stderr[-2000:]
    items = ET.parse(tmp_path / "drc.txt").getroot().find("items")
    assert items is not None and len(items) == 0
