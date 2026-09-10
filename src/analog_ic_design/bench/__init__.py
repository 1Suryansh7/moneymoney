"""AnalogBench registry + runner (R0 trust core).

Eight canonical benchmarks B0–B7 form the release scoreboard. B0 (inverter),
B1 (mirror), B2 (diff pair), B3 (common-source) and B4 (cascode) execute
today; B5–B7 raise NotImplementedError with per-bench defer owners instead
of faking results. Runner returns data
(BenchResult), never raises on simulation faults — failures are scoreboard
rows, and the fail-closed contract surfaces them as status="error" with the
taxonomy message attached.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Final

from analog_ic_design.engine.engine_v01 import EngineV01
from analog_ic_design.metrics.gain import extract_ac_gain, extract_dc_gain
from analog_ic_design.sim.cascode import build_cascode
from analog_ic_design.sim.cs_amp import build_cs_amplifier
from analog_ic_design.sim.diff_pair import build_diff_pair
from analog_ic_design.sim.inverter import build_inverter
from analog_ic_design.sim.mirror import build_mirror
from analog_ic_design.sim.ngspice import RawSim, SimError
from analog_ic_design.sim.testbench import assemble_ac, assemble_dc_sweep, assemble_transient
from analog_ic_design.sim.waveform import parse_ac, parse_transient
from analog_ic_design.store.schema import connect, migrate

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"

# Reference current pushed into the mirror diode by the testbench IDC source.
# Single source of truth: the deck string below is formatted from this value.
_MIRROR_IREF_A: Final = 20e-6
# Output bias point for the ratio readout (exact sweep grid point).
_MIRROR_VOUT_V: Final = 0.9
_MIRROR_VOUT_TRIODE_V: Final = 0.5


@dataclass(frozen=True)
class Benchmark:
    """Static definition: what the bench proves and who owns it."""

    bench_id: str
    name: str
    circuit: str
    analyses: tuple[str, ...]
    acceptance: str
    owner: str


@dataclass(frozen=True)
class BenchResult:
    """Measured outcome: status plus evidence, never bare pass/fail."""

    bench_id: str
    status: str  # "pass" | "fail" | "error"
    metrics: dict[str, float] = field(default_factory=dict)
    evidence: tuple[str, ...] = ()
    message: str = ""


BENCHES: dict[str, Benchmark] = {
    "B0": Benchmark("B0", "Inverter nominal transient", "cmos_inverter",
                    ("tran",), "rail-to-rail inversion", "R0-1"),
    "B1": Benchmark("B1", "Current mirror matching", "current_mirror",
                    ("dc",), "mirror ratio within tolerance", "R0-2"),
    "B2": Benchmark("B2", "Diff pair gain", "diff_pair",
                    ("ac",), "gain within tolerance of hand calc", "R0-2"),
    "B3": Benchmark("B3", "Common-source amp", "common_source",
                    ("ac", "tran"), "gain + swing within tolerance", "R0-3"),
    "B4": Benchmark("B4", "Telescopic cascode", "cascode",
                    ("ac",), "gain + headroom within tolerance", "R0-3"),
    "B5": Benchmark("B5", "Folded-cascode OTA", "folded_cascode",
                    ("ac", "tran"), "gain/UGB/PM within tolerance", "R0-4"),
    "B6": Benchmark("B6", "Miller op-amp PVT", "two_stage_miller",
                    ("ac", "pvt"), "spec across corners", "R0-4"),
    "B7": Benchmark("B7", "Bandgap reference", "bandgap",
                    ("dc", "temp"), "tempco within tolerance", "R0-5"),
}


def _run_b0(*, db_path: str, seed: int) -> BenchResult:
    setup = connect(db_path)
    try:
        migrate(setup)
        cell = build_inverter(setup)
    finally:
        setup.close()
    eng = EngineV01(db_path=db_path)
    try:
        valid, violations = eng.validate(cell_id=cell)
        if not valid:
            return BenchResult("B0", "fail", {}, (),
                               f"Constraint: validation gate failed: {violations}")
        frag = eng.netlist(cell_id=cell)
        deck = assemble_transient(frag, tstop_s=30e-9, libs=[(SKY130_LIB, "tt")])
        try:
            repro = eng.simulate(netlist=deck, seed=seed)
        except SimError as exc:
            return BenchResult("B0", "error", {}, (), f"{exc}")
        jobs = eng.list_jobs()
        if not jobs:
            return BenchResult("B0", "error", {}, (repro,),
                               "Schema: simulate returned no ledger job")
        detail = eng.job_result(job_id=jobs[0]["job_id"])
        raw = json.loads(str(detail["result"]))["vectors"]
        wave = parse_transient(RawSim(vectors=dict(raw), log=""))
        vout = [float(v) for v in wave.trace("out").values]
        metrics = {"vout_min_v": min(vout), "vout_max_v": max(vout)}
        if min(vout) < 0.1 and max(vout) > 1.7:
            return BenchResult("B0", "pass", metrics, (repro,), "")
        return BenchResult(
            "B0", "fail", metrics, (repro,),
            f"Constraint: no rail swing (min={min(vout):.3f}, max={max(vout):.3f})")
    finally:
        eng.close()


def _branch_current(vectors: dict[str, list[float]], *, exclude: tuple[str, ...]) -> list[float]:
    """Return the single non-supply branch-current vector (fail-closed).

    ngspice saves voltage-source currents as `<name>#branch` (observed live:
    `vin#branch`, `vdd#branch`, `vss#branch`). The sweep/load source is the
    only non-supply source by construction; anything else is ambiguous data.
    """
    found = [
        key for key in vectors
        if key.endswith("#branch") and key[: -len("#branch")].lower() not in exclude
    ]
    if len(found) != 1:
        raise SimError(
            f"Schema: expected exactly one load branch vector, found {found}"
        )
    return [float(v) for v in vectors[found[0]]]


def _at(vout: list[float], target: float) -> int:
    return min(range(len(vout)), key=lambda i: abs(vout[i] - target))


def _run_b1(*, db_path: str, seed: int) -> BenchResult:
    setup = connect(db_path)
    try:
        migrate(setup)
        cell = build_mirror(setup)
    finally:
        setup.close()
    eng = EngineV01(db_path=db_path)
    try:
        valid, violations = eng.validate(cell_id=cell)
        if not valid:
            return BenchResult("B1", "fail", {}, (),
                               f"Constraint: validation gate failed: {violations}")
        frag = eng.netlist(cell_id=cell)
        deck = assemble_dc_sweep(
            frag,
            sweep_net="out_mirror",
            v_start=0.3,
            v_stop=1.5,
            v_step=0.05,
            extra_lines=[f"Iref vdd in_ref DC {_MIRROR_IREF_A}"],
            libs=[(SKY130_LIB, "tt")],
        )
        try:
            repro = eng.simulate(netlist=deck, seed=seed)
        except SimError as exc:
            return BenchResult("B1", "error", {}, (), f"{exc}")
        jobs = eng.list_jobs()
        if not jobs:
            return BenchResult("B1", "error", {}, (repro,),
                               "Schema: simulate returned no ledger job")
        detail = eng.job_result(job_id=jobs[0]["job_id"])
        vecs = json.loads(str(detail["result"]))["vectors"]
        if "out_mirror" not in vecs:
            return BenchResult("B1", "error", {}, (repro,),
                               "Schema: output node vector missing from run")
        vout = [float(v) for v in vecs["out_mirror"]]
        try:
            iout = _branch_current(dict(vecs), exclude=("vdd", "vss"))
        except SimError as exc:
            return BenchResult("B1", "error", {}, (repro,), f"{exc}")
        i09 = _at(vout, _MIRROR_VOUT_V)
        i05 = _at(vout, _MIRROR_VOUT_TRIODE_V)
        ratio = abs(iout[i09]) / _MIRROR_IREF_A
        ratio_triode = abs(iout[i05]) / _MIRROR_IREF_A
        metrics = {
            "mirror_ratio": ratio,
            "mirror_ratio_triode": ratio_triode,
            "i_out_a": abs(iout[i09]),
            "vout_v": vout[i09],
        }
        # Matched same-size pair: saturation ratio near unity (Early effect
        # is a few percent — MEASURED 1.025 live), and saturation must exceed
        # triode-suppressed readout. Band is deliberately wide: it catches
        # opens/shorts/biased-off (ratio ~0 or wild), not mismatch precision.
        if 0.8 <= ratio <= 1.2 and ratio > ratio_triode:
            return BenchResult("B1", "pass", metrics, (repro,), "")
        return BenchResult(
            "B1", "fail", metrics, (repro,),
            f"Constraint: mirror ratio {ratio:.3f} outside [0.8, 1.2]"
            f" or triode ordering violated ({ratio_triode:.3f})")
    finally:
        eng.close()


def _run_b2(*, db_path: str, seed: int) -> BenchResult:
    setup = connect(db_path)
    try:
        migrate(setup)
        cell = build_diff_pair(setup)
    finally:
        setup.close()
    eng = EngineV01(db_path=db_path)
    try:
        valid, violations = eng.validate(cell_id=cell)
        if not valid:
            return BenchResult("B2", "fail", {}, (),
                               f"Constraint: validation gate failed: {violations}")
        frag = eng.netlist(cell_id=cell)
        deck = assemble_ac(
            frag,
            in_net="inp",
            v_bias=0.9,
            extra_lines=["Vinn inn 0 DC 0.9", "Vbias vbias 0 DC 0.9"],
            libs=[(SKY130_LIB, "tt")],
        )
        try:
            repro = eng.simulate(netlist=deck, seed=seed)
        except SimError as exc:
            return BenchResult("B2", "error", {}, (), f"{exc}")
        jobs = eng.list_jobs()
        if not jobs:
            return BenchResult("B2", "error", {}, (repro,),
                               "Schema: simulate returned no ledger job")
        detail = eng.job_result(job_id=jobs[0]["job_id"])
        payload = json.loads(str(detail["result"]))
        cx = {k: [complex(p[0], p[1]) for p in v]
              for k, v in payload.get("complex_vectors", {}).items()}
        wave = parse_ac(RawSim(vectors=payload["vectors"], complex_vectors=cx, log=""))
        try:
            gain_n = extract_ac_gain(wave, in_node="inp", out_node="outn")
            gain_p = extract_ac_gain(wave, in_node="inp", out_node="outp")
        except SimError as exc:
            return BenchResult("B2", "error", {}, (repro,), f"{exc}")
        metrics = {"gain_outn": gain_n, "gain_outp": gain_p}
        # Single-ended drive: the mirror-loaded side (outn) must show active
        # voltage gain while the diode-loaded side (outp) stays attenuated —
        # MEASURED 8.075 / 0.536 live. That split is the differential-action
        # fingerprint: a dead, misbiased, or converged-wrong pair cannot
        # produce it. Bands stay wide by design (structure, not precision).
        if math.isfinite(gain_n) and math.isfinite(gain_p) \
                and 3.0 < gain_n < 30.0 and gain_p < 2.0:
            return BenchResult("B2", "pass", metrics, (repro,), "")
        return BenchResult(
            "B2", "fail", metrics, (repro,),
            f"Constraint: differential split broken (outn={gain_n:.3f}, outp={gain_p:.3f})")
    finally:
        eng.close()


def _job_vectors(eng: EngineV01) -> tuple[dict[str, list[float]], str]:
    """Newest job's decoded vector payload plus its reproducibility id."""
    jobs = eng.list_jobs()
    if not jobs:
        raise SimError("Schema: simulate returned no ledger job")
    detail = eng.job_result(job_id=jobs[0]["job_id"])
    payload = json.loads(str(detail["result"]))
    return dict(payload["vectors"]), str(payload.get("reproducibility_id", ""))


def _run_b3(*, db_path: str, seed: int) -> BenchResult:
    setup = connect(db_path)
    try:
        migrate(setup)
        cell = build_cs_amplifier(setup)
    finally:
        setup.close()
    eng = EngineV01(db_path=db_path)
    try:
        valid, violations = eng.validate(cell_id=cell)
        if not valid:
            return BenchResult("B3", "fail", {}, (),
                               f"Constraint: validation gate failed: {violations}")
        frag = eng.netlist(cell_id=cell)
        dc_deck = assemble_dc_sweep(
            frag,
            sweep_net="in",
            v_start=0.4,
            v_stop=1.2,
            v_step=0.005,
            extra_lines=["Vbias vbias 0 DC 0.9"],
            libs=[(SKY130_LIB, "tt")],
        )
        try:
            eng.simulate(netlist=dc_deck, seed=seed)
            dc_vecs, _ = _job_vectors(eng)
            vin = [float(v) for v in dc_vecs["in"]]
            vout = [float(v) for v in dc_vecs["out"]]
            dc_gain = extract_dc_gain(vin, vout)
            slopes = [abs((vout[i + 1] - vout[i]) / (vin[i + 1] - vin[i]))
                      for i in range(len(vin) - 1)]
            trip = vin[slopes.index(max(slopes))]
            ac_deck = assemble_ac(
                frag,
                in_net="in",
                v_bias=trip,
                extra_lines=["Vbias vbias 0 DC 0.9"],
                libs=[(SKY130_LIB, "tt")],
            )
            repro = eng.simulate(netlist=ac_deck, seed=seed)
        except SimError as exc:
            return BenchResult("B3", "error", {}, (), f"{exc}")
        jobs = eng.list_jobs()
        detail = eng.job_result(job_id=jobs[0]["job_id"])
        payload = json.loads(str(detail["result"]))
        cx = {k: [complex(p[0], p[1]) for p in v]
              for k, v in payload.get("complex_vectors", {}).items()}
        wave = parse_ac(RawSim(vectors=payload["vectors"], complex_vectors=cx, log=""))
        try:
            ac_gain = extract_ac_gain(wave, in_node="in", out_node="out")
        except SimError as exc:
            return BenchResult("B3", "error", {}, (repro,), f"{exc}")
        metrics = {
            "dc_gain": dc_gain,
            "ac_gain": ac_gain,
            "vout_min_v": min(vout),
            "vout_max_v": max(vout),
        }
        # Stage 3C measured DC 9.1061 == AC 9.1059 on this exact deck: the two
        # independent analyses must agree (equivalence), the stage must show
        # active gain, and the transfer must swing rail to rail. Equivalence
        # band is 2x the contract tolerance — bench margin, not contract law.
        rel_diff = abs(dc_gain - ac_gain) / dc_gain if dc_gain > 0 else float("inf")
        if dc_gain > 5.0 and min(vout) < 0.1 and max(vout) > 1.7 and rel_diff < 0.10:
            return BenchResult("B3", "pass", metrics, (repro,), "")
        return BenchResult(
            "B3", "fail", metrics, (repro,),
            f"Constraint: gain/equivalence/swing broken (dc={dc_gain:.3f},"
            f" ac={ac_gain:.3f}, rel={rel_diff:.3f})")
    finally:
        eng.close()


def _run_b4(*, db_path: str, seed: int) -> BenchResult:
    setup = connect(db_path)
    try:
        migrate(setup)
        cell = build_cascode(setup)
    finally:
        setup.close()
    eng = EngineV01(db_path=db_path)
    try:
        valid, violations = eng.validate(cell_id=cell)
        if not valid:
            return BenchResult("B4", "fail", {}, (),
                               f"Constraint: validation gate failed: {violations}")
        frag = eng.netlist(cell_id=cell)
        extra = ["Vbcas vbcas 0 DC 1.1", "Vbaisp vbias_p 0 DC 0.9"]
        dc_deck = assemble_dc_sweep(
            frag,
            sweep_net="in",
            v_start=0.4,
            v_stop=1.2,
            v_step=0.005,
            extra_lines=extra,
            libs=[(SKY130_LIB, "tt")],
        )
        try:
            eng.simulate(netlist=dc_deck, seed=seed)
            dc_vecs, _ = _job_vectors(eng)
            vin = [float(v) for v in dc_vecs["in"]]
            vout = [float(v) for v in dc_vecs["out"]]
            dc_gain = extract_dc_gain(vin, vout)
            slopes = [abs((vout[i + 1] - vout[i]) / (vin[i + 1] - vin[i]))
                      for i in range(len(vin) - 1)]
            trip = vin[slopes.index(max(slopes))]
            span_vs = [vin[i] for i in range(len(slopes)) if slopes[i] > 1.0]
            high_gain_span = (max(span_vs) - min(span_vs)) if span_vs else 0.0
            ac_deck = assemble_ac(
                frag,
                in_net="in",
                v_bias=trip,
                extra_lines=extra,
                libs=[(SKY130_LIB, "tt")],
            )
            repro = eng.simulate(netlist=ac_deck, seed=seed)
        except SimError as exc:
            return BenchResult("B4", "error", {}, (), f"{exc}")
        jobs = eng.list_jobs()
        detail = eng.job_result(job_id=jobs[0]["job_id"])
        payload = json.loads(str(detail["result"]))
        cx = {k: [complex(p[0], p[1]) for p in v]
              for k, v in payload.get("complex_vectors", {}).items()}
        wave = parse_ac(RawSim(vectors=payload["vectors"], complex_vectors=cx, log=""))
        try:
            ac_gain = extract_ac_gain(wave, in_node="in", out_node="out")
        except SimError as exc:
            return BenchResult("B4", "error", {}, (repro,), f"{exc}")
        metrics = {
            "dc_gain": dc_gain,
            "ac_gain": ac_gain,
            "headroom_v": high_gain_span,
            "vout_min_v": min(vout),
            "vout_max_v": max(vout),
        }
        # MEASURED live: DC 12.999 == AC 12.989 at trip Vin=0.85V, headroom
        # span 0.205V, rails 0.091–1.800V. The gain clears the plain
        # common-source stage built from the same-size input device (9.1),
        # which is the entire physical point of cascoding — threshold 10
        # pins that action, not a fitted value.
        rel_diff = abs(dc_gain - ac_gain) / dc_gain if dc_gain > 0 else float("inf")
        if ac_gain > 10.0 and min(vout) < 0.1 and max(vout) > 1.7 \
                and rel_diff < 0.10 and high_gain_span > 0.1:
            return BenchResult("B4", "pass", metrics, (repro,), "")
        return BenchResult(
            "B4", "fail", metrics, (repro,),
            f"Constraint: cascode action broken (dc={dc_gain:.3f},"
            f" ac={ac_gain:.3f}, headroom={high_gain_span:.3f})")
    finally:
        eng.close()


def run_bench(bench_id: str, *, db_path: str, seed: int = 21) -> BenchResult:
    """Execute one benchmark by id; unknown ids fail closed (Schema)."""
    if bench_id not in BENCHES:
        raise ValueError(f"Schema: unknown bench {bench_id!r}")
    if bench_id == "B0":
        return _run_b0(db_path=db_path, seed=seed)
    if bench_id == "B1":
        return _run_b1(db_path=db_path, seed=seed)
    if bench_id == "B2":
        return _run_b2(db_path=db_path, seed=seed)
    if bench_id == "B3":
        return _run_b3(db_path=db_path, seed=seed)
    if bench_id == "B4":
        return _run_b4(db_path=db_path, seed=seed)
    owner = BENCHES[bench_id].owner
    raise NotImplementedError(f"{bench_id} deferred to {owner}")
