"""SI-prefix display formatting — DISPLAY LAYER ONLY.

Human-readable strings (`10 MHz`, `2.5 pF`) are produced here and NOWHERE
else. Engine, schema, simulator, and measurement code must never import this
module: if you are formatting a quantity outside a UI/report boundary, you
are building the string-coercion path the architecture forbids.

There is deliberately NO parser here. Prefix parsing (`10MHz` -> `Hertz`)
lives at the future UI input boundary (Stage 7), not in the kernel: a kernel
parser would legitimize unit strings inside the system. Until then, strings
are rejected at construction (see `Quantity.__new__` + `test_units.py`).
"""

from __future__ import annotations

from analog_ic_design.units.quantity import Quantity

_PREFIXES: tuple[tuple[float, str], ...] = (
    (1e12, "T"),
    (1e9, "G"),
    (1e6, "M"),
    (1e3, "k"),
    (1.0, ""),
    (1e-3, "m"),
    (1e-6, "µ"),
    (1e-9, "n"),
    (1e-12, "p"),
    (1e-15, "f"),
)


def format_quantity(value: Quantity) -> str:
    """Render `value` with the largest prefix keeping the scaled magnitude.

    Examples: `Hertz(10e6)` -> `"10 MHz"`, `Farad(2.5e-12)` -> `"2.5 pF"`,
    `Volt(0.0)` -> `"0 V"`. Values below 1 f-unit stay in femto.
    """
    symbol = type(value).symbol
    if float(value) == 0.0:
        return f"0 {symbol}"
    magnitude = abs(float(value))
    for scale, prefix in _PREFIXES:
        if magnitude >= scale:
            return f"{float(value) / scale:g} {prefix}{symbol}"
    return f"{float(value) / 1e-15:g} f{symbol}"
