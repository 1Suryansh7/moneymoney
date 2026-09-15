"""Stage 4.5 Commit 4.5A tests: Corner vocabulary and deck plumbing.

Pure-Python unit tests: run on base image with zero skips. Deck assertions
prove the SI boundary (Kelvin in, Celsius out) and corner precedence.
"""

from __future__ import annotations

import pytest

from analog_ic_design.robust import (
    FAST_5_CORNER_ENVELOPE,
    FULL_45_CORNER_MATRIX,
    Corner,
)
from analog_ic_design.sim.testbench import assemble_ac, assemble_temp_sweep


def test_corner_rejects_nonsense() -> None:
    with pytest.raises(ValueError, match="non-empty name"):
        Corner(name="", process="tt", vdd=1.8, temperature=300.15)
    with pytest.raises(ValueError, match="unknown process section"):
        Corner(name="x", process="xx", vdd=1.8, temperature=300.15)
    with pytest.raises(ValueError, match="positive Kelvin"):
        Corner(name="x", process="tt", vdd=1.8, temperature=0.0)
    with pytest.raises(ValueError, match="positive voltage"):
        Corner(name="x", process="tt", vdd=0.0, temperature=300.15)
    with pytest.raises(ValueError, match="finite SI number"):
        Corner(name="x", process="tt", vdd=1.8, temperature=float("inf"))


def test_temp_celsius_boundary() -> None:
    spot = Corner(name="t", process="tt", vdd=1.8, temperature=300.15)
    assert spot.temp_celsius() == 27.0
    cold = Corner(name="c", process="ff", vdd=1.98, temperature=233.15)
    assert cold.temp_celsius() == pytest.approx(-40.0)


def test_fast_5_envelope() -> None:
    assert [(c.process, c.vdd, c.temperature) for c in FAST_5_CORNER_ENVELOPE] == [
        ("tt", 1.80, 300.15),
        ("ff", 1.98, 233.15),
        ("ss", 1.62, 398.15),
        ("fs", 1.80, 233.15),
        ("sf", 1.80, 398.15),
    ]
    assert len({c.name for c in FAST_5_CORNER_ENVELOPE}) == 5


def test_full_45_matrix_defined_only() -> None:
    assert len(FULL_45_CORNER_MATRIX) == 45
    assert len({c.name for c in FULL_45_CORNER_MATRIX}) == 45
    assert {c.process for c in FULL_45_CORNER_MATRIX} == {"tt", "ss", "ff", "sf", "fs"}


def test_corner_deck_replaces_lib_section_and_supply() -> None:
    corner = Corner(name="ss_125C_1.62V", process="ss", vdd=1.62, temperature=398.15)
    deck = assemble_ac(
        "* cell x\nXm1 a b\n.end\n",
        libs=[("/models/sky130.lib.spice", "tt")],
        corner=corner,
    )
    assert deck.count(".lib '") == 1
    assert ".lib '/models/sky130.lib.spice' ss\n" in deck
    assert ".temp 125.00\n" in deck
    assert "VDD vdd 0 DC 1.62\n" in deck


def test_corner_without_libs_fails_closed() -> None:
    corner = Corner(name="ss", process="ss", vdd=1.62, temperature=398.15)
    with pytest.raises(ValueError, match="requires a .lib path"):
        assemble_ac("* cell x\nXm1 a b\n.end\n", libs=[], corner=corner)


def test_temp_sweep_deck_nominal() -> None:
    deck = assemble_temp_sweep(
        "* cell x\nXm1 a b\n.end\n", libs=[("/models/sky130.lib.spice", "tt")]
    )
    assert ".dc temp -40.0 125.0 5.0\n" in deck
    assert "VDD vdd 0 DC 1.8\n" in deck
    assert ".temp " not in deck
    assert deck.endswith(".end\n")


def test_temp_sweep_deck_corner_follows_lib_and_supply() -> None:
    corner = Corner(name="ss_125C_1.62V", process="ss", vdd=1.62, temperature=398.15)
    deck = assemble_temp_sweep(
        "* cell x\nXm1 a b\n.end\n",
        libs=[("/models/sky130.lib.spice", "tt")],
        corner=corner,
    )
    assert ".lib '/models/sky130.lib.spice' ss\n" in deck
    assert "VDD vdd 0 DC 1.62\n" in deck
    # The sweep owns temperature: no single-point .temp line may fight it.
    assert ".temp " not in deck
    assert ".dc temp -40.0 125.0 5.0\n" in deck
