import { INSTANCES, NETS, CONSTRAINTS, MARGINS, NOMINAL, LAYOUT_SHAPES } from "../data";
import { useStore } from "../store";
import { Bar, Field, SectionTitle, StatusCell } from "../ui";
import { cn } from "@/lib/utils";
import { useState } from "react";

const TABS = ["Properties", "Navigator", "Constraints", "Annotations", "Find", "Insights"];

function InstanceProps({ id }: { id: string }) {
  const s = useStore();
  const inst = INSTANCES.find((i) => i.id === id);
  if (!inst) return <div className="p-2 text-[11px] text-subtle">No object selected.</div>;
  return (
    <div>
      <div className="flex items-baseline gap-2 border-b border-border bg-raised px-2 py-1.5">
        <span className="num text-[13px] text-foreground">{inst.id}</span>
        <span className="text-[11px] text-muted-foreground">{inst.cell}</span>
        <span className="num ml-auto text-[10px] text-subtle">{inst.type}</span>
      </div>
      <SectionTitle>Parameters</SectionTitle>
      <Field label="Name" value={inst.id} />
      <Field label="Cell" value={inst.cell} />
      <Field label="Model" value={inst.type === "pmos" ? "pmos65" : inst.type === "nmos" ? "nmos65" : inst.cell} />
      {Object.entries(inst.params).map(([k, v]) => (
        <Field key={k} label={k} value={String(v)} />
      ))}
      <SectionTitle>Connectivity</SectionTitle>
      {Object.entries(inst.conn ?? {}).map(([t, net]) => (
        <button
          key={t}
          onClick={() => s.setSelection({ kind: "net", id: net })}
          className="flex w-full items-baseline justify-between border-b border-border/50 px-2 py-[5px] text-left hover:bg-raised/60"
        >
          <span className="num text-[11px] text-muted-foreground">{t}</span>
          <span className="num text-[11px] text-primary">{net}</span>
        </button>
      ))}
      <SectionTitle>Operating Point</SectionTitle>
      {Object.entries(inst.op ?? {}).map(([k, v]) => (
        <Field key={k} label={k} value={v} tone={k === "region" ? "text-success" : undefined} />
      ))}
      <SectionTitle>Constraints</SectionTitle>
      <Field label="Matched Group" value={id === "M1" || id === "M2" ? "INPUT_PAIR" : "—"} />
      <Field label="Topology" value={id === "M1" || id === "M2" ? "Common Centroid" : "—"} />
      <SectionTitle>Simulation</SectionTitle>
      <Field label="Save currents" value="yes" />
      <Field label="Probe" value="none" />
    </div>
  );
}

function NetProps({ id }: { id: string }) {
  const net = NETS.find((n) => n.id === id);
  if (!net) return null;
  return (
    <div>
      <div className="flex items-baseline gap-2 border-b border-border bg-raised px-2 py-1.5">
        <span className="text-[10px] tracking-wider text-subtle uppercase">Net</span>
        <span className="num text-[13px] text-cyan">{net.id}</span>
      </div>
      <SectionTitle>Summary</SectionTitle>
      <Field label="Connections" value={net.connections} />
      <Field label="Drivers" value={net.drivers} />
      <Field label="Loads" value={net.loads} />
      <Field label="Estimated C" value={net.cap} />
      <Field label="DC voltage" value={net.voltage} />
      <SectionTitle>Connected devices</SectionTitle>
      <div className="flex flex-wrap gap-1 p-2">
        {net.devices.map((d) => (
          <span
            key={d}
            className="num rounded-[2px] border border-border bg-raised px-1.5 py-[1px] text-[10px] text-muted-foreground"
          >
            {d}
          </span>
        ))}
      </div>
    </div>
  );
}

function LayoutProps({ id }: { id: string }) {
  const count = LAYOUT_SHAPES.filter((s) => s.device === id).length;
  return (
    <div>
      <div className="flex items-baseline gap-2 border-b border-border bg-raised px-2 py-1.5">
        <span className="num text-[13px]">{id === "M1" || id === "M2" ? "M1 / M2 matched pair" : id}</span>
      </div>
      <SectionTitle>PCell</SectionTitle>
      <Field label="PCell" value="nmos_1v2" />
      <Field label="W" value="12.00 µm" />
      <Field label="L" value="0.12 µm" />
      <Field label="Fingers" value="4" />
      <Field label="Multiplier" value="2" />
      <Field label="Effective width" value="96.00 µm" />
      <Field label="Shapes" value={count} />
      <SectionTitle>Placement</SectionTitle>
      <Field label="Orientation" value="R0" />
      <Field label="Matched Group" value="INPUT_PAIR" />
      <Field label="Constraint" value="Common centroid" />
      <Field label="Dummies" value="2" />
    </div>
  );
}

function Insights() {
  return (
    <div>
      <SectionTitle>Nominal</SectionTitle>
      {NOMINAL.map(([k, v]) => (
        <Field key={k} label={k} value={v} />
      ))}
      <SectionTitle>Specification margin</SectionTitle>
      {MARGINS.map((m) => (
        <div key={m.name} className="flex items-center gap-2 border-b border-border/50 px-2 py-[5px]">
          <span className="w-[52px] text-[11px] text-muted-foreground">{m.name}</span>
          <Bar pct={m.pct} tone={m.status === "FAIL" ? "bg-critical" : "bg-success"} />
          <span className="num ml-auto text-[11px]">{m.margin}</span>
          <StatusCell status={m.status} />
        </div>
      ))}
    </div>
  );
}

function Constraints() {
  const s = useStore();
  const [sel, setSel] = useState("INPUT_PAIR");
  const item = CONSTRAINTS.flatMap((g) => g.items).find((i) => i.id === sel);
  return (
    <div>
      {CONSTRAINTS.map((g) => (
        <div key={g.group}>
          <SectionTitle>{g.group}</SectionTitle>
          {g.items.map((i) => (
            <button
              key={i.id}
              onClick={() => {
                setSel(i.id);
                s.setSelection({ kind: "constraint", id: i.id });
              }}
              className={cn(
                "block w-full border-b border-border/40 px-3 py-[5px] text-left text-[11px] hover:bg-raised/60",
                sel === i.id ? "num text-primary" : "num text-muted-foreground"
              )}
            >
              {i.id}
            </button>
          ))}
        </div>
      ))}
      {item && (
        <>
          <SectionTitle>{item.id}</SectionTitle>
          <Field label="Type" value={item.type} />
          <Field label="Members" value={item.members.join(", ")} />
          <Field label="Orientation" value={item.orientation} />
          <Field label="Topology" value={item.topology} />
          <Field label="Dummy Devices" value={item.dummies} />
          <Field label="Maximum mismatch" value={item.mismatch} />
        </>
      )}
    </div>
  );
}

export function RightDock() {
  const s = useStore();
  const sel = s.selection;
  return (
    <div className="flex min-h-0 flex-1 flex-col bg-panel">
      <div className="flex h-[26px] shrink-0 items-stretch overflow-x-auto border-b border-border bg-chrome">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => s.setRightTab(t)}
            className={cn(
              "shrink-0 px-2.5 text-[11px] whitespace-nowrap",
              s.rightTab === t
                ? "bg-panel text-foreground shadow-[inset_0_-2px_0_var(--color-primary)]"
                : "text-subtle hover:text-foreground"
            )}
          >
            {t}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {s.rightTab === "Properties" &&
          (sel?.kind === "instance" ? (
            <InstanceProps id={sel.id} />
          ) : sel?.kind === "net" ? (
            <NetProps id={sel.id} />
          ) : sel?.kind === "layoutDevice" ? (
            <LayoutProps id={sel.id} />
          ) : (
            <div className="p-3 text-[11px] text-subtle">
              Nothing selected. Click a device, net or shape in the editor.
            </div>
          ))}
        {s.rightTab === "Constraints" && <Constraints />}
        {s.rightTab === "Insights" && <Insights />}
        {s.rightTab === "Navigator" && (
          <div>
            <SectionTitle>Hierarchy</SectionTitle>
            {["/ ota_core", "  XBIAS — bias_gen", "  XCMFB — cmfb", "  M1 — nmos_1v2", "  M2 — nmos_1v2", "  M5 — nmos_1v2"].map((r) => (
              <div key={r} className="num border-b border-border/40 px-2 py-[5px] text-[11px] whitespace-pre text-muted-foreground">
                {r}
              </div>
            ))}
          </div>
        )}
        {s.rightTab === "Annotations" && (
          <div>
            <SectionTitle>Annotation set</SectionTitle>
            {["DC Node Voltages", "Device Currents", "Operating Region", "gm/gds", "Power"].map((a) => (
              <label key={a} className="flex items-center gap-2 border-b border-border/40 px-2 py-[5px] text-[11px]">
                <input
                  type="checkbox"
                  checked={s.annotate === a}
                  onChange={() => s.setAnnotate(s.annotate === a ? "None" : a)}
                  className="h-[11px] w-[11px] accent-[color:var(--color-primary)]"
                />
                {a}
              </label>
            ))}
          </div>
        )}
        {s.rightTab === "Find" && (
          <div className="p-2">
            <input
              placeholder="Find object by name..."
              className="h-[24px] w-full rounded-[3px] border border-border bg-background px-2 text-[11px] focus:outline-none"
            />
            <div className="mt-2 text-[11px] text-subtle">Type a device, net or pin name.</div>
          </div>
        )}
      </div>
    </div>
  );
}
