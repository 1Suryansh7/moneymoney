"""Settling-time extraction: last band violation after a step (Stage 3 Commit 3I).

Governed by the `SETTLING_TIME` MetricContract: time from step initiation
until the output enters and permanently stays within `band` (default 1%)
of the step height around the final value. SI seconds (s).

Final value defaults to the mean of the last 10% of samples (steady-state
estimator); pass `v_final` explicitly when the window is known settled.
The step height derives from the first sample at or after `t0`.
"""

from __future__ import annotations

import math

from analog_ic_design.sim.ngspice import SimError
from analog_ic_design.sim.waveform import Waveform


def extract_settling_time(
    wave: Waveform,
    *,
    out_node: str = "out",
    t0: float,
    band: float = 0.01,
    v_final: float | None = None,
) -> float:
    """Extract settling time after a step at `t0`.

    Returns t_settle - t0 where t_settle is the last time at or after `t0`
    with |V(out) - V_final| above `band` times the step height (0.0 when
    already settled at `t0`). Fails closed with `SimError` on empty /
    non-finite / missing data, no samples at or after `t0`, a zero-height
    step, or a window ending outside the band.
    """
    if not wave.time:
        raise SimError("SPICE convergence: transient waveform has empty time vector")
    if not math.isfinite(t0):
        raise SimError(f"Schema: step time t0 is not finite ({t0!r})")
    if not math.isfinite(band) or band <= 0.0:
        raise SimError(f"Schema: error band is not a positive fraction ({band!r})")
    try:
        values = [float(v) for v in wave.trace(out_node).values]
    except KeyError as err:
        raise SimError(f"Schema: node {out_node!r} absent from transient waveform") from err
    times = [float(t) for t in wave.time]
    if len(values) != len(times):
        raise SimError(
            f"Schema: ragged transient vectors: time={len(times)} out={len(values)}"
        )
    if any(not math.isfinite(t) for t in times) or any(
        not math.isfinite(v) for v in values
    ):
        raise SimError("SPICE convergence: non-finite sample in transient response")

    post = [k for k, t in enumerate(times) if t >= t0]
    if not post:
        raise SimError(f"SPICE convergence: no samples at or after t0 ({t0!r})")
    tail = max(1, len(values) // 10)
    final = v_final if v_final is not None else sum(values[-tail:]) / tail
    if not math.isfinite(final):
        raise SimError("SPICE convergence: non-finite final-value estimate")
    step_height = abs(final - values[post[0]])
    if step_height == 0.0:
        raise SimError("SPICE convergence: zero-height step has no settling time")
    limit = band * step_height

    if abs(values[post[-1]] - final) > limit:
        raise SimError("SPICE convergence: waveform ends outside the error band")
    settled_at = t0
    for k in post:
        if abs(values[k] - final) > limit:
            settled_at = times[k]
    return float(settled_at - t0)
