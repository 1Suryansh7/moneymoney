"""Transient waveform parsing (Stage 2 Commit 2F).

Converts `RawSim` vector dicts into SI-typed, immutable structures. Unit
rule: branch-current vectors (ngspice names containing `#`, e.g. `v1#branch`)
become `Ampere`; the `time` vector becomes `Second`; every other vector
becomes `Volt`. Non-finite samples (diverged runs) fail closed as `SimError`,
never as a bare `UnitError` leak — the caller needs the taxonomy category.

Only transient data is accepted (`parse_transient`); anything without a
`time` vector is the wrong analysis kind, not a parseable waveform.
"""

from __future__ import annotations

from dataclasses import dataclass

from analog_ic_design.sim.ngspice import RawSim, SimError
from analog_ic_design.units.quantity import Ampere, Quantity, Second, Volt


@dataclass(frozen=True)
class Trace:
    """One named signal: SI-typed samples sharing one unit."""

    name: str
    values: tuple[Quantity, ...]


@dataclass(frozen=True)
class Waveform:
    """One transient result: SI time base plus named traces."""

    time: tuple[Second, ...]
    traces: tuple[Trace, ...]

    def trace(self, name: str) -> Trace:
        """Return the trace called `name`; `KeyError` if absent."""
        for item in self.traces:
            if item.name == name:
                return item
        raise KeyError(f"unknown trace {name!r}")


def _typed(name: str, samples: list[float]) -> Trace:
    cls = Ampere if "#" in name else Volt
    try:
        values = tuple(cls(v) for v in samples)
    except (ValueError, TypeError) as exc:
        raise SimError(f"SPICE convergence: non-finite sample in {name!r}: {exc}") from exc
    return Trace(name=name, values=values)


def parse_transient(raw: RawSim) -> Waveform:
    """Parse a transient `RawSim` into a `Waveform` (all vectors same length)."""
    if "time" not in raw.vectors:
        raise SimError("Schema: no 'time' vector — expected transient data")
    if not raw.vectors["time"]:
        raise SimError("SPICE convergence: empty time vector")
    count = len(raw.vectors["time"])
    for name, samples in raw.vectors.items():
        if len(samples) != count:
            raise SimError(f"SPICE convergence: ragged vector {name!r}")
    try:
        times = tuple(Second(t) for t in raw.vectors["time"])
    except (ValueError, TypeError) as exc:
        raise SimError(f"SPICE convergence: non-finite time sample: {exc}") from exc
    traces = tuple(
        _typed(name, samples) for name, samples in sorted(raw.vectors.items()) if name != "time"
    )
    return Waveform(time=times, traces=traces)
