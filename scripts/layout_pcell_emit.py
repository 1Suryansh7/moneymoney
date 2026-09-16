"""Stage 8 PCell emitter: JSON rectangles -> OASIS via pya (EDA only).

Dumb pipe by design: geometry math lives in `layout.pcells` (tested on
base); this script only transfers explicit rectangles into tool boxes.
Contract (same `klayout -b -r` argv lesson as the spike): reads
`rects.json` from the working directory
  {"layers": {"diff": [65, 20], ...}, "rects": {"diff": [[x0,y0,x1,y1], ...]}}
writes `pcell.oas` next to it, prints REPORT lines (parsed by
tests/test_layout_pcell.py). DBU 1nm, matching the model.
"""

import json
import os

import pya  # type: ignore[import-not-found]  # klayout runtime only (`klayout -b -r`)


def main() -> None:
    with open("rects.json", encoding="utf-8") as handle:
        spec = json.load(handle)
    layout = pya.Layout()
    layout.dbu = 0.001
    top = layout.create_cell("pcell_nmos")
    counts: dict[str, int] = {}
    for name, rects in spec["rects"].items():
        layer, datatype = spec["layers"][name]
        for x0, y0, x1, y1 in rects:
            top.shapes(layout.layer(layer, datatype)).insert(pya.DBox(x0, y0, x1, y1))
        counts[name] = len(rects)
    layout.write("pcell.oas")
    reread = pya.Layout()
    reread.read("pcell.oas")
    ok = all(
        sum(1 for _ in reread.top_cell().shapes(reread.layer(*spec["layers"][n])).each())
        == c
        for n, c in counts.items()
    )
    print(f"REPORT layers={len(counts)}")
    print(f"REPORT boxes_total={sum(counts.values())}")
    print(f"REPORT file_bytes={os.path.getsize('pcell.oas')}")
    print(f"REPORT roundtrip_ok={ok}")


main()
