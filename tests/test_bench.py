"""R0 tests: AnalogBench registry integrity + B0 inverter bench.

Registry assertions run everywhere (pure metadata). B0 without a backend
asserts fail-closed error data (base); B0 live asserts rail swing with
evidence (EDA only).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from analog_ic_design.bench import BENCHES, BenchResult, run_bench
from analog_ic_design.sim.ngspice import libngspice_available

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)


def test_registry_has_b0_through_b7_complete() -> None:
    assert sorted(BENCHES) == [f"B{i}" for i in range(8)]
    for bid, bench in BENCHES.items():
        assert bench.bench_id == bid
        assert bench.name and bench.circuit and bench.analyses
        assert bench.acceptance and bench.owner


def test_unknown_bench_fails_closed() -> None:
    with pytest.raises(ValueError, match="Schema"):
        run_bench("B9", db_path=":memory:")


def test_deferred_benches_raise_with_owner(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError, match="R0-2"):
        run_bench("B1", db_path=str(tmp_path / "b.sqlite"))


def test_b0_without_backend_reports_error(tmp_path: Path) -> None:
    result = run_bench("B0", db_path=str(tmp_path / "b0.sqlite"))
    assert isinstance(result, BenchResult)
    if libngspice_available():
        pytest.skip("backend present; fail-closed path covered on base")
    assert result.status == "error"
    assert "Schema" in result.message or "SimError" in result.message


@NEEDS_LIB
def test_b0_live_passes_with_evidence(tmp_path: Path) -> None:
    result = run_bench("B0", db_path=str(tmp_path / "b0live.sqlite"))
    assert result.status == "pass", result.message
    assert result.metrics["vout_min_v"] < 0.1
    assert result.metrics["vout_max_v"] > 1.7
    assert len(result.evidence) == 1 and len(result.evidence[0]) == 64
