"""Stage 8 plot tests: layout PNG rendering (base, pure matplotlib)."""

from __future__ import annotations

import json
from pathlib import Path

from analog_ic_design.layout.plot import render


def test_render_writes_labeled_png(tmp_path: Path) -> None:
    polys = tmp_path / "polys.json"
    polys.write_text(
        json.dumps({
            "layers": {"65/20": [65, 20], "66/20": [66, 20]},
            "rects": {
                "65/20": [[-0.4, -0.5, 0.4, 0.5]],
                "66/20": [[-0.075, -0.7, 0.075, 0.7]],
            },
            "dbu_um": 0.001,
        }),
        encoding="utf-8",
    )
    out = tmp_path / "shot.png"
    render(str(polys), str(out), title="probe caption")
    assert out.is_file()
    assert out.stat().st_size > 5000
