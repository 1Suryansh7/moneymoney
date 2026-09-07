"""Average power extraction: VDD times mean supply current (Stage 3 Commit 3G).

Governed by the `POWER` MetricContract: time-averaged product of supply
voltage and supply current over an integration window, SI Watts (W).
Positive means power dissipated (current drawn from the positive supply
into the circuit).

Sign convention (measured, not assumed — probed 2026-09-07 in the pinned
EDA image: 1.8 V across 1 kΩ to ground gives `vdd#branch` = -1.8 mA):
ngspice reports a voltage source's branch current entering its positive
terminal, i.e. flowing OUT of the circuit back into the source. Supply
current INTO the circuit is therefore the NEGATED branch mean.
"""

from __future__ import annotations

import math

from analog_ic_design.sim.ngspice import SimError
from analog_ic_design.sim.waveform import Waveform


def extract_power(
    wave: Waveform,
    *,
    vdd_node: str = "vdd",
    branch_node: str | None = None,
    t_start: float | None = None,
    t_end: float | None = None,
) -> float:
    """Extract average dissipated power over an integration window.

    P = mean(V(vdd)) * mean(-I(branch)) across samples with
    t_start <= t <= t_end (defaults: whole waveform). Fails closed with
    `SimError` on empty/non-finite data, missing nodes, or an empty window.
    """
    if not wave.time:
        raise SimError("SPICE convergence: transient waveform has empty time vector")
    branch = branch_node if branch_node is not None else f"{vdd_node}#branch"
    try:
        v_vals = [float(v) for v in wave.trace(vdd_node).values]
        i_vals = [float(v) for v in wave.trace(branch).values]
    except KeyError as err:
        raise SimError(f"Schema: node absent from transient waveform: {err}") from err
    times = [float(t) for t in wave.time]
    if len(v_vals) != len(times) or len(i_vals) != len(times):
        raise SimError(
            "Schema: ragged transient vectors: "
            f"time={len(times)} vdd={len(v_vals)} branch={len(i_vals)}"
        )
    if any(not math.isfinite(t) for t in times):
        raise SimError("SPICE convergence: non-finite time sample in transient response")
    if any(not math.isfinite(v) for v in v_vals) or any(
        not math.isfinite(i) for i in i_vals
    ):
        raise SimError("SPICE convergence: non-finite supply sample in transient response")

    lo = t_start if t_start is not None else times[0]
    hi = t_end if t_end is not None else times[-1]
    idx = [k for k, t in enumerate(times) if lo <= t <= hi]
    if not idx:
        raise SimError(
            f"SPICE convergence: empty integration window [{lo!r}, {hi!r}]"
        )
    v_mean = sum(v_vals[k] for k in idx) / len(idx)
    i_mean = sum(i_vals[k] for k in idx) / len(idx)
    return float(v_mean * -i_mean)
