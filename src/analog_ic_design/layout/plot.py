"""Layout rendering: polygon JSON -> PNG (Stage 8 visual record).

Renders the `polys.json` written by `scripts/layout_dump.py` (file
truth, never the geometry model) with a fixed palette plus a provenance
caption. Pure matplotlib: runs on base. This is an INTERIM visual for
the §8 checkpoint — KLayout offscreen `save_image` does not paint fills
in 0.30.12 (proven by control renders, including the PDK's own GDS), so
human KLayout-GUI review of the OASIS stays pending and is flagged.
"""

from __future__ import annotations

import json
from pathlib import Path

COLORS = {
    "65/20": "#4caf50",
    "65/44": "#2e7d32",
    "66/20": "#f44336",
    "66/44": "#ffeb3b",
    "67/20": "#ff9800",
    "67/44": "#9c27b0",
    "68/20": "#2196f3",
    "93/44": "#795548",
    "94/20": "#e91e63",
    "64/20": "#00bcd4",
}


def render(polys_path: str, out_path: str, *, title: str) -> None:
    """Render `polys.json` to `out_path` PNG with provenance caption."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.patches as patches
    import matplotlib.pyplot as plt

    spec = json.loads(Path(polys_path).read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_facecolor("black")
    fig.patch.set_facecolor("black")
    for name, boxes in spec["rects"].items():
        color = COLORS.get(name, "#9e9e9e")
        for x0, y0, x1, y1 in boxes:
            ax.add_patch(
                patches.Rectangle(
                    (x0, y0), x1 - x0, y1 - y0,
                    facecolor=color, edgecolor="white", linewidth=0.4, alpha=0.85,
                )
            )
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_xlabel("um", color="white")
    ax.tick_params(colors="white", labelsize=8)
    ax.text(
        0.5, 0.02, title, transform=ax.transAxes, ha="center",
        fontsize=9, color="white",
    )
    fig.savefig(out_path, dpi=110, facecolor="black")
    plt.close(fig)


__all__ = ["COLORS", "render"]
