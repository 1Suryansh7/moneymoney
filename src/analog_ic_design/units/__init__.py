"""Strict SI-base physical units system (Stage 1 Commit 1A — live).

`quantity` holds the validated types; `display` holds the display-layer-only
formatter (never import it from engine/schema/simulator code).
"""

from analog_ic_design.units.display import format_quantity
from analog_ic_design.units.quantity import (
    Ampere,
    Farad,
    Hertz,
    Kelvin,
    Meter,
    Ohm,
    Quantity,
    Second,
    UnitError,
    Volt,
)

__all__ = [
    "Ampere",
    "Farad",
    "Hertz",
    "Kelvin",
    "Meter",
    "Ohm",
    "Quantity",
    "Second",
    "UnitError",
    "Volt",
    "format_quantity",
]
