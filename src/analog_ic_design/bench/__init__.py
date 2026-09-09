"""AnalogBench registry + runner (R0 trust core, first slice).

Eight canonical benchmarks B0–B7 form the release scoreboard. Only B0
(inverter nominal transient) executes today; B1–B7 raise NotImplementedError
with per-bench defer owners instead of faking results. Runner returns data
(BenchResult), never raises on simulation faults — failures are scoreboard
rows, and the fail-closed contract surfaces them as status="error" with the
taxonomy message attached.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from analog_ic_design.engine.engine_v01 import EngineV01
from analog_ic_design.sim.inverter import build_inverter
from analog_ic_design.sim.ngspice import RawSim, SimError
from analog_ic_design.sim.testbench import assemble_transient
from analog_ic_design.sim.waveform import parse_transient
from analog_ic_design.store.schema import connect, migrate

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"


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


def run_bench(bench_id: str, *, db_path: str, seed: int = 21) -> BenchResult:
    """Execute one benchmark by id; unknown ids fail closed (Schema)."""
    if bench_id not in BENCHES:
        raise ValueError(f"Schema: unknown bench {bench_id!r}")
    if bench_id == "B0":
        return _run_b0(db_path=db_path, seed=seed)
    owner = BENCHES[bench_id].owner
    raise NotImplementedError(f"{bench_id} deferred to {owner}")
