import { useEffect, useState } from "react";
import { CORNERS, MARGINS, MATRIX, NOMINAL, RUN_PLAN, TESTS, type Status } from "../data";
import { useStore } from "../store";
import { Bar, SectionTitle, StatusCell, td, th } from "../ui";
import { cn } from "@/lib/utils";
import { Play } from "lucide-react";

export function VerificationAssembler() {
  const s = useStore();
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState<string[]>(MATRIX.map((m) => m.test + m.corner));
  const [sel, setSel] = useState<string | null>(null);
  const [plan, setPlan] = useState<string[]>([]);

  useEffect(() => {
    if (!running) return;
    setDone([]);
    setPlan([]);
    let i = 0;
    const iv = window.setInterval(() => {
      i += 1;
      setDone(MATRIX.slice(0, i).map((m) => m.test + m.corner));
      setPlan(RUN_PLAN.slice(0, Math.ceil((i / MATRIX.length) * RUN_PLAN.length)));
      if (i >= MATRIX.length) {
        window.clearInterval(iv);
        setRunning(false);
        s.log("Assembler run complete: 27 pass / 2 fail / 1 warn", "warn");
      }
    }, 130);
    return () => window.clearInterval(iv);
  }, [running, s]);

  const cell = (test: string, corner: string) => MATRIX.find((m) => m.test === test && m.corner === corner)!;
  const total = MATRIX.length;
  const pass = MATRIX.filter((m) => done.includes(m.test + m.corner) && m.status === "PASS").length;
  const fail = MATRIX.filter((m) => done.includes(m.test + m.corner) && m.status === "FAIL").length;
  const warn = MATRIX.filter((m) => done.includes(m.test + m.corner) && m.status === "WARN").length;
  const selRow = sel ? MATRIX.find((m) => m.test + m.corner === sel) : null;

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-background">
      <div className="flex h-[30px] shrink-0 items-center gap-3 border-b border-border bg-chrome px-2 text-[11px]">
        <span className="text-muted-foreground">
          Plan <span className="num text-foreground">ota_core_signoff</span>
        </span>
        <span className="num text-success">{pass} pass</span>
        <span className="num text-critical">{fail} fail</span>
        <span className="num text-warning">{warn} warn</span>
        <span className="num text-subtle">
          {done.length}/{total} complete
        </span>
        <span className="h-[5px] w-[140px] overflow-hidden rounded-[1px] bg-raised">
          <span className="block h-full bg-primary transition-all" style={{ width: `${(done.length / total) * 100}%` }} />
        </span>
        <button
          onClick={() => setRunning(true)}
          className="ml-auto flex h-[22px] items-center gap-1 rounded-[3px] bg-success/15 px-2 text-[11px] text-success hover:bg-success/25"
        >
          <Play className="h-[12px] w-[12px]" /> Run Plan
        </button>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[1fr_260px] overflow-hidden">
        <div className="min-h-0 overflow-auto">
          <SectionTitle>Test × Corner Matrix</SectionTitle>
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className={th}>Test</th>
                {CORNERS.map((c) => (
                  <th key={c.id} className={th}>
                    {c.id} · {c.temp}°C · {c.supply}V
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {TESTS.map((t) => (
                <tr key={t}>
                  <td className={cn(td, "text-foreground")}>{t}</td>
                  {CORNERS.map((c) => {
                    const m = cell(t, c.id);
                    const key = t + c.id;
                    const complete = done.includes(key);
                    return (
                      <td
                        key={c.id}
                        onClick={() => setSel(key)}
                        className={cn(td, "cursor-default", sel === key && "bg-primary/15")}
                      >
                        <StatusCell status={complete ? (m.status as Status) : running ? "RUNNING" : "NOT RUN"} />
                        {complete && <span className="num ml-2 text-[10px] text-subtle">{m.runtime}</span>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>

          {selRow && (
            <>
              <SectionTitle>
                {selRow.test} — {selRow.corner}
              </SectionTitle>
              <table className="w-full border-collapse">
                <thead>
                  <tr>
                    {["Metric", "Value", "Spec", "Status"].map((h) => (
                      <th key={h} className={th}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[
                    ["DC Gain", `${selRow.gain} dB`, "> 60 dB"],
                    ["UGBW", `${selRow.ugbw} MHz`, "> 150 MHz"],
                    ["Phase Margin", `${selRow.pm} °`, "> 60 °"],
                    ["Noise", `${selRow.noise} µVrms`, "< 20 µVrms"],
                    ["Power", `${selRow.power} mW`, "< 2.5 mW"],
                  ].map((r) => (
                    <tr key={r[0]}>
                      <td className={td}>{r[0]}</td>
                      <td className={cn(td, "num text-right")}>{r[1]}</td>
                      <td className={cn(td, "num text-right text-muted-foreground")}>{r[2]}</td>
                      <td className={td}>
                        <StatusCell status={selRow.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          <SectionTitle>Nominal Summary</SectionTitle>
          <div className="grid grid-cols-3 gap-px bg-border">
            {NOMINAL.map(([k, v]) => (
              <div key={k} className="bg-panel px-2 py-[6px]">
                <div className="text-[10px] text-subtle">{k}</div>
                <div className="num text-[12px] text-foreground">{v}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="min-h-0 overflow-auto border-l border-border bg-panel">
          <SectionTitle>Run Plan</SectionTitle>
          {RUN_PLAN.map((p) => (
            <div key={p} className="flex items-center gap-2 border-b border-border/40 px-2 py-[6px] text-[11px]">
              <StatusCell status={plan.includes(p) || (!running && done.length === total) ? "PASS" : running ? "RUNNING" : "NOT RUN"} />
              <span className="text-foreground">{p}</span>
            </div>
          ))}
          <SectionTitle>Coverage</SectionTitle>
          <div className="space-y-2 p-2">
            {[
              ["Corners", 100],
              ["Temperature", 83],
              ["Supply", 66],
              ["Monte Carlo", 40],
              ["Post-layout", s.postLayout ? 100 : 0],
            ].map(([l, p]) => (
              <div key={l as string}>
                <div className="num mb-[3px] flex justify-between text-[10px] text-subtle">
                  <span>{l as string}</span>
                  <span>{p as number}%</span>
                </div>
                <Bar pct={p as number} />
              </div>
            ))}
          </div>
          <SectionTitle>Specification Margins</SectionTitle>
          {MARGINS.map((m) => (
            <div key={m.name} className="border-b border-border/40 px-2 py-[6px]">
              <div className="num mb-[3px] flex justify-between text-[11px]">
                <span>{m.name}</span>
                <span className={m.status === "FAIL" ? "text-critical" : "text-success"}>{m.margin}</span>
              </div>
              <Bar pct={m.pct} tone={m.status === "FAIL" ? "bg-critical" : "bg-success"} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
