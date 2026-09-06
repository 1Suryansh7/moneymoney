"""Gain extraction metrics: DC transfer slope and AC small-signal gain (Stage 3 Commit 3C).

Governed by `DC_GAIN` and `AC_GAIN` MetricContracts:
- DC Gain: max |dV(out)/dV(in)| across DC transfer sweep active region.
- AC Gain: |V(out)| / |V(in)| at minimum frequency decade (f = f_min).
Units: V/V (dimensionless ratio). Magnitude is positive float.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from analog_ic_design.sim.ngspice import SimError
from analog_ic_design.sim.waveform import ACWaveform


def extract_dc_gain(v_in: Sequence[float], v_out: Sequence[float]) -> float:
    """Extract small-signal DC voltage gain: max |dV(out) / dV(in)|.

    Requires strictly monotonic `v_in`, equal non-empty sequences (len >= 2),
    and finite values. Fails closed with `SimError` on invalid data.
    """
    if len(v_in) != len(v_out):
        raise SimError(
            f"Schema: ragged DC vectors: len(v_in)={len(v_in)} != len(v_out)={len(v_out)}"
        )
    if len(v_in) < 2:
        raise SimError(f"SPICE convergence: DC sweep has fewer than 2 points ({len(v_in)})")

    # Validate finiteness
    for idx, (vi, vo) in enumerate(zip(v_in, v_out, strict=True)):
        if not math.isfinite(vi) or not math.isfinite(vo):
            raise SimError(f"SPICE convergence: non-finite DC sample at index {idx}: ({vi}, {vo})")

    # Validate strictly monotonic v_in
    diff_in = [b - a for a, b in zip(v_in, v_in[1:], strict=False)]
    is_increasing = all(d > 0.0 for d in diff_in)
    is_decreasing = all(d < 0.0 for d in diff_in)
    if not (is_increasing or is_decreasing):
        raise SimError("SPICE convergence: v_in sweep vector is not strictly monotonic")

    # Compute maximum absolute derivative between adjacent points
    max_slope = 0.0
    for i in range(len(v_in) - 1):
        d_in = v_in[i + 1] - v_in[i]
        d_out = v_out[i + 1] - v_out[i]
        slope = abs(d_out / d_in)
        if slope > max_slope:
            max_slope = slope

    return float(max_slope)


def extract_ac_gain(
    ac: ACWaveform,
    *,
    in_node: str = "in",
    out_node: str = "out",
) -> float:
    """Extract low-frequency small-signal AC voltage gain: |V(out) / V(in)| at f_min."""
    if not ac.frequency:
        raise SimError("SPICE convergence: AC waveform has empty frequency vector")

    in_tr = ac.trace(in_node)
    out_tr = ac.trace(out_node)

    in_mag = in_tr.magnitude()[0]
    out_mag = out_tr.magnitude()[0]

    if not math.isfinite(in_mag) or not math.isfinite(out_mag):
        raise SimError("SPICE convergence: non-finite AC magnitude at f_min")
    if in_mag <= 0.0:
        raise SimError(f"SPICE convergence: input AC magnitude is zero or negative ({in_mag})")

    gain = out_mag / in_mag
    return float(gain)


def extract_ac_gain_db(
    ac: ACWaveform,
    *,
    in_node: str = "in",
    out_node: str = "out",
) -> float:
    """Extract low-frequency small-signal AC voltage gain in decibels: 20*log10(|Av|)."""
    gain_linear = extract_ac_gain(ac, in_node=in_node, out_node=out_node)
    if gain_linear <= 0.0:
        return float("-inf")
    return float(20.0 * math.log10(gain_linear))
