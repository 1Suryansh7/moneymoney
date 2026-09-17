"""Stage 8 dump: OASIS -> polygon JSON via pya (EDA only).

Keeps the layout file as the single source of truth for downstream
rendering: `examples/plot_layout.py` draws exactly what this dumps, so
the PNG and the DRC input cannot drift apart. Contract (same
`klayout -b -r` argv lesson as the emitter): reads `pcell.oas` from the
working directory, writes `polys.json` next to it, prints REPORT lines.
"""

import json

import pya  # type: ignore[import-not-found]  # klayout runtime only (`klayout -b -r`)


def main() -> None:
    layout = pya.Layout()
    layout.read("pcell.oas")
    top = layout.top_cell()
    layers: dict[str, list[int]] = {}
    rects: dict[str, list[list[float]]] = {}
    for info in layout.layer_infos():
        name = f"{info.layer}/{info.datatype}"
        boxes = []
        for shape in top.shapes(layout.layer(info.layer, info.datatype)).each():
            box = shape.bbox()
            dbu = layout.dbu
            boxes.append([
                box.left * dbu,
                box.bottom * dbu,
                box.right * dbu,
                box.top * dbu,
            ])
        if boxes:
            layers[name] = [info.layer, info.datatype]
            rects[name] = boxes
    with open("polys.json", "w", encoding="utf-8") as handle:
        json.dump({"layers": layers, "rects": rects, "dbu_um": layout.dbu}, handle)
    total = sum(len(v) for v in rects.values())
    print(f"REPORT layers={len(rects)}")
    print(f"REPORT boxes_total={total}")


main()
