"""Bandwidth extraction: unity-gain frequency (Stage 3 Commit 3D).

Governed by the `BANDWIDTH` MetricContract: first downward crossing of the
open-loop AC magnitude through 1.0 V/V (0 dB), located by linear
interpolation on the frequency axis between the bracketing sweep points.
Units: Hz (positive float).

Contract note: the stage brief sketches bandwidth as "-3 dB from DC
reference", but the committed contract defines the 0 dB-absolute
unity-gain crossing (with matching invalid-data behavior), and the
contract is the nearer ground truth — this function implements the
contract exactly. The 3D human checkpoint re-verifies the definition.
"""

from __future__ import annotations

import math

from analog_ic_design.sim.ngspice import SimError
from analog_ic_design.sim.waveform import ACWaveform

_UNITY_GAIN = 1.0


def extract_bandwidth(
    ac: ACWaveform,
    *,
    in_node: str = "in",
    out_node: str = "out",
) -> float:
    """Extract unity-gain bandwidth: first downward crossing of |V(out)/V(in)|
    through 1.0 V/V, linearly interpolated in frequency.

    Fails closed with `SimError` on empty/non-finite/non-monotonic data,
    zero input, a response that starts below unity, or one that never
    crosses unity within the sweep.
    """
    if not ac.frequency:
        raise SimError("SPICE convergence: AC waveform has empty frequency vector")
    freqs = [float(f) for f in ac.frequency]
    if any(not math.isfinite(f) for f in freqs):
        raise SimError("SPICE convergence: non-finite frequency sample in AC response")
    if any(b <= a for a, b in zip(freqs, freqs[1:], strict=False)):
        raise SimError("SPICE convergence: AC frequency vector is not strictly increasing")

    in_mag = ac.trace(in_node).magnitude()
    out_mag = ac.trace(out_node).magnitude()
    if len(in_mag) != len(freqs) or len(out_mag) != len(freqs):
        raise SimError(
            "Schema: ragged AC vectors: "
            f"freq={len(freqs)} in={len(in_mag)} out={len(out_mag)}"
        )
    gains: list[float] = []
    for idx, (vi, vo) in enumerate(zip(in_mag, out_mag, strict=True)):
        if not math.isfinite(vi) or not math.isfinite(vo):
            raise SimError(f"SPICE convergence: non-finite AC magnitude at index {idx}")
        if vi <= 0.0:
            raise SimError(f"SPICE convergence: input AC magnitude not positive ({vi})")
        gains.append(vo / vi)

    if gains[0] < _UNITY_GAIN:
        raise SimError(
            f"SPICE convergence: AC response starts below unity ({gains[0]:.4f} V/V)"
        )
    for i in range(1, len(gains)):
        if gains[i] < _UNITY_GAIN:
            f_lo, g_lo = freqs[i - 1], gains[i - 1]
            f_hi, g_hi = freqs[i], gains[i]
            frac = (_UNITY_GAIN - g_lo) / (g_hi - g_lo)
            return float(f_lo + frac * (f_hi - f_lo))
    raise SimError("SPICE convergence: AC response never crosses unity within the sweep")
