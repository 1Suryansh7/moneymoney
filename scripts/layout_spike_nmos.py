"""Stage 8 spike K: single-NMOS geometry proof via KLayout pya (EDA only).

Draws one honest DRC-dirty demo device (NOT a PCell, NOT DRC-clean —
placement/DRC rules arrive later) to prove the KLayout Python API path:
SI-meter inputs -> DBU boxes -> OASIS write -> re-read round trip.

Layer map quoted (Law 2) from the pinned PDK:
  libs.tech/klayout/tech/sky130A.lyp
  diff.drawing 65/20, tap.drawing 65/44, poly.drawing 66/20,
  licon1.drawing 66/44, li1.drawing 67/20, mcon.drawing 67/44,
  met1.drawing 68/20, nsdm.drawing 93/44.
Geometry values (W/L) are author-chosen demo sizes for the API proof.

Run: klayout -b -r scripts/layout_spike_nmos.py (from the target
directory — `klayout -b -r` treats positional args as input layouts,
so the output name is fixed by contract, not argv).
Report lines on stdout: REPORT key=value (parsed by tests/test_layout_spike.py).
"""

import os

import pya  # type: ignore[import-not-found]  # klayout runtime only (`klayout -b -r`)

# SI-meter device sizes (author-chosen demo values for the API proof).
W_M = 1.0e-6
L_M = 0.15e-6
# DBU resolution: 1 nm. SI boundary conversion mirrors the deck micron
# rule (geometry crosses to tool units here, documented, one way).
DBU_UM = 0.001

LAYERS = {
    "diff": (65, 20),
    "tap": (65, 44),
    "poly": (66, 20),
    "licon1": (66, 44),
    "li1": (67, 20),
    "mcon": (67, 44),
    "met1": (68, 20),
    "nsdm": (93, 44),
}


def _box_um(x0: float, y0: float, x1: float, y1: float) -> pya.DBox:
    return pya.DBox(x0, y0, x1, y1)


def build() -> tuple[pya.Layout, dict[str, int]]:
    l_um = L_M * 1e6
    layout = pya.Layout()
    layout.dbu = DBU_UM
    top = layout.create_cell("spike_nmos")
    layers = {name: layout.layer(*lv) for name, lv in LAYERS.items()}
    boxes: dict[str, list[pya.DBox]] = {
        # Active + gate: poly crosses diff (gate extends past active).
        "diff": [_box_um(-0.40, -0.50, 0.40, 0.50)],
        "poly": [_box_um(-l_um / 2.0, -0.70, l_um / 2.0, 0.70)],
        # Implant oversize around active.
        "nsdm": [_box_um(-0.55, -0.65, 0.55, 0.65)],
        # Source/drain contacts: two per side on the active.
        "licon1": [
            _box_um(-0.335, -0.25, -0.165, -0.08),
            _box_um(-0.335, 0.08, -0.165, 0.25),
            _box_um(0.165, -0.25, 0.335, -0.08),
            _box_um(0.165, 0.08, 0.335, 0.25),
        ],
        # Local-interconnect straps over the contacts, reaching outward.
        "li1": [
            _box_um(-0.40, -0.30, -0.10, 0.30),
            _box_um(0.10, -0.30, 0.40, 0.30),
        ],
        # Met1 pads over the straps (vias omitted: DRC-dirty demo).
        "mcon": [
            _box_um(-0.335, -0.25, -0.165, -0.08),
            _box_um(-0.335, 0.08, -0.165, 0.25),
            _box_um(0.165, -0.25, 0.335, -0.08),
            _box_um(0.165, 0.08, 0.335, 0.25),
        ],
        "met1": [
            _box_um(-0.45, -0.35, -0.05, 0.35),
            _box_um(0.05, -0.35, 0.45, 0.35),
        ],
        # Substrate tap ring segment (bulk hookup placeholder).
        "tap": [_box_um(-0.90, -0.90, 0.90, -0.70)],
    }
    counts: dict[str, int] = {}
    for name, rects in boxes.items():
        for rect in rects:
            top.shapes(layers[name]).insert(rect)
        counts[name] = len(rects)
    return layout, counts


def main() -> None:
    out = "spike_nmos.oas"
    layout, counts = build()
    layout.write(out)
    reread = pya.Layout()
    reread.read(out)
    ok = True
    for name, (layer, datatype) in LAYERS.items():
        have = sum(
            1
            for _ in reread.top_cell().shapes(reread.layer(layer, datatype)).each()
        )
        if have != counts[name]:
            ok = False
    print(f"REPORT klayout_version={pya.Application.instance().version()}")
    print(f"REPORT dbu_um={layout.dbu}")
    print(f"REPORT layers={len(LAYERS)}")
    print(f"REPORT boxes_total={sum(counts.values())}")
    print(f"REPORT file_bytes={os.path.getsize(out)}")
    print(f"REPORT roundtrip_ok={ok}")


main()
