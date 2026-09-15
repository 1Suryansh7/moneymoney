import { useState } from "react";
import { DRC_VIOLATIONS, LVS_SUMMARY, PEX_SUMMARY, POSTLAYOUT } from "../data";
import { useStore } from "../store";
import { Bar, Field, SectionTitle, StatusCell, StatusDot, td, th } from "../ui";
import { cn } from "@/lib/utils";
import { Play } from "lucide-react";

const TABS = ["DRC", "LVS", "ERC", "Extraction", "Post-Layout"] as const;

export function PhysicalVerification() {
  const s = useStore();
  const [tab, setTab] = useState<(typeof TABS)[number]>("DRC");
  const [rules, setRules] = useState("gpdk65.drc");
  const [erc, setErc] = useState(false);

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-background">
      <div className="flex h-[28px] shrink-0 items-center gap-1 border-b border-border bg-chrome px-2">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              "h-[22px] rounded-[3px] px-2 text-[11px]",
              tab === t ? "bg-raised text-primary" : "text-muted-foreground hover:bg-raised/60"
            )}
          >
            {t}
          </button>
        ))}
        <span className="num ml-auto text-[11px] text-subtle">
          Cell ota_core / layout · Rules {rules}
        </span>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {tab === "DRC" && (
          <>
            <div className="flex items-center gap-2 border-b border-border bg-panel px-2 py-[6px] text-[11px]">
              <span className="text-subtle">Rule deck</span>
              <select
                value={rules}
                onChange={(e) => setRules(e.target.value)}
                className="num h-[22px] rounded-[3px] border border-border bg-background px-1 text-[11px]"
              >
                <option>gpdk65.drc</option>
                <option>gpdk65_signoff.drc</option>
                <option>gpdk65_density.drc</option>
              </select>
              <label className="flex items-center gap-1">
                <input type="checkbox" defaultChecked className="h-[11px] w-[11px] accent-[color:var(--color-primary)]" /> Hierarchical
              </label>
              <label className="flex items-center gap-1">
                <input type="checkbox" className="h-[11px] w-[11px] accent-[color:var(--color-primary)]" /> Incremental
              </label>
              <button
                onClick={s.runDrc}
                className="ml-auto flex h-[22px] items-center gap-1 rounded-[3px] bg-success/15 px-2 text-success hover:bg-success/25"
              >
                <Play className="h-[12px] w-[12px]" /> Run DRC
              </button>
            </div>
            <div className="flex items-center gap-4 border-b border-border px-2 py-[6px] text-[11px]">
              <StatusDot status={s.drcDone ? "FAIL" : "NOT RUN"} />
              <span className="num">
                {s.drcDone ? `${DRC_VIOLATIONS.length} violations across 3 rules` : "Not run"}
              </span>
              <span className="num text-critical">
                {DRC_VIOLATIONS.filter((v) => v.severity === "Error").length} errors
              </span>
              <span className="num text-warning">
                {DRC_VIOLATIONS.filter((v) => v.severity === "Warning").length} warnings
              </span>
            </div>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {["#", "Rule", "Layer", "Severity", "X µm", "Y µm", "Description"].map((h) => (
                    <th key={h} className={th}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(s.drcDone ? DRC_VIOLATIONS : []).map((v) => (
                  <tr
                    key={v.id}
                    onClick={() => {
                      s.setActiveDrc(v.id);
                      s.setOverlay("DRC");
                      s.openTab({ id: "layout", label: "ota_core : layout" });
                      s.setStatusMsg(`Zoomed to violation ${v.id}`);
                    }}
                    className={cn("cursor-default hover:bg-raised/60", s.activeDrc === v.id && "bg-primary/15")}
                  >
                    <td className={cn(td, "num")}>{v.id}</td>
                    <td className={cn(td, "num text-primary")}>{v.rule}</td>
                    <td className={cn(td, "num")}>{v.layer}</td>
                    <td className={td}>
                      <StatusCell status={v.severity === "Error" ? "FAIL" : "WARN"} />
                    </td>
                    <td className={cn(td, "num text-right")}>{v.x.toFixed(2)}</td>
                    <td className={cn(td, "num text-right")}>{v.y.toFixed(2)}</td>
                    <td className={cn(td, "text-muted-foreground")}>{v.text}</td>
                  </tr>
                ))}
                {!s.drcDone && (
                  <tr>
                    <td className={cn(td, "text-subtle")} colSpan={7}>
                      Run DRC to populate results.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </>
        )}

        {tab === "LVS" && (
          <>
            <div className="flex items-center gap-3 border-b border-border bg-panel px-2 py-[6px] text-[11px]">
              <button
                onClick={() => {
                  s.setLvsMismatch(false);
                  s.log("LVS complete: netlists match");
                }}
                className="flex h-[22px] items-center gap-1 rounded-[3px] bg-success/15 px-2 text-success hover:bg-success/25"
              >
                <Play className="h-[12px] w-[12px]" /> Run LVS
              </button>
              <button
                onClick={() => {
                  s.setLvsMismatch(true);
                  s.log("LVS: 1 mismatched net (VCM), 1 property error", "err");
                }}
                className="h-[22px] rounded-[3px] border border-border px-2 text-muted-foreground hover:bg-raised"
              >
                Inject mismatch
              </button>
              <span className="num ml-auto flex items-center gap-2">
                <StatusDot status={s.lvsMismatch ? "FAIL" : "PASS"} />
                {s.lvsMismatch ? "MISMATCH" : "MATCH"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-px bg-border">
              {(
                [
                  ["Schematic", LVS_SUMMARY.schematic],
                  ["Layout", LVS_SUMMARY.layout],
                ] as const
              ).map(([label, d]) => (
                <div key={label} className="bg-panel">
                  <SectionTitle>{label}</SectionTitle>
                  <Field label="Devices" value={String(d.devices)} />
                  <Field label="Nets" value={String(s.lvsMismatch && label === "Layout" ? d.nets + 1 : d.nets)} />
                  <Field label="Pins" value={String(d.pins)} />
                </div>
              ))}
            </div>
            <SectionTitle>Comparison</SectionTitle>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {["Category", "Schematic", "Layout", "Status"].map((h) => (
                    <th key={h} className={th}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  ["Devices", "38", "38", "PASS"],
                  ["Nets", "52", s.lvsMismatch ? "53" : "52", s.lvsMismatch ? "FAIL" : "PASS"],
                  ["Ports", "8", "8", "PASS"],
                  ["Properties", "310", s.lvsMismatch ? "309" : "310", s.lvsMismatch ? "FAIL" : "PASS"],
                ].map((r) => (
                  <tr key={r[0]}>
                    <td className={td}>{r[0]}</td>
                    <td className={cn(td, "num text-right")}>{r[1]}</td>
                    <td className={cn(td, "num text-right")}>{r[2]}</td>
                    <td className={td}>
                      <StatusCell status={r[3]} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {s.lvsMismatch && (
              <>
                <SectionTitle>Mismatches</SectionTitle>
                <table className="w-full border-collapse">
                  <thead>
                    <tr>
                      {["Type", "Object", "Schematic", "Layout"].map((h) => (
                        <th key={h} className={th}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className={cn(td, "text-critical")}>Net</td>
                      <td className={cn(td, "num")}>VCM</td>
                      <td className={cn(td, "num")}>1 net</td>
                      <td className={cn(td, "num")}>2 fragments (open)</td>
                    </tr>
                    <tr>
                      <td className={cn(td, "text-critical")}>Property</td>
                      <td className={cn(td, "num")}>M6.W</td>
                      <td className={cn(td, "num")}>16 µm</td>
                      <td className={cn(td, "num")}>15.2 µm</td>
                    </tr>
                  </tbody>
                </table>
              </>
            )}
          </>
        )}

        {tab === "ERC" && (
          <>
            <div className="flex items-center gap-3 border-b border-border bg-panel px-2 py-[6px] text-[11px]">
              <button
                onClick={() => {
                  setErc(true);
                  s.log("ERC complete: 1 warning (floating gate M7)", "warn");
                }}
                className="flex h-[22px] items-center gap-1 rounded-[3px] bg-success/15 px-2 text-success hover:bg-success/25"
              >
                <Play className="h-[12px] w-[12px]" /> Run ERC
              </button>
              <span className="num text-subtle">Deck gpdk65.erc</span>
            </div>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {["Check", "Result", "Detail"].map((h) => (
                    <th key={h} className={th}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  ["Floating gates", erc ? "WARN" : "NOT RUN", "M7.G not driven in bias_gen"],
                  ["Shorted supplies", erc ? "PASS" : "NOT RUN", "VDD / VSS isolated"],
                  ["Missing substrate taps", erc ? "PASS" : "NOT RUN", "All wells tapped"],
                  ["Antenna ratio", erc ? "PASS" : "NOT RUN", "Max 82 : limit 400"],
                ].map((r) => (
                  <tr key={r[0]}>
                    <td className={td}>{r[0]}</td>
                    <td className={td}>
                      <StatusCell status={r[1]} />
                    </td>
                    <td className={cn(td, "num text-muted-foreground")}>{r[2]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {tab === "Extraction" && (
          <>
            <div className="flex items-center gap-3 border-b border-border bg-panel px-2 py-[6px] text-[11px]">
              <span className="text-subtle">Mode</span>
              <select className="num h-[22px] rounded-[3px] border border-border bg-background px-1 text-[11px]">
                <option>R + C + CC</option>
                <option>C only</option>
                <option>R only</option>
              </select>
              <button
                onClick={() => {
                  s.setPexDone(true);
                  s.log("Extraction complete: 1,482 R / 3,761 C generated");
                }}
                className="ml-auto flex h-[22px] items-center gap-1 rounded-[3px] bg-success/15 px-2 text-success hover:bg-success/25"
              >
                <Play className="h-[12px] w-[12px]" /> Run Extraction
              </button>
            </div>
            {s.pexDone ? (
              <>
                <SectionTitle>Parasitic Summary</SectionTitle>
                {PEX_SUMMARY.map(([k, v]) => (
                  <Field key={k} label={k} value={v} />
                ))}
                <SectionTitle>Top Coupling Nets</SectionTitle>
                <table className="w-full border-collapse">
                  <thead>
                    <tr>
                      {["Net", "C total", "Cc", "R"].map((h) => (
                        <th key={h} className={th}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ["VOUTP", "142.6 fF", "38.1 fF", "18.2 Ω"],
                      ["VOUTN", "139.4 fF", "37.4 fF", "17.9 Ω"],
                      ["VTAIL", "88.1 fF", "12.0 fF", "9.4 Ω"],
                      ["VCM", "61.7 fF", "8.8 fF", "22.6 Ω"],
                    ].map((r) => (
                      <tr key={r[0]}>
                        <td className={cn(td, "num text-primary")}>{r[0]}</td>
                        <td className={cn(td, "num text-right")}>{r[1]}</td>
                        <td className={cn(td, "num text-right")}>{r[2]}</td>
                        <td className={cn(td, "num text-right")}>{r[3]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : (
              <div className="p-3 text-[11px] text-subtle">Run extraction to generate the parasitic netlist.</div>
            )}
          </>
        )}

        {tab === "Post-Layout" && (
          <>
            <div className="flex items-center gap-3 border-b border-border bg-panel px-2 py-[6px] text-[11px]">
              <button
                disabled={!s.pexDone}
                onClick={() => {
                  s.setPostLayout(true);
                  s.runSimulation();
                  s.log("Post-layout simulation launched with extracted view");
                }}
                className="flex h-[22px] items-center gap-1 rounded-[3px] bg-success/15 px-2 text-success hover:bg-success/25 disabled:opacity-40"
              >
                <Play className="h-[12px] w-[12px]" /> Simulate Extracted View
              </button>
              {!s.pexDone && <span className="text-subtle">Extraction required first</span>}
            </div>
            <SectionTitle>Pre vs Post Layout</SectionTitle>
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  {["Metric", "Pre-layout", "Post-layout", "Δ", "Status"].map((h) => (
                    <th key={h} className={th}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {POSTLAYOUT.map(([name, post, delta], i) => (
                  <tr key={name}>
                    <td className={td}>{name}</td>
                    <td className={cn(td, "num text-right")}>{["67.41 dB", "184.2 MHz", "63.8 °", "2.41 mW"][i]}</td>
                    <td className={cn(td, "num text-right")}>{s.postLayout ? post : "—"}</td>
                    <td className={cn(td, "num text-right", delta.startsWith("-") ? "text-critical" : "text-success")}>
                      {s.postLayout ? delta : "—"}
                    </td>
                    <td className={td}>
                      <StatusCell status={s.postLayout ? (i === 1 ? "WARN" : "PASS") : "NOT RUN"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <SectionTitle>Signoff readiness</SectionTitle>
            <div className="space-y-2 p-2">
              {[
                ["DRC clean", s.drcDone ? 40 : 0],
                ["LVS clean", s.lvsMismatch ? 0 : 100],
                ["Extraction", s.pexDone ? 100 : 0],
                ["Post-layout sim", s.postLayout ? 100 : 0],
              ].map(([l, p]) => (
                <div key={l as string}>
                  <div className="num mb-[3px] flex justify-between text-[10px] text-subtle">
                    <span>{l as string}</span>
                    <span>{p as number}%</span>
                  </div>
                  <Bar pct={p as number} tone={(p as number) === 100 ? "bg-success" : "bg-warning"} />
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
