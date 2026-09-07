"""Stage 4.5 Commit 4.5C tests: protocol, Wilson CI, robustness report.

Pure-math and validation tests run on base image with zero skips.
Live Monte Carlo report on `cs_amp_nmos` (seeded geometric perturbation,
DC gain threshold) runs under `@NEEDS_LIB`. Counts only — never headlines.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from analog_ic_design.circuit import compile_netlist, validate
from analog_ic_design.metrics.gain import extract_dc_gain
from analog_ic_design.robust.mc_sampler import MonteCarloSampler, PerturbationConfig
from analog_ic_design.robust.protocol import (
    RobustnessReport,
    StatisticalProtocol,
    build_report,
    wilson_interval,
)
from analog_ic_design.sim.cs_amp import build_cs_amplifier
from analog_ic_design.sim.ngspice import SimError, libngspice_available, run_deck
from analog_ic_design.sim.testbench import assemble_dc_sweep
from analog_ic_design.store import connect, migrate, new_id, utcnow_iso

NEEDS_LIB = pytest.mark.skipif(
    not libngspice_available(),
    reason="libngspice absent (base image); covered by CI eda job",
)

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"


def _protocol(**over: object) -> StatisticalProtocol:
    base: dict[str, object] = {
        "name": "p",
        "sample_count": 8,
        "seed": 3,
        "corners": ("tt_27C_1.80V",),
        "supplies": (1.8,),
        "temperatures": (300.15,),
        "variation_mechanisms": ("corner-files",),
        "sampling_method": "enumerated",
        "metric_thresholds": {"dc_gain": (">=", 8.0, 0.1)},
    }
    base.update(over)
    return StatisticalProtocol(**base)  # type: ignore[arg-type]


def test_protocol_rejects_incomplete() -> None:
    with pytest.raises(ValueError, match="no corners"):
        _protocol(corners=())
    with pytest.raises(ValueError, match="no variation mechanisms"):
        _protocol(variation_mechanisms=())
    with pytest.raises(ValueError, match="no metric thresholds"):
        _protocol(metric_thresholds={})
    with pytest.raises(ValueError, match="bad operator"):
        _protocol(metric_thresholds={"dc_gain": (">>", 8.0, 0.1)})
    with pytest.raises(ValueError, match="sample_count must be positive"):
        _protocol(sample_count=0)
    with pytest.raises(ValueError, match="confidence.*\\(0, 1\\)"):
        _protocol(confidence_level=1.0)


def test_wilson_interval_properties() -> None:
    lower, upper = wilson_interval(0, 10)
    assert lower < 1e-9 and 0.0 < upper < 0.4
    lower, upper = wilson_interval(10, 10)
    assert 0.7 < lower < 1.0 and abs(upper - 1.0) < 1e-9
    lower, upper = wilson_interval(8, 10)
    assert lower < 0.8 < upper
    assert abs(lower - 0.4902) < 0.005 and abs(upper - 0.9436) < 0.005
    with pytest.raises(ValueError, match="total > 0"):
        wilson_interval(0, 0)
    with pytest.raises(ValueError, match="0 <= passes"):
        wilson_interval(11, 10)


def test_build_report_counts() -> None:
    protocol = _protocol()
    results = [(f"t{i}", 9.0 - i) for i in range(5)]
    report = build_report(protocol, "dc_gain", results)
    assert isinstance(report, RobustnessReport)
    assert (report.passes, report.total) == (2, 5)
    assert report.yield_estimate == 0.4
    assert report.ci_lower <= 0.4 <= report.ci_upper
    assert report.trial_ids == tuple(f"t{i}" for i in range(5))
    assert report.operator == ">=" and report.threshold == 8.0
    with pytest.raises(ValueError, match="no threshold"):
        build_report(protocol, "nope", results)
    with pytest.raises(ValueError, match="zero trials"):
        build_report(protocol, "dc_gain", [])
    with pytest.raises(ValueError, match="not finite"):
        build_report(protocol, "dc_gain", [("t0", float("nan"))])


@NEEDS_LIB
def test_mc_gain_report_live(tmp_path: Path) -> None:
    db_path = str(tmp_path / "mc.sqlite")
    conn = connect(db_path)
    migrate(conn)
    sampler = MonteCarloSampler(
        seed=11, config=PerturbationConfig(sigma_w=0.02, sigma_l=0.01)
    )
    protocol = StatisticalProtocol(
        name="cs_amp_mc_gain",
        sample_count=8,
        seed=11,
        corners=("tt_27C_1.80V",),
        supplies=(1.8,),
        temperatures=(300.15,),
        variation_mechanisms=(
            "sky130 corner files (tt) + seeded geometric W/L perturbation"
            " (sigma_w=0.02, sigma_l=0.01)",
        ),
        sampling_method="seeded-gaussian-geometry",
        metric_thresholds={"dc_gain": (">=", 8.0, 0.1)},
    )
    base = {"m1": {"W": 1e-06, "L": 160e-09}, "m2": {"W": 2e-06, "L": 160e-09}}
    results: list[tuple[str, float]] = []
    stamp = utcnow_iso()
    for index in range(8):
        geo = sampler.perturb(base, index)
        cell_conn = connect()
        migrate(cell_conn)
        cell = build_cs_amplifier(
            cell_conn,
            w_n=geo["m1"]["W"],
            l_n=geo["m1"]["L"],
            w_p=geo["m2"]["W"],
            l_p=geo["m2"]["L"],
        )
        trial_id = f"mc-{index}"
        gain: float | None = None
        try:
            rep = validate(cell_conn, cell)
            if not rep.valid:
                raise SimError(f"Schema: {[v.message for v in rep.violations]}")
            frag = compile_netlist(cell_conn, cell)
            deck = assemble_dc_sweep(
                frag,
                sweep_net="in",
                v_start=0.4,
                v_stop=1.2,
                v_step=0.005,
                extra_lines=["Vbias vbias 0 DC 0.9"],
                libs=[(SKY130_LIB, "tt")],
            )
            raw = run_deck(lines=deck.splitlines())
            gain = extract_dc_gain(raw.vectors["in"], raw.vectors["out"])
            status, verdict, metrics = "succeeded", "pass", {"dc_gain": gain}
        except SimError as exc:
            status, verdict, metrics = (
                "failed",
                f"{type(exc).__name__}: {exc}",
                {},
            )
        finally:
            cell_conn.close()
        if gain is not None:
            results.append((trial_id, gain))
        jid = new_id()
        conn.execute(
            "INSERT INTO job VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (jid, "mc_sample", status, f'{{"sample": {index}}}',
             json.dumps(metrics, sort_keys=True),
             None if status == "succeeded" else verdict, stamp, stamp),
        )
        conn.execute(
            "INSERT INTO experiment VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id(), "cs_amp_mc_gain", index, "trial", status, "mc",
             f'{{"sample": {index}}}', json.dumps(metrics, sort_keys=True),
             verdict, f"mc-{protocol.seed}-{index}", protocol.seed, jid, stamp),
        )
        conn.commit()
        print(f"sample={index} status={status} metrics={metrics}")
    assert len(results) == 8
    report = build_report(protocol, "dc_gain", results)
    assert report.total == 8
    assert 0 <= report.passes <= 8
    assert report.ci_lower <= report.yield_estimate <= report.ci_upper
    assert report.trial_ids == tuple(f"mc-{i}" for i in range(8))
    conn.close()
