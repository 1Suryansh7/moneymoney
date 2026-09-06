"""Sky130 PDK geometry minima for automated W/L validation (Stage 1 follow-up).

Closes the open 1F follow-up ("automated W/L-minima checks need PDK minima
ingestion") that human eyes previously covered at checkpoints. Values are
SI base units (meters). The validator consumes this table; device symbols
absent from it are NOT checked (no invented limits — unknown devices stay
fail-open, exactly as before).

Provenance (Law 2: read, never recalled — extracted 2026-09-06 in the
pinned EDA image with `lmin\\s*=\\s*(\\S+)\\s+lmax...wmin...wmax` over
every `.model` bin card; global minimum of each column per file):
- `nfet_01v8`: `.../libs.ref/sky130_fd_pr/spice/sky130_fd_pr__nfet_01v8__tt.pm3.spice`
  (1137294 bytes, sha256[:16] `459eca963a134574`, 180 bins)
  → min lmin `1.5e-07`, min wmin `3.6e-07`.
- `pfet_01v8`: `.../libs.ref/sky130_fd_pr/spice/sky130_fd_pr__pfet_01v8__tt.pm3.spice`
  (809553 bytes, sha256[:16] `c943246ce012ea3d`, 108 bins)
  → min lmin `1.5e-07`, min wmin `4.2e-07`.
  (The `__tt.corner.spice` file of the same name is a 796-byte stub that only
  `.include`s the pm3 above — verified by reading it; bins were taken from
  the pm3.)
- PDK scope: sky130A primitive-only @open_pdks `1689ac3f` (fd_pr `403964dc`),
  same pin as the Dockerfile contract and the 1G evidence.

Interpretation: a device geometry strictly below the global bin minimum has
no valid binned model (`could not find a valid modelname` at sim time, as
observed in Stage 2H) and violates foundry rules regardless of bin. Values
AT the minimum are accepted (boundary-inclusive, matching bin edges).
"""

from __future__ import annotations

from typing import Final

#: device_symbol -> (w_min_m, l_min_m). SI meters. See module docstring.
DEVICE_MINIMA: Final[dict[str, tuple[float, float]]] = {
    "nfet_01v8": (3.6e-07, 1.5e-07),
    "pfet_01v8": (4.2e-07, 1.5e-07),
}

#: Parameter names treated as geometry (case-insensitive; ngspice is).
GEOMETRY_PARAMS: Final = frozenset({"W", "L"})
