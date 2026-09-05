"""Stage 1 Commit 1A tests: the SI unit contract.

Headline claim: a unit string such as "10MHz" can never reach storage —
construction rejects it with `UnitError` (taxonomy: Schema). Formatting is
covered as display-layer behavior with exact expected strings.
"""

from __future__ import annotations

import pytest

from analog_ic_design.units import (
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
    format_quantity,
)

TYPES: tuple[type[Quantity], ...] = (Farad, Ohm, Hertz, Volt, Ampere, Second, Meter, Kelvin)
BAD_VALUES: tuple[object, ...] = (
    "10MHz",
    "10k",
    "2.5pF",
    "",
    None,
    True,
    float("nan"),
    float("inf"),
)


@pytest.mark.parametrize("cls", TYPES)
def test_construction_preserves_exact_si_value(cls: type[Quantity]) -> None:
    assert float(cls(1.8)) == 1.8
    assert float(cls(3)) == 3.0
    assert isinstance(cls(1.0), (Quantity, float))
    assert cls.symbol != ""


@pytest.mark.parametrize("cls", TYPES)
@pytest.mark.parametrize("bad", BAD_VALUES)
def test_non_numeric_and_non_finite_rejected(cls: type[Quantity], bad: object) -> None:
    with pytest.raises(UnitError):
        cls(bad)  # type: ignore[arg-type]


def test_headline_unit_strings_never_reach_storage() -> None:
    with pytest.raises(UnitError):
        Hertz("10MHz")  # type: ignore[arg-type]
    with pytest.raises(UnitError):
        Ohm("10k")  # type: ignore[arg-type]
    with pytest.raises(UnitError):
        Farad("2.5pF")  # type: ignore[arg-type]


def test_unit_error_is_catch_compatible_value_error() -> None:
    assert issubclass(UnitError, ValueError)


def test_quantities_are_immutable() -> None:
    with pytest.raises(AttributeError):
        Farad(1.0).symbol = "X"  # type: ignore[misc]


def test_quantity_types_are_runtime_distinct() -> None:
    assert not isinstance(Farad(1.0), Ohm)
    assert not isinstance(Hertz(1.0), Second)
    assert type(Farad(1.0)) is Farad
    assert type(Ohm(1.0)) is Ohm


def test_arithmetic_yields_plain_float_by_design() -> None:
    result = Farad(1.0) + Farad(2.0)
    assert type(result) is float and result == 3.0


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Hertz(10e6), "10 MHz"),
        (Farad(2.5e-12), "2.5 pF"),
        (Volt(1.8), "1.8 V"),
        (Meter(180e-9), "180 nm"),
        (Ohm(1e3), "1 kΩ"),
        (Second(2.2e-3), "2.2 ms"),
        (Kelvin(300.0), "300 K"),
        (Ampere(1e-3), "1 mA"),
        (Farad(0.0), "0 F"),
        (Volt(-3.3), "-3.3 V"),
    ],
)
def test_display_formatting(value: Quantity, expected: str) -> None:
    assert format_quantity(value) == expected
