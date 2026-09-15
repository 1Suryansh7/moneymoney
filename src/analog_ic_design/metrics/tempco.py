"""Bandgap tempco extractors (R0-5, B7 bench-local).

Pure functions over measured vectors — no simulator, no database. The
bench matrix (Stage 3) stays frozen; these bench-local extractors serve
the B7 runner the way `extract_dc_gain` serves B3, and are pinned by
hand-computed goldens below in `tests/test_tempco.py`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from analog_ic_design.sim.ngspice import SimError


def compensated_vref(
    veb: Sequence[float],
    delta_vbe: Sequence[float],
    *,
    k: float,
) -> list[float]:
    """First-order bandgap sum: `Vref = Veb + k·ΔVbe` point by point.

    `k` is the runner's declared design constant (nominal first-order
    cancel near `(dVeb/dT)/(dΔVbe/dT)`); the tempco of the result is the
    measured claim, never the choice of `k`.
    """
    if len(veb) != len(delta_vbe) or not veb:
        raise SimError("Constraint: Veb/ΔVbe vectors must be non-empty and aligned")
    if not math.isfinite(k):
        raise SimError("Constraint: compensation factor k must be finite")
    out = []
    for v, d in zip(veb, delta_vbe, strict=True):
        if not math.isfinite(v) or not math.isfinite(d):
            raise SimError("Constraint: bandgap vectors must be finite")
        out.append(v + k * d)
    return out


def extract_tempco(temps_c: Sequence[float], values: Sequence[float]) -> float:
    """Box-method temperature coefficient in ppm/°C.

    `(max-min)/mean/(Tmax-Tmin) × 1e6` over the swept range. Fails closed
    on fewer than 2 points, non-increasing temperatures, non-finite data,
    or zero mean/span — a flat or degenerate sweep is a broken bench,
    not a perfect reference.
    """
    if len(temps_c) != len(values) or len(temps_c) < 2:
        raise SimError("Constraint: tempco needs ≥2 aligned (temp, value) points")
    if any(b <= a for a, b in zip(temps_c, temps_c[1:], strict=False)):
        raise SimError("Constraint: sweep temperatures must be strictly increasing")
    if any(
        not math.isfinite(t) or not math.isfinite(v)
        for t, v in zip(temps_c, values, strict=True)
    ):
        raise SimError("Constraint: tempco vectors must be finite")
    span = temps_c[-1] - temps_c[0]
    mean = sum(values) / len(values)
    if span <= 0.0 or mean == 0.0:
        raise SimError("Constraint: tempco needs positive span and non-zero mean")
    return (max(values) - min(values)) / abs(mean) / span * 1e6


__all__ = ["compensated_vref", "extract_tempco"]
