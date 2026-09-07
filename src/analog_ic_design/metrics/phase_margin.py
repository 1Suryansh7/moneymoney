"""Phase-margin extraction from a loop-gain response (Stage 3 Commit 3E).

Governed by the `PHASE_MARGIN` MetricContract: closed-loop return-ratio
benchmark, unity loop-gain frequency, degrees.

Method (Tian injection, documented for the checkpoint): the testbench
closes the amplifier loop through a zero-DC-voltage AC injection source
(`assemble_loop_gain`). With the loop closed by an ideal source, nodal
analysis gives measured M = V(out)/V(in) = G(s) exactly — the open-loop
amplifier transfer at every frequency, independent of source polarity.
M(0) is negative-real (inverting stage), so the unity crossing below is
the amplifier's unity-gain frequency and PM = 180 - |arg(M)| there, with
the phase linearly interpolated between the bracketing sweep points
(same interpolation as `extract_bandwidth`; duplicated deliberately so
verified metric code stays untouched).

Cross-checks that must hold on real data (asserted live): |M| at f_min
equals the DC small-signal gain (two independent analyses agreeing), and
PM lands in the plausible window for the benchmark.
"""

from __future__ import annotations

import cmath
import math

from analog_ic_design.sim.ngspice import SimError
from analog_ic_design.sim.waveform import ACWaveform

_UNITY_GAIN = 1.0


def _deg(phase_rad: float) -> float:
    return float(math.degrees(phase_rad))


def extract_phase_margin(
    ac: ACWaveform,
    *,
    in_node: str = "in",
    out_node: str = "out",
) -> float:
    """Extract phase margin in degrees from a loop-gain AC response.

    Fails closed with `SimError` on empty/non-finite/non-monotonic data,
    zero input, a response that starts below unity, or one that never
    crosses unity within the sweep. A negative return means the loop is
    unstable (reported, not clamped).
    """
    if not ac.frequency:
        raise SimError("SPICE convergence: AC waveform has empty frequency vector")
    freqs = [float(f) for f in ac.frequency]
    if any(not math.isfinite(f) for f in freqs):
        raise SimError("SPICE convergence: non-finite frequency sample in AC response")
    if any(b <= a for a, b in zip(freqs, freqs[1:], strict=False)):
        raise SimError("SPICE convergence: AC frequency vector is not strictly increasing")

    in_vals = ac.trace(in_node).values
    out_vals = ac.trace(out_node).values
    if len(in_vals) != len(freqs) or len(out_vals) != len(freqs):
        raise SimError(
            "Schema: ragged AC vectors: "
            f"freq={len(freqs)} in={len(in_vals)} out={len(out_vals)}"
        )
    ratios: list[complex] = []
    for idx, (vi, vo) in enumerate(zip(in_vals, out_vals, strict=True)):
        if not all(map(math.isfinite, (vi.real, vi.imag, vo.real, vo.imag))):
            raise SimError(f"SPICE convergence: non-finite AC sample at index {idx}")
        if vi == 0j:
            raise SimError(f"SPICE convergence: zero loop-injection response at index {idx}")
        ratios.append(vo / vi)

    mags = [abs(r) for r in ratios]
    if mags[0] < _UNITY_GAIN:
        raise SimError(
            f"SPICE convergence: loop gain starts below unity ({mags[0]:.4f} V/V)"
        )
    for i in range(1, len(mags)):
        if mags[i] < _UNITY_GAIN:
            frac = (_UNITY_GAIN - mags[i - 1]) / (mags[i] - mags[i - 1])
            phase = _deg(cmath.phase(ratios[i - 1])) * (1.0 - frac) + _deg(
                cmath.phase(ratios[i])
            ) * frac
            return float(180.0 - abs(phase))
    raise SimError("SPICE convergence: loop gain never crosses unity within the sweep")
