"""Slew-rate extraction: large-signal voltage transition slope (Stage 3 Commit 3F).

Governed by the `SLEW_RATE` MetricContract: 20% to 80% output transition window,
linear interpolation between threshold crossings.
Units: V/s (positive float).
"""

from __future__ import annotations

import math

from analog_ic_design.sim.ngspice import SimError
from analog_ic_design.sim.waveform import Waveform


def _interpolate_crossing(
    t1: float,
    v1: float,
    t2: float,
    v2: float,
    v_target: float,
) -> float:
    """Linearly interpolate the time where voltage crosses v_target."""
    if v2 == v1:
        return t1
    frac = (v_target - v1) / (v2 - v1)
    return float(t1 + frac * (t2 - t1))


def _validate_waveform(
    wave: Waveform,
    out_node: str,
) -> tuple[list[float], list[float]]:
    """Validate transient waveform vectors fail-closed against corruption."""
    if not wave.time:
        raise SimError("SPICE convergence: transient waveform has empty time vector")
    times = [float(t) for t in wave.time]
    if any(not math.isfinite(t) for t in times):
        raise SimError("SPICE convergence: non-finite time sample in transient response")
    if any(b <= a for a, b in zip(times, times[1:], strict=False)):
        raise SimError("SPICE convergence: time vector is not strictly increasing")

    try:
        trace = wave.trace(out_node)
    except KeyError as err:
        raise SimError(f"Schema: node {out_node!r} absent from transient waveform") from err

    values = [float(v) for v in trace.values]
    if len(values) != len(times):
        raise SimError(
            f"Schema: ragged transient vectors: time={len(times)} out={len(values)}"
        )
    if any(not math.isfinite(v) for v in values):
        raise SimError("SPICE convergence: non-finite output sample in transient response")

    v_min, v_max = min(values), max(values)
    delta_v = v_max - v_min
    if delta_v < 0.1:
        raise SimError(
            f"SPICE convergence: output swing negligible ({delta_v:.4f} V < 0.1 V)"
        )

    return times, values


def extract_rising_slew_rate(
    wave: Waveform,
    *,
    out_node: str = "out",
    v_start: float | None = None,
    v_stop: float | None = None,
    low_frac: float = 0.20,
    high_frac: float = 0.80,
) -> float:
    """Extract rising slew rate: slope between low_frac (20%) and high_frac (80%)
    of total step height. Units: V/s (positive float).
    """
    times, values = _validate_waveform(wave, out_node)
    if v_start is not None and v_stop is not None:
        v_min, v_max = min(v_start, v_stop), max(v_start, v_stop)
    else:
        v_min, v_max = min(values), max(values)
    delta_v = v_max - v_min

    v_lo = v_min + low_frac * delta_v
    v_hi = v_min + high_frac * delta_v

    t_lo: float | None = None
    t_hi: float | None = None

    for i in range(1, len(values)):
        v_prev, v_curr = values[i - 1], values[i]
        t_prev, t_curr = times[i - 1], times[i]

        # First upward crossing through v_lo
        if t_lo is None and v_prev <= v_lo and v_curr > v_lo:
            t_lo = _interpolate_crossing(t_prev, v_prev, t_curr, v_curr, v_lo)

        # Subsequent upward crossing through v_hi
        if t_lo is not None and v_prev <= v_hi and v_curr >= v_hi:
            t_hi = _interpolate_crossing(t_prev, v_prev, t_curr, v_curr, v_hi)
            break

    if t_lo is None or t_hi is None or t_hi <= t_lo:
        raise SimError("SPICE convergence: output does not reach 80% threshold for rising edge")

    return float((v_hi - v_lo) / (t_hi - t_lo))


def extract_falling_slew_rate(
    wave: Waveform,
    *,
    out_node: str = "out",
    v_start: float | None = None,
    v_stop: float | None = None,
    low_frac: float = 0.20,
    high_frac: float = 0.80,
) -> float:
    """Extract falling slew rate: slope between high_frac (80%) and low_frac (20%)
    of total step height. Units: V/s (positive float).
    """
    times, values = _validate_waveform(wave, out_node)
    if v_start is not None and v_stop is not None:
        v_min, v_max = min(v_start, v_stop), max(v_start, v_stop)
    else:
        v_min, v_max = min(values), max(values)
    delta_v = v_max - v_min

    v_lo = v_min + low_frac * delta_v
    v_hi = v_min + high_frac * delta_v

    t_hi: float | None = None
    t_lo: float | None = None

    for i in range(1, len(values)):
        v_prev, v_curr = values[i - 1], values[i]
        t_prev, t_curr = times[i - 1], times[i]

        # First downward crossing through v_hi
        if t_hi is None and v_prev >= v_hi and v_curr < v_hi:
            t_hi = _interpolate_crossing(t_prev, v_prev, t_curr, v_curr, v_hi)

        # Subsequent downward crossing through v_lo
        if t_hi is not None and v_prev >= v_lo and v_curr <= v_lo:
            t_lo = _interpolate_crossing(t_prev, v_prev, t_curr, v_curr, v_lo)
            break

    if t_hi is None or t_lo is None or t_lo <= t_hi:
        raise SimError("SPICE convergence: output does not reach 80% threshold for falling edge")

    return float((v_hi - v_lo) / (t_lo - t_hi))




def extract_slew_rate(
    wave: Waveform,
    *,
    out_node: str = "out",
    edge: str = "both",
    v_start: float | None = None,
    v_stop: float | None = None,
    low_frac: float = 0.20,
    high_frac: float = 0.80,
) -> float:
    """Extract slew rate under large-signal step excitation.

    If edge="rising", returns rising slew rate.
    If edge="falling", returns falling slew rate.
    If edge="both", returns min(rising, falling) if both present, or the single
    detected edge rate. Units: V/s (positive float).
    """
    _validate_waveform(wave, out_node)

    if edge == "rising":
        return extract_rising_slew_rate(
            wave,
            out_node=out_node,
            v_start=v_start,
            v_stop=v_stop,
            low_frac=low_frac,
            high_frac=high_frac,
        )
    if edge == "falling":
        return extract_falling_slew_rate(
            wave,
            out_node=out_node,
            v_start=v_start,
            v_stop=v_stop,
            low_frac=low_frac,
            high_frac=high_frac,
        )
    if edge == "both":
        sr_rise: float | None = None
        sr_fall: float | None = None
        try:
            sr_rise = extract_rising_slew_rate(
                wave,
                out_node=out_node,
                v_start=v_start,
                v_stop=v_stop,
                low_frac=low_frac,
                high_frac=high_frac,
            )
        except SimError:
            pass
        try:
            sr_fall = extract_falling_slew_rate(
                wave,
                out_node=out_node,
                v_start=v_start,
                v_stop=v_stop,
                low_frac=low_frac,
                high_frac=high_frac,
            )
        except SimError:
            pass

        if sr_rise is not None and sr_fall is not None:
            return min(sr_rise, sr_fall)
        if sr_rise is not None:
            return sr_rise
        if sr_fall is not None:
            return sr_fall
        raise SimError("SPICE convergence: output does not reach 80% threshold on any edge")

    raise ValueError(f"unknown edge option: {edge!r}; expected 'rising', 'falling', or 'both'")


