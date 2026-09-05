"""Typed SI-base quantities (Stage 1 Commit 1A).

Every physical value in storage, schema, APIs, and algorithms is one of these
types, holding a float in SI base units. Plain `float` carries no unit and
must not cross a typed boundary unwrapped.

Honest limits (read before extending):
- Arithmetic yields plain `float` (e.g. `Farad(1.0) + Farad(2.0)` is `3.0`,
  not `Farad`). Re-wrap at API boundaries; mypy enforces the annotations.
- Only finiteness is validated here. Sign/domain rules (e.g. W/L minima)
  belong to the Stage 1F validator, not to this shell.
- `Kelvin` covers absolute temperatures and temperature deltas alike, so its
  sign is unconstrained here for the same reason.
"""

from __future__ import annotations

import math
from typing import ClassVar, Self


class UnitError(ValueError):
    """A value breached the SI unit contract. Failure taxonomy: Schema."""


class Quantity(float):
    """Base SI quantity: a finite float. Never NaN/inf, never non-numeric."""

    __slots__ = ()
    symbol: ClassVar[str] = ""

    def __new__(cls, value: float | int) -> Self:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise UnitError(
                f"Schema: {cls.__name__} requires a numeric SI value, got {type(value).__name__}"
            )
        magnitude = float(value)
        if not math.isfinite(magnitude):
            raise UnitError(f"Schema: {cls.__name__} requires a finite value, got {value!r}")
        return super().__new__(cls, magnitude)


class Farad(Quantity):
    """Capacitance in farads (F)."""

    __slots__ = ()
    symbol: ClassVar[str] = "F"


class Ohm(Quantity):
    """Resistance in ohms (Ω)."""

    __slots__ = ()
    symbol: ClassVar[str] = "Ω"


class Hertz(Quantity):
    """Frequency in hertz (Hz)."""

    __slots__ = ()
    symbol: ClassVar[str] = "Hz"


class Volt(Quantity):
    """Voltage in volts (V)."""

    __slots__ = ()
    symbol: ClassVar[str] = "V"


class Ampere(Quantity):
    """Current in amperes (A)."""

    __slots__ = ()
    symbol: ClassVar[str] = "A"


class Second(Quantity):
    """Time in seconds (s)."""

    __slots__ = ()
    symbol: ClassVar[str] = "s"


class Meter(Quantity):
    """Length/width in meters (m)."""

    __slots__ = ()
    symbol: ClassVar[str] = "m"


class Kelvin(Quantity):
    """Temperature in kelvin (K); absolute values and deltas alike."""

    __slots__ = ()
    symbol: ClassVar[str] = "K"
