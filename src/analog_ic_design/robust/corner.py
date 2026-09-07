"""PVT corner definitions (Stage 4.5 Commit 4.5A).

A `Corner` binds one process section, one supply voltage, and one
temperature — all stored SI (Volts, Kelvin); Celsius appears only in the
emitted deck (ADR-020 boundary law). Valid process sections are exactly
the five canonical MOS corners quoted from
`sky130.lib.spice` (`.lib tt/sf/ff/ss/fs` blocks).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_VALID_PROCESSES = frozenset({"tt", "ss", "ff", "sf", "fs"})


@dataclass(frozen=True)
class Corner:
    """One PVT evaluation point: process section + supply + temperature."""

    name: str
    process: str
    vdd: float
    temperature: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Schema: corner needs a non-empty name")
        if self.process not in _VALID_PROCESSES:
            raise ValueError(
                f"Schema: unknown process section {self.process!r}"
                f" (expected one of {sorted(_VALID_PROCESSES)})"
            )
        for label, value in (("vdd", self.vdd), ("temperature", self.temperature)):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise ValueError(f"Schema: corner {label} is not a finite SI number")
        if float(self.temperature) <= 0.0:
            raise ValueError("Schema: corner temperature must be positive Kelvin")
        if float(self.vdd) <= 0.0:
            raise ValueError("Schema: corner supply must be a positive voltage")

    def temp_celsius(self) -> float:
        """Deck-boundary conversion: Kelvin to Celsius for `.temp`."""
        return float(self.temperature) - 273.15


def _corner(process: str, temp_k: float, vdd: float) -> Corner:
    temp_c = temp_k - 273.15
    return Corner(
        name=f"{process}_{temp_c:.0f}C_{vdd:.2f}V",
        process=process,
        vdd=float(vdd),
        temperature=float(temp_k),
    )


#: Fast 5-corner envelope (live-simulated): TT nominal, FF cold/high-VDD,
#: SS hot/low-VDD, plus the two skew corners at nominal supply.
FAST_5_CORNER_ENVELOPE: tuple[Corner, ...] = (
    _corner("tt", 300.15, 1.80),
    _corner("ff", 233.15, 1.98),
    _corner("ss", 398.15, 1.62),
    _corner("fs", 233.15, 1.80),
    _corner("sf", 398.15, 1.80),
)

_SUPPLIES = (1.62, 1.80, 1.98)
_TEMPS_K = (233.15, 300.15, 398.15)

#: Full 45-corner matrix: defined and unit-tested only (5 process x 3
#: supplies x 3 temps). Live runs stay on the envelope to bound CI time.
FULL_45_CORNER_MATRIX: tuple[Corner, ...] = tuple(
    _corner(process, temp, vdd)
    for process in ("tt", "ss", "ff", "sf", "fs")
    for vdd in _SUPPLIES
    for temp in _TEMPS_K
)
