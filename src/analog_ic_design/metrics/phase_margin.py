"""Phase-margin extraction from a loop-gain response (Stage 3 Commit 3E).

Governed by the `PHASE_MARGIN` MetricContract: closed-loop return-ratio
benchmark, unity loop-gain frequency, signed degrees.

Method: the testbench closes the amplifier loop through a zero-DC-voltage
AC injection source (`assemble_loop_gain`). With the loop closed by an
ideal source, nodal analysis gives measured M = V(out)/V(in) = G(s) —
the open-loop amplifier transfer at every frequency. The extractor
unwraps the measured phasor phase along the frequency axis (VERIFY-PM-001:
principal-value `cmath.phase` wraps past ±180°, which fabricated PM=+155°
for a violently unstable Miller candidate in Stage 6F), then reports
PM = 180° − (lag accumulated from the DC phasor to the unity crossing).
Negative PM is instability data, never clamped. Classification bounds:
STABLE (PM >= 45°), MARGINAL (0° <= PM < 45°), UNSTABLE (PM < 0°).

Crossing authority: the first downward magnitude crossing through 1.0 V/V
uses the same linear fraction as `extract_bandwidth`, so the two functions
can never disagree on where unity gain is (final_build.md §2: one metric,
one meaning). Phase is interpolated with that same fraction on the
UNWRAPPED values — never across a branch cut.
"""

from __future__ import annotations

import cmath
import math
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from analog_ic_design.sim.ngspice import SimError
from analog_ic_design.sim.waveform import ACWaveform

_UNITY_GAIN = 1.0


class StabilityClassification(StrEnum):
    """Stability verdict accompanying every phase-margin measurement."""

    STABLE = "STABLE"  # PM >= 45 deg: robust transients.
    MARGINAL = "MARGINAL"  # 0 deg <= PM < 45 deg: ringing, peaking.
    UNSTABLE = "UNSTABLE"  # PM < 0 deg: oscillation, must not sign off.


@dataclass(frozen=True)
class PhaseMarginData:
    """Full phase-margin telemetry: signed value plus crossing context."""

    phase_margin_deg: float
    unity_gain_freq_hz: float
    phase_at_ugb_deg: float
    stability: StabilityClassification


def _deg(phase_rad: float) -> float:
    return float(math.degrees(phase_rad))


def unwrap_phase_degrees(phases_deg: Sequence[float]) -> list[float]:
    """Unwrap principal-value phases into a continuous trajectory.

    Detects jump discontinuities (|step| > 180°) and compensates ±360°
    cumulatively (identical to numpy.unwrap on radians). Inputs are
    principal values in (-180, 180], so consecutive differences stay
    within (-360, 360) and a single compensation per step suffices.
    """
    unwrapped: list[float] = []
    offset = 0.0
    prev_raw: float | None = None
    for raw in phases_deg:
        cur = float(raw)
        if prev_raw is not None:
            diff = cur - prev_raw
            if diff > 180.0:
                offset -= 360.0
            elif diff < -180.0:
                offset += 360.0
        unwrapped.append(cur + offset)
        prev_raw = cur
    return unwrapped


def classify_stability(pm_deg: float) -> StabilityClassification:
    """Classify a signed phase margin; never clamps the value itself."""
    if pm_deg >= 45.0:
        return StabilityClassification.STABLE
    if pm_deg >= 0.0:
        return StabilityClassification.MARGINAL
    return StabilityClassification.UNSTABLE


def extract_phase_margin_detailed(
    ac: ACWaveform,
    *,
    in_node: str = "in",
    out_node: str = "out",
) -> PhaseMarginData:
    """Extract signed phase margin with full crossing telemetry.

    PM = 180° − (unwrapped lag accumulated from the DC phasor to the
    first downward unity-magnitude crossing). Anchor-invariant: only
    phase differences enter, so the DC branch (+180° vs −180°) cannot
    skew the result. A negative return means the loop is unstable
    (reported, not clamped).
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
    unwrapped = unwrap_phase_degrees([_deg(cmath.phase(r)) for r in ratios])
    for i in range(1, len(mags)):
        if mags[i] < _UNITY_GAIN:
            frac = (_UNITY_GAIN - mags[i - 1]) / (mags[i] - mags[i - 1])
            f_lo, f_hi = freqs[i - 1], freqs[i]
            f_ugb = f_lo + frac * (f_hi - f_lo)
            phase_at_ugb = unwrapped[i - 1] + frac * (unwrapped[i] - unwrapped[i - 1])
            lag = unwrapped[0] - phase_at_ugb
            pm = 180.0 - lag
            return PhaseMarginData(
                phase_margin_deg=float(pm),
                unity_gain_freq_hz=float(f_ugb),
                phase_at_ugb_deg=float(phase_at_ugb),
                stability=classify_stability(float(pm)),
            )
    raise SimError("SPICE convergence: loop gain never crosses unity within the sweep")


def extract_phase_margin(
    ac: ACWaveform,
    *,
    in_node: str = "in",
    out_node: str = "out",
) -> float:
    """Extract signed phase margin in degrees from a loop-gain AC response.

    Backward-compatible float view of `extract_phase_margin_detailed`.
    Fails closed with `SimError` on empty/non-finite/non-monotonic data,
    zero input, a response that starts below unity, or one that never
    crosses unity within the sweep. A negative return means the loop is
    unstable (reported, not clamped).
    """
    return extract_phase_margin_detailed(ac, in_node=in_node, out_node=out_node).phase_margin_deg
