import { useState } from "react";
import {
  CONFIG_BINDINGS,
  CONSTRAINTS,
  LAYERS,
  LIBRARIES,
  LIB_CELLS,
  PROJECT,
  REVISIONS,
  STACK,
  TECH_DEVICES,
} from "../data";
import { useStore } from "../store";
import { Bar, Field, SectionTitle, StatusCell, StatusDot, td, th } from "../ui";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ library */
export function LibraryManager() {
  const s = useStore();
  const [lib, setLib] = useState("aurora_65");
  const [cell, setCell] = useState("ota_core");
  const cells = LIB_CELLS[lib] ?? [];
  const views = cells.find((c) => c.name === cell)?.views ?? [];

  return (
    <div className="grid min-h-0 flex-1 grid-cols-[220px_1fr_260px] bg-background">
      <div className="min-h-0 overflow-auto border-r border-border bg-panel">
        <SectionTitle>Libraries</SectionTitle>
        {LIBRARIES.map((l) => (
          <button
            key={l.name}
            onClick={() => {
              setLib(l.name);
              setCell((LIB_CELLS[l.name] ?? [])[0]?.name ?? "");
            }}
            className={cn(
              "block w-full border-b border-border/40 px-2 py-[6px] text-left text-[11px] hover:bg-raised/60",
              lib === l.name && "bg-primary/15 text-primary"
            )}
          >
            <div className="num flex justify-between">
              <span>{l.name}</span>
              <span className="text-subtle">{l.cells}</span>
            </div>
            <div className="num text-[10px] text-subtle">
              {l.path} · {l.writable ? "RW" : "RO"}
            </div>
          </button>
        ))}
      </div>

      <div className="min-h-0 overflow-auto">
        <SectionTitle>Cells — {lib}</SectionTitle>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {["Cell", "Views", "Modified"].map((h) => (
                <th key={h} className={th}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cells.map((c) => (
              <tr
                key={c.name}
                onClick={() => setCell(c.name)}
                onDoubleClick={() => s.openTab({ id: "schematic", label: `${c.name} : schematic` })}
                className={cn("cursor-default hover:bg-raised/60", cell === c.name && "bg-primary/15")}
              >
                <td className={cn(td, "num text-foreground")}>{c.name}</td>
                <td className={cn(td, "num text-muted-foreground")}>{c.views.join(", ")}</td>
                <td className={cn(td, "num text-subtle")}>{c.modified}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="min-h-0 overflow-auto border-l border-border bg-panel">
        <SectionTitle>Views — {cell}</SectionTitle>
        {views.map((v) => (
          <button
            key={v}
            onDoubleClick={() =>
              s.openTab(
                v === "layout"
                  ? { id: "layout", label: `${cell} : layout` }
                  : { id: "schematic", label: `${cell} : ${v}` }
              )
            }
            className="block w-full border-b border-border/40 px-2 py-[6px] text-left text-[11px] hover:bg-raised/60"
          >
            <span className="num">{v}</span>
          </button>
        ))}
        <SectionTitle>Revision History</SectionTitle>
        {REVISIONS.map((r) => (
          <div key={r.rev} className="border-b border-border/40 px-2 py-[5px] text-[11px]">
            <div className="num flex justify-between">
              <span className="text-primary">{r.rev}</span>
              <span className="text-subtle">
                {r.who} · {r.when}
              </span>
            </div>
            <div className="text-muted-foreground">{r.msg}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ project */
export function ProjectDashboard() {
  const s = useStore();
  return (
    <div className="min-h-0 flex-1 overflow-auto bg-background">
      <SectionTitle>Project</SectionTitle>
      <div className="grid grid-cols-3 gap-px bg-border">
        {[
          ["Project", PROJECT.name],
          ["Technology", PROJECT.technology],
          ["PDK", PROJECT.pdk],
          ["Top cell", PROJECT.topCell],
          ["Supply", PROJECT.supply],
          ["Owner", "Y. Salem"],
        ].map(([k, v]) => (
          <div key={k} className="bg-panel px-2 py-[6px]">
            <div className="text-[10px] text-subtle">{k}</div>
            <div className="num text-[12px]">{v}</div>
          </div>
        ))}
      </div>
      <div className="px-2 py-2 text-[11px] text-muted-foreground">{PROJECT.description}</div>

      <SectionTitle>Signoff Status</SectionTitle>
      <table className="w-full border-collapse">
        <thead>
          <tr>
            {["Stage", "Status", "Detail"].map((h) => (
              <th key={h} className={th}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[
            ["Schematic", "NOT RUN", "use Check in Schematic Editor"],
            [
              "Simulation",
              s.simPhase === "COMPLETE" ? "COMPLETE" : "NOT RUN",
              s.measuredGain
                ? `DC gain ${s.measuredGain.value.toFixed(2)} ${s.measuredGain.unit}`
                : "no live run yet",
            ],
            ["Layout", "NOT RUN", "no layout backend (Stage 8)"],
            ["DRC", "NOT RUN", "mock runner only (Stage 8)"],
            ["LVS", "NOT RUN", "no LVS backend (Stage 8)"],
            ["Extraction", "NOT RUN", "no PEX backend (Stage 9)"],
            ["Post-layout", "NOT RUN", "no extracted netlist (Stage 9)"],
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

      <div className="grid grid-cols-2 gap-px bg-border">
        <div className="bg-panel">
          <SectionTitle>Measured</SectionTitle>
          <Field
            label="DC gain"
            value={
              s.measuredGain
                ? `${s.measuredGain.value.toFixed(2)} ${s.measuredGain.unit}`
                : "NOT RUN"
            }
          />
          <Field label="Sim phase" value={s.simPhase} />
          <Field label="Backend" value={s.backendUp === false ? "unreachable" : "up"} />
        </div>
        <div className="bg-panel">
          <SectionTitle>Margins</SectionTitle>
          <div className="num px-2 py-[6px] text-[11px] text-subtle">
            No specs loaded — margins appear once specifications bind to measurements.
          </div>
        </div>
      </div>
    </div>
  );
}

/* --------------------------------------------------------------- technology */
export function TechnologyBrowser() {
  return (
    <div className="grid min-h-0 flex-1 grid-cols-[1fr_1fr_200px] bg-background">
      <div className="min-h-0 overflow-auto border-r border-border">
        <SectionTitle>Devices</SectionTitle>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {["Device", "Min L", "VDD", "Parameters"].map((h) => (
                <th key={h} className={th}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {TECH_DEVICES.map((d) => (
              <tr key={d.name} className="hover:bg-raised/60">
                <td className={cn(td, "num text-primary")}>{d.name}</td>
                <td className={cn(td, "num")}>{d.minL}</td>
                <td className={cn(td, "num")}>{d.vdd}</td>
                <td className={cn(td, "num text-subtle")}>{d.params.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="min-h-0 overflow-auto border-r border-border">
        <SectionTitle>Layers</SectionTitle>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              {["", "Layer", "Purpose", "Color"].map((h) => (
                <th key={h} className={th}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {LAYERS.map((l) => (
              <tr key={l.name} className="hover:bg-raised/60">
                <td className={td}>
                  <span className="inline-block h-[10px] w-[14px] border border-border" style={{ background: l.color, opacity: l.fill }} />
                </td>
                <td className={cn(td, "num")}>{l.name}</td>
                <td className={cn(td, "num text-subtle")}>{l.purpose}</td>
                <td className={cn(td, "num text-subtle")}>{l.color}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <SectionTitle>Design Rules</SectionTitle>
        {[
          ["M1 min width", "0.090 µm"],
          ["M1 min space", "0.090 µm"],
          ["Poly min width", "0.060 µm"],
          ["Via1 enclosure", "0.015 µm"],
          ["Nwell min space", "0.600 µm"],
          ["M2 density", "20 %"],
        ].map(([k, v]) => (
          <Field key={k} label={k} value={v} />
        ))}
      </div>
      <div className="min-h-0 overflow-auto bg-panel">
        <SectionTitle>Layer Stack</SectionTitle>
        {STACK.map((l, i) => (
          <div
            key={l}
            className="num flex items-center justify-between border-b border-border/40 px-2 py-[5px] text-[11px]"
            style={{ background: `color-mix(in oklab, var(--color-primary) ${Math.max(0, 14 - i)}%, transparent)` }}
          >
            <span>{l}</span>
            <span className="text-subtle">{(0.6 - i * 0.03).toFixed(2)} µm</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------- config */
export function HierarchyConfig() {
  return (
    <div className="min-h-0 flex-1 overflow-auto bg-background">
      <SectionTitle>Hierarchy Configuration — ota_core</SectionTitle>
      <table className="w-full border-collapse">
        <thead>
          <tr>
            {["Instance", "Cell", "View to use", "Available"].map((h) => (
              <th key={h} className={th}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {CONFIG_BINDINGS.map((b) => (
            <tr key={b.inst} className="hover:bg-raised/60">
              <td className={cn(td, "num")}>{b.inst}</td>
              <td className={cn(td, "num text-primary")}>{b.cell}</td>
              <td className={td}>
                <select
                  defaultValue={b.view}
                  className="num h-[22px] rounded-[3px] border border-border bg-background px-1 text-[11px]"
                >
                  {["schematic", "symbol", "extracted", "spectre"].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </td>
              <td className={cn(td, "num text-subtle")}>schematic, symbol, extracted</td>
            </tr>
          ))}
        </tbody>
      </table>
      <SectionTitle>Global Bindings</SectionTitle>
      <Field label="View list" value="spectre extracted schematic symbol" />
      <Field label="Stop list" value="spectre" />
      <Field label="Bind mode" value="Use config" />
    </div>
  );
}

/* ------------------------------------------------------------ design intent */
export function DesignIntent() {
  const s = useStore();
  return (
    <div className="min-h-0 flex-1 overflow-auto bg-background">
      {CONSTRAINTS.map((g) => (
        <div key={g.group}>
          <SectionTitle>{g.group}</SectionTitle>
          <table className="w-full border-collapse">
            <thead>
              <tr>
                {["Constraint", "Type", "Members", "Orientation", "Topology", "Dummies", "Mismatch"].map((h) => (
                  <th key={h} className={th}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {g.items.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => s.setSelection({ kind: "constraint", id: c.id })}
                  className={cn(
                    "cursor-default hover:bg-raised/60",
                    s.selection?.kind === "constraint" && s.selection.id === c.id && "bg-primary/15"
                  )}
                >
                  <td className={cn(td, "num text-primary")}>{c.id}</td>
                  <td className={cn(td, "text-muted-foreground")}>{c.type}</td>
                  <td className={cn(td, "num")}>{c.members.join(", ")}</td>
                  <td className={cn(td, "num")}>{c.orientation}</td>
                  <td className={cn(td, "num")}>{c.topology}</td>
                  <td className={cn(td, "num")}>{c.dummies}</td>
                  <td className={cn(td, "num text-right")}>{c.mismatch}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

/* --------------------------------------------------------------------- jobs */
export function JobMonitor() {
  const s = useStore();
  return (
    <div className="min-h-0 flex-1 overflow-auto bg-background">
      <SectionTitle>Compute Jobs</SectionTitle>
      <table className="w-full border-collapse">
        <thead>
          <tr>
            {["Job ID", "Type", "Cell", "Host", "Status", "Progress", "Runtime", ""].map((h) => (
              <th key={h} className={th}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {s.jobs.map((j) => (
            <tr key={j.id} className="hover:bg-raised/60">
              <td className={cn(td, "num text-primary")}>{j.id}</td>
              <td className={cn(td, "num")}>{j.type}</td>
              <td className={cn(td, "num")}>{j.cell}</td>
              <td className={cn(td, "num text-subtle")}>{j.host}</td>
              <td className={td}>
                <span className="flex items-center gap-1.5">
                  <StatusDot status={j.status === "Complete" ? "PASS" : j.status === "Failed" ? "FAIL" : j.status === "Running" ? "RUNNING" : "NOT RUN"} />
                  <span className="num">{j.status}</span>
                </span>
              </td>
              <td className={td}>
                <Bar pct={j.progress} />
              </td>
              <td className={cn(td, "num text-right")}>{j.runtime}</td>
              <td className={td}>
                <button
                  onClick={() => s.log(`Job ${j.id} cancelled`, "warn")}
                  className="rounded-[2px] border border-border px-1.5 text-[10px] text-muted-foreground hover:bg-raised"
                >
                  Cancel
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <SectionTitle>Compute Resources</SectionTitle>
      <div className="grid grid-cols-3 gap-px bg-border">
        {[
          ["local", 34],
          ["compute03", 78],
          ["farm", 12],
        ].map(([h, u]) => (
          <div key={h as string} className="bg-panel px-2 py-2">
            <div className="num mb-1 flex justify-between text-[11px]">
              <span>{h as string}</span>
              <span className="text-subtle">{u as number}%</span>
            </div>
            <Bar pct={u as number} />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ----------------------------------------------------------------- settings */
export function SettingsWorkspace() {
  const s = useStore();
  return (
    <div className="min-h-0 flex-1 overflow-auto bg-background">
      <SectionTitle>Appearance</SectionTitle>
      <div className="flex gap-2 p-2">
        {[
          ["graphite", "Graphite Dark"],
          ["light", "Light Workstation"],
          ["contrast", "High Contrast"],
        ].map(([id, label]) => (
          <button
            key={id}
            onClick={() => s.setTheme(id)}
            className={cn(
              "h-[26px] rounded-[3px] border border-border px-3 text-[11px]",
              s.theme === id ? "bg-primary text-primary-foreground" : "hover:bg-raised"
            )}
          >
            {label}
          </button>
        ))}
      </div>
      <SectionTitle>Editor</SectionTitle>
      {[
        ["Grid spacing", "0.005 µm"],
        ["Snap mode", "orthogonal"],
        ["Default wire width", "0.10 µm"],
        ["Autosave interval", "5 min"],
        ["Cursor", "crosshair"],
      ].map(([k, v]) => (
        <Field key={k} label={k} value={v} />
      ))}
      <SectionTitle>Simulation</SectionTitle>
      {[
        ["Default simulator", "Generic SPICE"],
        ["Threads", "8"],
        ["Results directory", "~/simulation/aurora_65"],
      ].map(([k, v]) => (
        <Field key={k} label={k} value={v} />
      ))}
      <SectionTitle>Keyboard</SectionTitle>
      {[
        ["Command palette", "Ctrl K"],
        ["Run simulation", "Ctrl R"],
        ["Save", "Ctrl S"],
        ["Zoom fit", "F"],
        ["Shortcuts overlay", "?"],
      ].map(([k, v]) => (
        <Field key={k} label={k} value={v} />
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------- start */
export function StartPage() {
  const s = useStore();
  return (
    <div className="min-h-0 flex-1 overflow-auto bg-background p-6">
      <h1 className="text-[18px] font-semibold tracking-tight text-foreground">Axiom IC Studio</h1>
      <p className="mt-1 text-[11px] text-muted-foreground">Custom analog / mixed-signal design environment</p>
      <div className="mt-5 grid max-w-[820px] grid-cols-2 gap-px bg-border">
        {[
          ["Open Project", "aurora_65 — 65 nm OTA", "project" as const],
          ["Library Manager", "4 libraries, 535 cells", "library" as const],
          ["Schematic Editor", "ota_core / schematic", "schematic" as const],
          ["Layout Editor", "ota_core / layout", "layout" as const],
          ["Simulation Explorer", "tb_ota_ac", "sim" as const],
          ["Physical Verification", "DRC / LVS / PEX", "pv" as const],
        ].map(([title, sub, ws]) => (
          <button
            key={title as string}
            onClick={() => s.openTab({ id: ws as never, label: title as string })}
            className="bg-panel px-3 py-3 text-left hover:bg-raised"
          >
            <div className="text-[12px] text-foreground">{title as string}</div>
            <div className="num text-[10px] text-subtle">{sub as string}</div>
          </button>
        ))}
      </div>
      <SectionTitle>Recent</SectionTitle>
      {REVISIONS.map((r) => (
        <div key={r.rev} className="num max-w-[820px] border-b border-border/40 py-[5px] text-[11px]">
          <span className="text-primary">{r.rev}</span> <span className="text-muted-foreground">{r.msg}</span>{" "}
          <span className="text-subtle">
            {r.who} · {r.when}
          </span>
        </div>
      ))}
    </div>
  );
}
