"""R0 tests: AnalogBench registry integrity + B0/B1/B2/B3 benches.

Registry assertions run everywhere (pure metadata). Benches without a
backend assert fail-closed error data (base); live benches assert measured
behavior with evidence (EDA only).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from analog_ic_design.bench import BENCHES, BenchResult, run_bench
from analog_ic_design.circuit import validate
from analog_ic_design.sim.cascode import build_cascode
from analog_ic_design.sim.cs_amp import build_cs_amplifier
from analog_ic_design.sim.diff_pair import build_diff_pair
from analog_ic_design.sim.folded_cascode import build_folded_cascode
from analog_ic_design.sim.mirror import build_mirror
from analog_ic_design.sim.ngspice import libngspice_available
from analog_ic_design.store.schema import connect, migrate

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
    with pytest.raises(NotImplementedError, match="R0-4"):
        run_bench("B6", db_path=str(tmp_path / "b.sqlite"))


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


def test_b1_fixture_validates_without_backend(tmp_path: Path) -> None:
    """Mirror cell passes the pre-simulation gate with no simulator."""
    conn = connect(str(tmp_path / "b1fix.sqlite"))
    try:
        migrate(conn)
        cell = build_mirror(conn)
        report = validate(conn, cell)
    finally:
        conn.close()
    assert report.valid, [v.message for v in report.violations]


def test_b1_without_backend_reports_error(tmp_path: Path) -> None:
    result = run_bench("B1", db_path=str(tmp_path / "b1.sqlite"))
    assert isinstance(result, BenchResult)
    if libngspice_available():
        pytest.skip("backend present; fail-closed path covered on base")
    assert result.status == "error"
    assert "Schema" in result.message or "SimError" in result.message


@NEEDS_LIB
def test_b1_live_passes_with_evidence(tmp_path: Path) -> None:
    result = run_bench("B1", db_path=str(tmp_path / "b1live.sqlite"))
    assert result.status == "pass", result.message
    assert 0.8 <= result.metrics["mirror_ratio"] <= 1.2
    assert result.metrics["mirror_ratio"] > result.metrics["mirror_ratio_triode"]
    assert len(result.evidence) == 1 and len(result.evidence[0]) == 64


def test_b2_fixture_validates_without_backend(tmp_path: Path) -> None:
    """Diff-pair cell passes the pre-simulation gate with no simulator."""
    conn = connect(str(tmp_path / "b2fix.sqlite"))
    try:
        migrate(conn)
        cell = build_diff_pair(conn)
        report = validate(conn, cell)
    finally:
        conn.close()
    assert report.valid, [v.message for v in report.violations]


def test_b2_without_backend_reports_error(tmp_path: Path) -> None:
    result = run_bench("B2", db_path=str(tmp_path / "b2.sqlite"))
    assert isinstance(result, BenchResult)
    if libngspice_available():
        pytest.skip("backend present; fail-closed path covered on base")
    assert result.status == "error"
    assert "Schema" in result.message or "SimError" in result.message


@NEEDS_LIB
def test_b2_live_passes_with_evidence(tmp_path: Path) -> None:
    result = run_bench("B2", db_path=str(tmp_path / "b2live.sqlite"))
    assert result.status == "pass", result.message
    assert 3.0 < result.metrics["gain_outn"] < 30.0
    assert result.metrics["gain_outp"] < 2.0
    assert len(result.evidence) == 1 and len(result.evidence[0]) == 64


def test_b3_fixture_validates_without_backend(tmp_path: Path) -> None:
    """CS-amp cell passes the pre-simulation gate with no simulator."""
    conn = connect(str(tmp_path / "b3fix.sqlite"))
    try:
        migrate(conn)
        cell = build_cs_amplifier(conn)
        report = validate(conn, cell)
    finally:
        conn.close()
    assert report.valid, [v.message for v in report.violations]


def test_b3_without_backend_reports_error(tmp_path: Path) -> None:
    result = run_bench("B3", db_path=str(tmp_path / "b3.sqlite"))
    assert isinstance(result, BenchResult)
    if libngspice_available():
        pytest.skip("backend present; fail-closed path covered on base")
    assert result.status == "error"
    assert "Schema" in result.message or "SimError" in result.message


@NEEDS_LIB
def test_b3_live_passes_with_evidence(tmp_path: Path) -> None:
    result = run_bench("B3", db_path=str(tmp_path / "b3live.sqlite"))
    assert result.status == "pass", result.message
    assert result.metrics["dc_gain"] > 5.0
    assert result.metrics["vout_min_v"] < 0.1
    assert result.metrics["vout_max_v"] > 1.7
    rel = abs(result.metrics["dc_gain"] - result.metrics["ac_gain"])
    rel /= result.metrics["dc_gain"]
    assert rel < 0.10
    assert len(result.evidence) == 1 and len(result.evidence[0]) == 64


def test_b4_fixture_validates_without_backend(tmp_path: Path) -> None:
    """Cascode cell passes the pre-simulation gate with no simulator."""
    conn = connect(str(tmp_path / "b4fix.sqlite"))
    try:
        migrate(conn)
        cell = build_cascode(conn)
        report = validate(conn, cell)
    finally:
        conn.close()
    assert report.valid, [v.message for v in report.violations]


def test_b4_without_backend_reports_error(tmp_path: Path) -> None:
    result = run_bench("B4", db_path=str(tmp_path / "b4.sqlite"))
    assert isinstance(result, BenchResult)
    if libngspice_available():
        pytest.skip("backend present; fail-closed path covered on base")
    assert result.status == "error"
    assert "Schema" in result.message or "SimError" in result.message


@NEEDS_LIB
def test_b4_live_passes_with_evidence(tmp_path: Path) -> None:
    result = run_bench("B4", db_path=str(tmp_path / "b4live.sqlite"))
    assert result.status == "pass", result.message
    assert result.metrics["ac_gain"] > 10.0
    assert result.metrics["vout_min_v"] < 0.1
    assert result.metrics["vout_max_v"] > 1.7
    assert result.metrics["headroom_v"] > 0.1
    assert len(result.evidence) == 1 and len(result.evidence[0]) == 64


def test_b5_fixture_validates_without_backend(tmp_path: Path) -> None:
    """Folded-cascode OTA cell passes the pre-simulation gate with no simulator."""
    conn = connect(str(tmp_path / "b5fix.sqlite"))
    try:
        migrate(conn)
        cell = build_folded_cascode(conn)
        report = validate(conn, cell)
    finally:
        conn.close()
    assert report.valid, [v.message for v in report.violations]


def test_b5_without_backend_reports_error(tmp_path: Path) -> None:
    result = run_bench("B5", db_path=str(tmp_path / "b5.sqlite"))
    assert isinstance(result, BenchResult)
    if libngspice_available():
        pytest.skip("backend present; fail-closed path covered on base")
    assert result.status == "error"
    assert "Schema" in result.message or "SimError" in result.message


@NEEDS_LIB
def test_b5_live_passes_with_evidence(tmp_path: Path) -> None:
    result = run_bench("B5", db_path=str(tmp_path / "b5live.sqlite"))
    assert result.status == "pass", result.message
    assert result.metrics["ac_gain"] > 10.0
    assert 1e3 < result.metrics["ugb_hz"] < 1e9
    assert result.metrics["vout_min_v"] < 0.1
    assert result.metrics["vout_max_v"] > 1.7
    assert len(result.evidence) == 1 and len(result.evidence[0]) == 64
