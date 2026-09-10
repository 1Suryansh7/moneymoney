import { useState } from "react";
import { ANALYSES, CORNERS, DESIGN_VARIABLES } from "../data";
import { useStore } from "../store";
import { Field, IconBtn, SectionTitle, StatusCell, StatusDot, td, th } from "../ui";
import { cn } from "@/lib/utils";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Play, RotateCw, Square, Sliders, ChevronDown } from "lucide-react";

type MetricRow = { name: string; expr: string; spec: string };

// No measured metrics exist yet: the backend has no measure endpoint until
// the R0 Testbench Manager lands, so every metric row reads NOT RUN.
// Showing invented numbers here would be fabrication, not simulation.
const PENDING_METRICS: MetricRow[] = [
  { name: "DC Gain", expr: "gain(VOUT/VID)", spec: "> 60 dB" },
  { name: "UGBW", expr: "unityGainFreq", spec: "> 150 MHz" },
  { name: "Phase Margin", expr: "phaseMargin", spec: "> 60 °" },
  { name: "Slew Rate +", expr: "slewRate", spec: "> 35 V/µs" },
  { name: "Noise", expr: "integratedNoise", spec: "< 20 µVrms" },
  { name: "Power", expr: "averagePower", spec: "< 2.5 mW" },
  { name: "Output Swing", expr: "swing", spec: "> 0.95 V" },
];

function fmtSi(v: number, unit: string): string {
  if (unit === "s") {
    if (v >= 1) return `${v.toFixed(2)} s`;
    if (v >= 1e-3) return `${(v * 1e3).toFixed(2)} ms`;
    if (v >= 1e-6) return `${(v * 1e6).toFixed(2)} µs`;
    return `${(v * 1e9).toFixed(2)} ns`;
  }
  if (unit === "Hz") {
    if (v >= 1e9) return `${(v / 1e9).toFixed(2)} GHz`;
    if (v >= 1e6) return `${(v / 1e6).toFixed(2)} MHz`;
    if (v >= 1e3) return `${(v / 1e3).toFixed(2)} kHz`;
    return `${v.toFixed(0)} Hz`;
  }
  return `${v.toFixed(3)} ${unit}`;
}

export function SimulationExplorer({ dense = false }: { dense?: boolean }) {
  const s = useStore();
  const [vars, setVars] = useState(DESIGN_VARIABLES);
  const [edit, setEdit] = useState<string | null>(null);
  const [dirtyVars, setDirtyVars] = useState<string[]>([]);
  const [analyses, setAnalyses] = useState(ANALYSES.map((a) => ({ ...a })));
  const [corners, setCorners] = useState(CORNERS.map((c) => ({ ...c })));
  const [tuning, setTuning] = useState(false);
  const [mcOpen, setMcOpen] = useState(false);
  const [setupOpen, setSetupOpen] = useState(false);

  const wave = s.liveWave;
  const readout = (name: string): string => {
    const t = wave?.traces.find((x) => x.name === name);
    if (!t || !wave) return "—";
    if (t.y && t.y.length > 0) {
      const lo = Math.min(...t.y);
      const hi = Math.max(...t.y);
      return `${lo.toFixed(3)}…${hi.toFixed(3)} ${t.unit ?? ""}`.trim();
    }
    if (t.magnitude_db && t.magnitude_db.length > 0) {
      const peak = Math.max(...t.magnitude_db);
      const at = wave.x[t.magnitude_db.indexOf(peak)] ?? NaN;
      return `peak ${peak.toFixed(2)} dB @ ${fmtSi(at, wave.x_unit)}`;
    }
    return "—";
  };
  const traceNames = wave?.traces.map((t) => t.name) ?? [];

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-background">
      {/* header */}
      <div className="flex h-[30px] shrink-0 items-center gap-3 border-b border-border bg-chrome px-2 text-[11px]">
        <span className="text-muted-foreground">
          Testbench <span className="num text-foreground">inverter_tran (demo)</span>
        </span>
        <span className="text-muted-foreground">
          Simulator <span className="num text-foreground">ngspice-47 · sky130 tt</span>
        </span>
        <span className="text-muted-foreground">
          Mode <span className="num text-foreground">Explorer</span>
        </span>
        {s.backendUp === false && (
          <span className="num text-critical">backend unreachable — start app-eda uvicorn :8000</span>
        )}
        <span className="ml-3 flex items-center gap-1.5">
          <StatusDot status={s.simPhase === "COMPLETE" ? "PASS" : s.simPhase === "READY" ? "NOT RUN" : "RUNNING"} />
          <span className="num text-foreground">
            {s.simPhase}
            {s.simPhase === "RUNNING" && ` ${s.simProgress}%`}
          </span>
        </span>
        {s.simPhase === "RUNNING" && (
          <span className="h-[5px] w-[120px] overflow-hidden rounded-[1px] bg-raised">
            <span className="block h-full bg-primary transition-all" style={{ width: `${s.simProgress}%` }} />
          </span>
        )}
        <div className="ml-auto flex items-center gap-1">
          <button
            onClick={s.runSimulation}
            className="flex h-[22px] items-center gap-1 rounded-[3px] bg-success/15 px-2 text-[11px] text-success hover:bg-success/25"
          >
            <Play className="h-[12px] w-[12px]" /> Run
          </button>
          <button
            onClick={s.stopSimulation}
            className="flex h-[22px] items-center gap-1 rounded-[3px] border border-border px-2 text-[11px] text-muted-foreground hover:bg-raised"
          >
            <Square className="h-[10px] w-[10px]" /> Stop
          </button>
          <button
            onClick={s.runSimulation}
            className="flex h-[22px] items-center gap-1 rounded-[3px] border border-border px-2 text-[11px] text-muted-foreground hover:bg-raised"
          >
            <RotateCw className="h-[11px] w-[11px]" /> Netlist + Run
          </button>
          <button
            onClick={() => setSetupOpen(true)}
            className="flex h-[22px] items-center gap-1 rounded-[3px] border border-border px-2 text-[11px] text-muted-foreground hover:bg-raised"
          >
            Run Options <ChevronDown className="h-3 w-3" />
          </button>
          <IconBtn label="Real-time tuning" active={tuning} onClick={() => setTuning(!tuning)}>
            <Sliders className="h-[13px] w-[13px]" />
          </IconBtn>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[300px_1fr] overflow-hidden">
        {/* data view */}
        <div className="min-h-0 overflow-auto border-r border-border bg-panel">
          <SectionTitle>Design Variables</SectionTitle>
          <table className="w-full border-collapse">
            <thead>
              <tr>
                {["Variable", "Value", "Unit"].map((h) => (
                  <th key={h} className={th}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {vars.map((v) => (
                <tr key={v.name} className="hover:bg-raised/60" onDoubleClick={() => setEdit(v.name)}>
                  <td className={cn(td, "num")}>
                    {dirtyVars.includes(v.name) && <span className="mr-1 text-warning">•</span>}
                    {v.name}
                  </td>
                  <td className={cn(td, "num text-right")}>
                    {edit === v.name ? (
                      <input
                        autoFocus
                        defaultValue={v.value}
                        onBlur={(e) => {
                          setVars(vars.map((x) => (x.name === v.name ? { ...x, value: e.target.value } : x)));
                          setDirtyVars([...dirtyVars, v.name]);
                          setEdit(null);
                          if (v.name === "IBIAS") s.setIbias(Number(e.target.value) || 200);
                        }}
                        onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
                        className="num w-full bg-background text-right text-[11px] focus:outline-none"
                      />
                    ) : v.name === "IBIAS" ? (
                      s.ibias.toFixed(0)
                    ) : (
                      v.value
                    )}
                  </td>
                  <td className={cn(td, "num text-subtle")}>{v.unit}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <SectionTitle>Analyses</SectionTitle>
          {analyses.map((a) => (
            <div key={a.id}>
              <label className="flex items-center gap-2 border-b border-border/40 px-2 py-[5px] text-[11px]">
                <input
                  type="checkbox"
                  checked={a.enabled}
                  onChange={() => setAnalyses(analyses.map((x) => (x.id === a.id ? { ...x, enabled: !x.enabled } : x)))}
                  className="h-[11px] w-[11px] accent-[color:var(--color-primary)]"
                />
                <span className="num text-foreground">{a.id}</span>
              </label>
              {a.enabled &&
                a.rows.map(([k, v]) => (
                  <div key={k} className="flex justify-between border-b border-border/30 py-[3px] pr-2 pl-7 text-[11px]">
                    <span className="text-muted-foreground">{k}</span>
                    <span className="num">{v}</span>
                  </div>
                ))}
            </div>
          ))}

          <SectionTitle>Corners</SectionTitle>
          {corners.map((c) => (
            <label key={c.id} className="flex items-center gap-2 border-b border-border/40 px-2 py-[5px] text-[11px]">
              <input
                type="checkbox"
                checked={c.enabled}
                onChange={() => setCorners(corners.map((x) => (x.id === c.id ? { ...x, enabled: !x.enabled } : x)))}
                className="h-[11px] w-[11px] accent-[color:var(--color-primary)]"
              />
              <span className="num w-[26px]">{c.id}</span>
              <span className="num text-muted-foreground">{c.temp} °C</span>
              <span className="num ml-auto text-muted-foreground">{c.supply} V</span>
            </label>
          ))}
          <div className="flex gap-1 p-2">
            <button onClick={s.runSimulation} className="h-[22px] flex-1 rounded-[3px] border border-border text-[11px] hover:bg-raised">
              Run All Corners
            </button>
            <button onClick={() => setMcOpen(true)} className="h-[22px] flex-1 rounded-[3px] border border-border text-[11px] hover:bg-raised">
              Monte Carlo...
            </button>
          </div>

          <SectionTitle>Model Libraries</SectionTitle>
          <Field label="sky130.lib.spice" value="tt" />
          <Field label="mc_mm_switch" value="0" />
          <SectionTitle>Environment</SectionTitle>
          <Field label="Temperature" value="27 °C" />
          <Field label="Threads" value="8" />
          <Field label="Host" value="local" />
        </div>

        {/* outputs */}
        <div className="flex min-h-0 flex-col">
          <div className="min-h-0 flex-1 overflow-auto">
            <SectionTitle>Live Run</SectionTitle>
            <table className="w-full border-collapse">
              <tbody>
                {[
                  ["Phase", s.simPhase] as const,
                  ["Job", s.lastJobId ? `${s.lastJobId.slice(0, 8)}…` : "—"] as const,
                  ["Analysis", wave?.analysis ?? "—"] as const,
                  ["Points", wave ? String(wave.x.length) : "—"] as const,
                  ...traceNames.map((n) => [`Trace ${n}`, readout(n)] as const),
                ].map(([k, v]) => (
                  <tr key={k} className="hover:bg-raised/60">
                    <td className={cn(td, "text-foreground")}>{k}</td>
                    <td className={cn(td, "num text-right")}>{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <SectionTitle>Outputs / Specifications</SectionTitle>
            <div className="num px-2 pb-1 text-[10px] text-subtle">
              DC gain measures live on inverter-shape cells; remaining metrics pending the next testbenches —
              no numbers shown rather than invented ones.
            </div>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {["Output", "Expression", "Result", "Spec", "Status", ""].map((h) => (
                    <th key={h} className={th}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {PENDING_METRICS.map((r) => {
                  const live = r.name === "DC Gain" ? s.measuredGain : null;
                  const db = live ? 20 * Math.log10(live.value) : null;
                  return (
                    <tr key={r.name} className="cursor-default hover:bg-raised/60">
                      <td className={cn(td, "text-foreground")}>{r.name}</td>
                      <td className={cn(td, "num text-subtle")}>{r.expr}</td>
                      <td className={cn(td, "num text-right")}>
                        {live && db !== null
                          ? `${live.value.toFixed(2)} ${live.unit} (${db.toFixed(2)} dB)`
                          : "—"}
                      </td>
                      <td className={cn(td, "num text-right text-muted-foreground")}>{r.spec}</td>
                      <td className={td}>
                        <StatusCell status={live ? "MEASURED" : "NOT RUN"} />
                      </td>
                      <td className={td}>
                        <button
                          onClick={() => {
                            s.openTab({ id: "waveforms", label: "Waveform Analyzer" });
                          }}
                          className="rounded-[2px] border border-border px-1.5 text-[10px] text-muted-foreground hover:bg-raised"
                        >
                          Plot
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {!dense && (
              <>
                <SectionTitle>History</SectionTitle>
                <table className="w-full border-collapse">
                  <thead>
                    <tr>
                      {["Job", "Kind", "Status", "Progress"].map((h) => (
                        <th key={h} className={th}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {s.jobs.map((j) => (
                      <tr key={j.id} className="hover:bg-raised/60">
                        <td className={cn(td, "num text-primary")}>{j.id.slice(0, 8)}…</td>
                        <td className={cn(td, "num text-subtle")}>{j.type}</td>
                        <td className={cn(td, "num text-right")}>{j.status}</td>
                        <td className={cn(td, "num text-right")}>{j.progress}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>

          {tuning && (
            <div className="shrink-0 border-t border-border bg-panel">
              <SectionTitle>Real-time tuning</SectionTitle>
              <div className="flex items-center gap-3 px-3 py-2">
                <span className="num w-[50px] text-[11px]">IBIAS</span>
                <span className="num text-[10px] text-subtle">100 µA</span>
                <input
                  type="range"
                  min={100}
                  max={400}
                  value={s.ibias}
                  aria-label="IBIAS tuning"
                  onChange={(e) => s.setIbias(Number(e.target.value))}
                  className="flex-1 accent-[color:var(--color-primary)]"
                />
                <span className="num text-[10px] text-subtle">400 µA</span>
                <span className="num w-[64px] text-right text-[11px] text-primary">{s.ibias} µA</span>
                <span className="num text-[10px] text-subtle">re-run applies · live metrics pending</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Monte Carlo dialog */}
      <Dialog open={mcOpen} onOpenChange={setMcOpen}>
        <DialogContent className="max-w-[520px] gap-0 rounded-[5px] border-border bg-popover p-0">
          <SectionTitle>Monte Carlo Setup</SectionTitle>
          <div className="p-3">
            {[
              ["Samples", "200"],
              ["Seed", "91342"],
              ["Variation", "Process + Mismatch"],
              ["Distribution", "Gaussian"],
              ["Sigma", "3"],
              ["Save waveforms", "Failed runs only"],
            ].map(([k, v]) => (
              <Field key={k} label={k} value={v} />
            ))}
            <div className="num mt-3 text-[11px] text-subtle">
              Monte Carlo runs land with the R0 Testbench Manager — this control is inert, no samples are
              fabricated.
            </div>
          </div>
          <div className="flex justify-end gap-2 border-t border-border p-2">
            <button onClick={() => setMcOpen(false)} className="h-[24px] rounded-[3px] border border-border px-3 text-[11px]">
              Close
            </button>
            <button
              disabled
              title="Monte Carlo wiring pending"
              className="h-[24px] cursor-not-allowed rounded-[3px] bg-raised px-3 text-[11px] text-subtle"
            >
              Run
            </button>
          </div>
        </DialogContent>
      </Dialog>

      {/* setup dialog */}
      <Dialog open={setupOpen} onOpenChange={setSetupOpen}>
        <DialogContent className="max-w-[440px] gap-0 rounded-[5px] border-border bg-popover p-0">
          <SectionTitle>Simulation Setup</SectionTitle>
          <div className="p-3">
            {[
              ["Simulator", "Generic SPICE"],
              ["Precision", "Moderate"],
              ["Temperature", "27 °C"],
              ["Threads", "8"],
            ].map(([k, v]) => (
              <Field key={k} label={k} value={v} />
            ))}
            <div className="mt-2 text-[11px]">
              <div className="mb-1 text-subtle">Save</div>
              {["Selected", "All public nodes", "All"].map((o, i) => (
                <label key={o} className="mr-3 inline-flex items-center gap-1">
                  <input type="radio" name="save" defaultChecked={i === 1} className="accent-[color:var(--color-primary)]" />
                  {o}
                </label>
              ))}
            </div>
            <div className="mt-2 space-y-1 text-[11px]">
              {[
                ["Preserve operating point", true],
                ["Save device currents", true],
                ["High precision", false],
              ].map(([l, c]) => (
                <label key={l as string} className="flex items-center gap-2">
                  <input type="checkbox" defaultChecked={c as boolean} className="h-[11px] w-[11px] accent-[color:var(--color-primary)]" />
                  {l as string}
                </label>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2 border-t border-border p-2">
            <button onClick={() => setSetupOpen(false)} className="h-[24px] rounded-[3px] border border-border px-3 text-[11px]">
              Cancel
            </button>
            <button onClick={() => setSetupOpen(false)} className="h-[24px] rounded-[3px] bg-primary px-3 text-[11px] text-primary-foreground">
              Apply
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
