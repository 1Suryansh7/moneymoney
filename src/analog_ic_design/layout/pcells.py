"""Parametric cells: pure geometry models (Stage 8 PCells).

`nmos_rects` computes axis-aligned rectangles in MICRONS from SI-meter
device sizes — the single SI boundary crossing in physical design,
mirroring the deck micron rule (documented, one way). No tool imports
here: this module is importable and fully testable on base. Emission to
OASIS/GDS lives in `scripts/layout_pcell_emit.py` (pya runtime) over an
explicit JSON boundary, so no Python object graph ever crosses into the
layout tool implicitly.

Layer map quoted (Law 2) from the pinned PDK:
  libs.tech/klayout/tech/sky130A.lyp
  diff.drawing 65/20, tap.drawing 65/44, poly.drawing 66/20,
  licon1.drawing 66/44, li1.drawing 67/20, mcon.drawing 67/44,
  met1.drawing 68/20, nsdm.drawing 93/44.

Grade: honest DRC-dirty demo geometry (vias omitted, minimum-rule
blind). DRC-clean iteration and the §8 visual checkpoint come later;
this module proves parameterization (counts/areas scale with W/L and
finger count), never rule compliance.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

LAYERS: Final = {
    "diff": (65, 20),
    "tap": (65, 44),
    "poly": (66, 20),
    "licon1": (66, 44),
    "li1": (67, 20),
    "mcon": (67, 44),
    "met1": (68, 20),
    "nsdm": (93, 44),
    "psdm": (94, 20),
    "nwell": (64, 20),
}

#: Pin layers for GDS TEXT labels, quoted from `sky130A.lyp`
#: (diff.pin 65/16, poly.pin 66/16, met1.pin 68/16, tap.pin 65/48).
PIN_LAYERS: Final = {
    "poly.pin": (66, 16),
    "met1.pin": (68, 16),
    "tap.pin": (65, 48),
}

Rect = tuple[float, float, float, float]

_CONTACT_UM: Final = 0.17
# S/D bar width derived from li rules (deck: li.5 enclosure 0.08 by two
# opposite edges, li.3 spacing 0.17): strap 0.37 (enclosure 0.10) +
# spacing 0.20 (0.17 + margin).
_LI_STRAP_UM: Final = 0.37
_LI_SPACE_UM: Final = 0.20
_SD_BAR_UM: Final = _LI_STRAP_UM + _LI_SPACE_UM
_DIFF_Y_MARGIN_UM: Final = 0.25
# Gate endcap past the diff edge (deck: poly.8 min 0.13um + margin).
_GATE_ENDCAP_UM: Final = 0.18
_IMPLANT_OVERSIZE_UM: Final = 0.15
# Tap gap to diff (deck: difftap.3 min spacing 0.27um + margin).
_TAP_Y_GAP_UM: Final = 0.30
_TAP_Y_WIDTH_UM: Final = 0.20


def _positive(value: float, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"Schema: pcell {name} must be a number")
    if not value > 0.0 or value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"Schema: pcell {name} must be finite and positive")
    return float(value)


# nwell minimum width (deck: nwell.1 0.84um); well box is grown to it.
_NWELL_MIN_UM: Final = 0.84
_NWELL_MARGIN_UM: Final = 0.30


def _mos_rects(
    *,
    w_um: float,
    l_um: float,
    fingers: int,
    implant: str,
    well: bool,
) -> dict[str, list[Rect]]:
    pitch = l_um + _SD_BAR_UM
    span_x = fingers * pitch + _SD_BAR_UM
    x0 = -span_x / 2.0
    half_w = w_um / 2.0

    rects: dict[str, list[Rect]] = {name: [] for name in LAYERS}
    # Active + implant.
    rects["diff"] = [(x0, -half_w - _DIFF_Y_MARGIN_UM, x0 + span_x, half_w + _DIFF_Y_MARGIN_UM)]
    rects[implant] = [
        (
            x0 - _IMPLANT_OVERSIZE_UM,
            -half_w - _DIFF_Y_MARGIN_UM - _IMPLANT_OVERSIZE_UM,
            x0 + span_x + _IMPLANT_OVERSIZE_UM,
            half_w + _DIFF_Y_MARGIN_UM + _IMPLANT_OVERSIZE_UM,
        )
    ]
    # Gate stripes + S/D gap grid.
    gate_hi = half_w + _DIFF_Y_MARGIN_UM + _GATE_ENDCAP_UM
    for i in range(fingers):
        cx = x0 + _SD_BAR_UM + i * pitch + l_um / 2.0
        rects["poly"].append(
            (cx - l_um / 2.0, -gate_hi, cx + l_um / 2.0, gate_hi)
        )
    gaps = [x0 + _SD_BAR_UM / 2.0 + i * pitch for i in range(fingers + 1)]
    for gx in gaps:
        for sign in (-1.0, 1.0):
            cy = sign * half_w / 2.0
            half_c = _CONTACT_UM / 2.0
            contact: Rect = (gx - half_c, cy - half_c, gx + half_c, cy + half_c)
            rects["licon1"].append(contact)
            rects["mcon"].append(contact)
        half_s = _LI_STRAP_UM / 2.0
        strap: Rect = (gx - half_s, -half_w - 0.10, gx + half_s, half_w + 0.10)
        rects["li1"].append(strap)
        rects["met1"].append(strap)
    # Substrate tap segment below the device + its contact (deck:
    # licon.16 tap must enclose one licon; licon.4 needs li overlap).
    tap_y1 = -half_w - _DIFF_Y_MARGIN_UM - _TAP_Y_GAP_UM - _TAP_Y_WIDTH_UM
    tap_y0 = tap_y1 + _TAP_Y_WIDTH_UM
    rects["tap"] = [(x0, tap_y1, x0 + span_x, tap_y0)]
    tap_cy = (tap_y0 + tap_y1) / 2.0
    tap_half = _CONTACT_UM / 2.0
    rects["licon1"].append((-tap_half, tap_cy - tap_half, tap_half, tap_cy + tap_half))
    tap_li_half = _LI_STRAP_UM / 2.0
    rects["li1"].append((-tap_li_half, tap_y1 - 0.05, tap_li_half, tap_y0 + 0.05))
    if well:
        # nwell ring around device + tap (deck: nwell.1 min width 0.84um).
        wx0 = x0 - _NWELL_MARGIN_UM
        wx1 = x0 + span_x + _NWELL_MARGIN_UM
        wy0 = tap_y1 - _NWELL_MARGIN_UM
        wy1 = half_w + _DIFF_Y_MARGIN_UM + _IMPLANT_OVERSIZE_UM + _NWELL_MARGIN_UM
        if wx1 - wx0 < _NWELL_MIN_UM:
            mid = (wx0 + wx1) / 2.0
            wx0, wx1 = mid - _NWELL_MIN_UM / 2.0, mid + _NWELL_MIN_UM / 2.0
        if wy1 - wy0 < _NWELL_MIN_UM:
            mid = (wy0 + wy1) / 2.0
            wy0, wy1 = mid - _NWELL_MIN_UM / 2.0, mid + _NWELL_MIN_UM / 2.0
        rects["nwell"] = [(wx0, wy0, wx1, wy1)]
    return rects


def _checked(*, w_m: float, l_m: float, fingers: int) -> tuple[float, float, int]:
    w_um = _positive(w_m, "w_m") * 1e6
    l_um = _positive(l_m, "l_m") * 1e6
    if not isinstance(fingers, int) or isinstance(fingers, bool) or fingers < 1:
        raise ValueError("Schema: pcell fingers must be a positive integer")
    return w_um, l_um, fingers


def nmos_rects(
    *,
    w_m: float,
    l_m: float,
    fingers: int = 1,
) -> dict[str, list[Rect]]:
    """Multi-finger NMOS rectangles in microns, keyed by layer name.

    Fingers tile along X with shared S/D bars (`fingers + 1` gaps);
    each finger has width `w_m` along Y. Contacts land two per gap,
    centered in their S/D bar; straps/pads follow the contact grid;
    vias are omitted (documented DRC-dirty grade, since cleaned for
    the canonical device — see To-Do Stage 8).
    """
    w_um, l_um, fingers = _checked(w_m=w_m, l_m=l_m, fingers=fingers)
    return _mos_rects(w_um=w_um, l_um=l_um, fingers=fingers, implant="nsdm", well=False)


def pmos_rects(
    *,
    w_m: float,
    l_m: float,
    fingers: int = 1,
) -> dict[str, list[Rect]]:
    """Multi-finger PMOS rectangles: NMOS geometry in an nwell ring with
    psdm implant. Tap sits inside the well (n-tap); well box grown to
    the deck nwell minimum.
    """
    w_um, l_um, fingers = _checked(w_m=w_m, l_m=l_m, fingers=fingers)
    return _mos_rects(w_um=w_um, l_um=l_um, fingers=fingers, implant="psdm", well=True)


def rect_areas(rects: Sequence[Rect]) -> float:
    """Total area of rectangles (square microns); pure helper for tests."""
    return sum((x1 - x0) * (y1 - y0) for x0, y0, x1, y1 in rects)


Label = tuple[float, float, str, str]


def mos_labels(
    *,
    w_m: float,
    l_m: float,
    fingers: int = 1,
) -> list[Label]:
    """Net labels `(x, y, pin_layer, net)` for Magic extraction.

    Shared by both polarities (identical grid): gate `g` on the poly
    extension, S/D alternating `s`/`d` by gap starting with source on
    the met pads, bulk `b` on the tap contact. Positions sit strictly
    inside their shapes (pinned by containment tests); pin layers are
    the PDK `.pin` purposes so GDS TEXT attaches in Magic.
    """
    w_um, l_um, fingers = _checked(w_m=w_m, l_m=l_m, fingers=fingers)
    half_w = w_um / 2.0
    pitch = l_um + _SD_BAR_UM
    span_x = fingers * pitch + _SD_BAR_UM
    x0 = -span_x / 2.0
    gate_hi = half_w + _DIFF_Y_MARGIN_UM + _GATE_ENDCAP_UM
    gate_cx = x0 + _SD_BAR_UM + l_um / 2.0
    labels: list[Label] = [(gate_cx, gate_hi - 0.09, "poly.pin", "g")]
    for i in range(fingers + 1):
        gx = x0 + _SD_BAR_UM / 2.0 + i * pitch
        labels.append((gx, 0.0, "met1.pin", "s" if i % 2 == 0 else "d"))
    tap_y1 = -half_w - _DIFF_Y_MARGIN_UM - _TAP_Y_GAP_UM - _TAP_Y_WIDTH_UM
    tap_y0 = tap_y1 + _TAP_Y_WIDTH_UM
    labels.append((0.0, (tap_y0 + tap_y1) / 2.0, "tap.pin", "b"))
    return labels


__all__ = [
    "LAYERS",
    "PIN_LAYERS",
    "Label",
    "Rect",
    "mos_labels",
    "nmos_rects",
    "pmos_rects",
    "rect_areas",
]
