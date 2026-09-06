"""First-simulation demo: CMOS inverter transient -> artifacts/inverter_transient.png.

Run in the EDA image (matplotlib lives there via dev extras):
  docker compose --profile eda run --rm app-eda python3.11 examples/plot_inverter.py

Chain exercised end to end: schema fixture -> validate -> compile ->
testbench assembly (sky130 TT) -> Job (worker process) -> parse ->
SI-typed waveform -> PNG. Prints the same numbers the 2H checkpoint asks
the human to verify visually (rails, inversion, timings).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (Agg backend selected above by design)

from analog_ic_design.circuit import compile_netlist, validate
from analog_ic_design.sim.inverter import build_inverter
from analog_ic_design.sim.jobs import JobRunner
from analog_ic_design.sim.ngspice import RawSim
from analog_ic_design.sim.testbench import assemble_transient
from analog_ic_design.sim.waveform import parse_transient
from analog_ic_design.store import connect, migrate

SKY130_LIB = "/usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice"
PNG = Path(__file__).resolve().parents[1] / "artifacts" / "inverter_transient.png"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = str(Path(tmp) / "inv.sqlite")
        conn = connect(db_path)
        migrate(conn)
        try:
            cell = build_inverter(conn)
            report = validate(conn, cell)
            if not report.valid:
                print("GATE FAILED:")
                for violation in report.violations:
                    print(f"  [{violation.category}] {violation.message}")
                return 1
            deck = assemble_transient(
                compile_netlist(conn, cell), tstop_s=30e-9, libs=[(SKY130_LIB, "tt")]
            )
        finally:
            conn.close()
        jobs = JobRunner(db_path=db_path)
        try:
            result = jobs.wait(jobs.submit_simulation(netlist=deck, seed=21), timeout=300)
        finally:
            jobs.shutdown()
    if result.status != "succeeded" or result.result is None:
        print(f"SIM FAILED: {result.error}")
        return 1
    raw = json.loads(result.result)["vectors"]
    wave = parse_transient(RawSim(vectors=dict(raw), log=""))
    times = [float(t) * 1e9 for t in wave.time]
    vin = [float(v) for v in wave.trace("in").values]
    vout = [float(v) for v in wave.trace("out").values]
    print(f"points={len(times)} vin=[{min(vin):.3f},{max(vin):.3f}]"
          f" vout=[{min(vout):.3f},{max(vout):.3f}]")
    fig, ax = plt.subplots()
    ax.plot(times, vin, label="in")
    ax.plot(times, vout, label="out")
    ax.set_xlabel("time (ns)")
    ax.set_ylabel("voltage (V)")
    ax.set_title("CMOS inverter transient (sky130 TT, 1.8 V)")
    ax.legend()
    ax.grid(True)
    fig.savefig(PNG, dpi=100)
    print(f"wrote {PNG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
