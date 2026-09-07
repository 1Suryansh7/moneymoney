"""Input-offset extraction: differential zero-crossing (Stage 3 Commit 3H).

Governed by the `OFFSET` MetricContract: differential input voltage Vid =
V(inp) - V(inn) at which differential output Vod = V(outp) - V(outn)
crosses zero. Signed Volts (V); systematic offset near zero for symmetric
geometry (mismatch models off), nonzero with predictable sign under
intentional imbalance (verified live, see tests).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from analog_ic_design.sim.ngspice import SimError


def extract_offset(
    v_inp: Sequence[float],
    v_inn: Sequence[float],
    v_outp: Sequence[float],
    v_outn: Sequence[float],
) -> float:
    """Extract input-referred offset: Vid at the first Vod zero crossing.

    Fails closed with `SimError` on ragged/short/non-finite data,
    non-monotonic Vid sweep, or no zero crossing within the sweep range.
    """
    n = len(v_inp)
    if not (len(v_inn) == len(v_outp) == len(v_outn) == n):
        raise SimError(
            "Schema: ragged offset vectors: "
            f"inp={len(v_inp)} inn={len(v_inn)} "
            f"outp={len(v_outp)} outn={len(v_outn)}"
        )
    if n < 2:
        raise SimError(f"SPICE convergence: offset sweep has fewer than 2 points ({n})")
    for idx, vals in enumerate(zip(v_inp, v_inn, v_outp, v_outn, strict=True)):
        if not all(math.isfinite(v) for v in vals):
            raise SimError(f"SPICE convergence: non-finite offset sample at index {idx}")

    vid = [float(a) - float(b) for a, b in zip(v_inp, v_inn, strict=True)]
    vod = [float(a) - float(b) for a, b in zip(v_outp, v_outn, strict=True)]
    diffs = [b - a for a, b in zip(vid, vid[1:], strict=False)]
    if not (all(d > 0.0 for d in diffs) or all(d < 0.0 for d in diffs)):
        raise SimError("SPICE convergence: Vid sweep vector is not strictly monotonic")

    for i in range(1, n):
        prev, curr = vod[i - 1], vod[i]
        if prev == 0.0:
            return float(vid[i - 1])
        if curr == 0.0:
            return float(vid[i])
        if (prev < 0.0) != (curr < 0.0):
            frac = (0.0 - prev) / (curr - prev)
            return float(vid[i - 1] + frac * (vid[i] - vid[i - 1]))
    raise SimError("SPICE convergence: differential output never crosses zero in sweep")
