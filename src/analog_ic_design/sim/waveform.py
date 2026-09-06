"""Waveform parsing: transient (2F) and AC small-signal frequency response (3B).

Converts `RawSim` vector dicts into SI-typed, immutable structures. Unit
rule: branch-current vectors (ngspice names containing `#`, e.g. `v1#branch`)
become `Ampere`; the `time` vector becomes `Second`; `frequency` becomes
`Hertz`; every other node vector becomes `Volt` (or unitless ratio/admittance
as appropriate). Non-finite samples (diverged runs) fail closed as `SimError`.

- `parse_transient`: accepts only real transient data with a `time` vector.
  Rejects runs with complex data or missing time base.
- `parse_ac`: accepts frequency-domain AC data with a `frequency` vector
  and complex small-signal vectors.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass

from analog_ic_design.sim.ngspice import RawSim, SimError
from analog_ic_design.units.quantity import Ampere, Hertz, Quantity, Second, Volt


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


@dataclass(frozen=True)
class ACTrace:
    """One named AC small-signal frequency response: complex values."""

    name: str
    values: tuple[complex, ...]

    def magnitude(self) -> tuple[float, ...]:
        """Linear magnitude |V|."""
        return tuple(abs(c) for c in self.values)

    def magnitude_db(self) -> tuple[float, ...]:
        """Logarithmic magnitude in decibels: 20 * log10(|V|)."""
        return tuple(
            20.0 * math.log10(abs(c)) if abs(c) > 0.0 else float("-inf")
            for c in self.values
        )

    def phase_rad(self) -> tuple[float, ...]:
        """Phase angle in radians (-pi to +pi)."""
        return tuple(cmath.phase(c) for c in self.values)

    def phase_deg(self) -> tuple[float, ...]:
        """Phase angle in degrees (-180 to +180)."""
        return tuple(math.degrees(cmath.phase(c)) for c in self.values)

    def real(self) -> tuple[float, ...]:
        """Real component."""
        return tuple(c.real for c in self.values)

    def imag(self) -> tuple[float, ...]:
        """Imaginary component."""
        return tuple(c.imag for c in self.values)


@dataclass(frozen=True)
class ACWaveform:
    """One AC small-signal frequency response: SI frequency base + complex traces."""

    frequency: tuple[Hertz, ...]
    traces: tuple[ACTrace, ...]

    def trace(self, name: str) -> ACTrace:
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
    if raw.complex_vectors:
        raise SimError("Schema: complex data passed to parse_transient — expected real transient")
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


def parse_ac(raw: RawSim) -> ACWaveform:
    """Parse an AC small-signal `RawSim` into an `ACWaveform`."""
    if "frequency" not in raw.vectors and "frequency" not in raw.complex_vectors:
        raise SimError("Schema: no 'frequency' vector — expected AC small-signal data")
    raw_freqs = raw.vectors.get("frequency")
    if raw_freqs is None:
        raw_freqs = [c.real for c in raw.complex_vectors["frequency"]]
    if not raw_freqs:
        raise SimError("SPICE convergence: empty frequency vector")
    try:
        freqs = tuple(Hertz(f) for f in raw_freqs)
    except (ValueError, TypeError) as exc:
        raise SimError(f"SPICE convergence: non-finite frequency sample: {exc}") from exc
    if any(f < 0.0 for f in freqs):
        raise SimError("SPICE convergence: negative frequency in AC response")
    count = len(freqs)

    traces_dict: dict[str, list[complex]] = {}
    for name, samples in raw.complex_vectors.items():
        if name == "frequency":
            continue
        traces_dict[name] = samples
    for name, real_samples in raw.vectors.items():
        if name == "frequency" or name in traces_dict:
            continue
        traces_dict[name] = [complex(v, 0.0) for v in real_samples]

    traces: list[ACTrace] = []
    for name in sorted(traces_dict.keys()):
        samples = traces_dict[name]
        if len(samples) != count:
            raise SimError(f"SPICE convergence: ragged vector {name!r}")
        if any(not math.isfinite(c.real) or not math.isfinite(c.imag) for c in samples):
            raise SimError(f"SPICE convergence: non-finite sample in {name!r}")
        traces.append(ACTrace(name=name, values=tuple(samples)))
    return ACWaveform(frequency=freqs, traces=tuple(traces))
