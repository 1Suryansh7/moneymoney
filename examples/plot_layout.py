"""Plot one OASIS-derived polygon set to PNG (Stage 8 visual record).

Thin CLI over `layout.plot.render` (mirrors `plot_inverter.py` usage):
  python examples/plot_layout.py polys.json out.png "caption"
"""

from __future__ import annotations

import sys

from analog_ic_design.layout.plot import render

if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], title=sys.argv[3])
