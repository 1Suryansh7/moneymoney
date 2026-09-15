"""R0-5 B7a tests: bandgap tempco extractors (pure, hand-computed goldens).

No simulator: exact arithmetic on synthetic vectors plus fail-closed
rejections. Live vectors arrive in B7b.
"""

from __future__ import annotations

import math

import pytest

from analog_ic_design.metrics.tempco import compensated_vref, extract_tempco
from analog_ic_design.sim.ngspice import SimError


def test_compensated_vref_exact() -> None:
    assert compensated_vref([0.8, 0.7], [0.05, 0.06], k=9.0) == pytest.approx([1.25, 1.24])


def test_extract_tempco_box_golden() -> None:
    # Exact-decimal check: 0.01/1.245/165 × 1e6 = 10000/205.425 = 48.679566…
    assert extract_tempco([-40.0, 125.0], [1.25, 1.24]) == pytest.approx(48.67957, rel=1e-4)


def test_extract_tempco_flat_is_zero() -> None:
    assert extract_tempco([0.0, 100.0], [1.2, 1.2]) == 0.0


def test_compensated_vref_rejects_misaligned() -> None:
    with pytest.raises(SimError, match="aligned"):
        compensated_vref([0.8], [0.05, 0.06], k=9.0)
    with pytest.raises(SimError, match="aligned"):
        compensated_vref([], [], k=9.0)


def test_compensated_vref_rejects_bad_k() -> None:
    with pytest.raises(SimError, match="finite"):
        compensated_vref([0.8], [0.05], k=math.inf)


def test_compensated_vref_rejects_nonfinite() -> None:
    with pytest.raises(SimError, match="finite"):
        compensated_vref([0.8], [math.nan], k=9.0)


def test_extract_tempco_rejects_degenerate() -> None:
    with pytest.raises(SimError, match="2 aligned"):
        extract_tempco([25.0], [1.2])
    with pytest.raises(SimError, match="increasing"):
        extract_tempco([125.0, -40.0], [1.2, 1.3])
    with pytest.raises(SimError, match="increasing"):
        extract_tempco([25.0, 25.0], [1.2, 1.2])
    with pytest.raises(SimError, match="finite"):
        extract_tempco([0.0, 100.0], [1.2, math.inf])
    with pytest.raises(SimError, match="non-zero mean"):
        extract_tempco([0.0, 100.0], [-1.0, 1.0])
