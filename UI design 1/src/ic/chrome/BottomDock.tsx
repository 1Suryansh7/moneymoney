import { useEffect, useRef, useState } from "react";
import { useStore } from "../store";
import { DRC_VIOLATIONS } from "../data";
import { StatusCell, StatusDot, th, td } from "../ui";
import { cn } from "@/lib/utils";
import { ChevronDown, X } from "lucide-react";

const TABS = ["Console", "Problems", "Simulation", "Verification", "Jobs", "Search", "Markers"];

function Console() {
  const s = useStore();
  const [cmd, setCmd] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [s.console_.length]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const c = cmd.trim();
    if (!c) return;
    s.log(`axiom> ${c}`, "cmd");
    if (c === "check") {
      s.log("Checking schematic...");
      s.log("Completed: 0 errors, 2 warnings.", "warn");
    } else if (c === "help") {
      ["check", "run", "drc", "lvs", "pex", "hiLightNet <net>", "zoomFit", "save", "clear"].forEach(
        (h) => s.log("  " + h)
      );
    } else if (c === "run") {
      s.runSimulation();
    } else if (c === "drc") {
      s.runDrc();
    } else if (c === "clear") {
      s.setConsole([]);
    } else if (c === "save") {
      s.setDirty(false);
      s.log("Saved ota_core/schematic.");
    } else {
      s.log(`*Error* unbound command: ${c}`, "err");
    }
    setCmd("");
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-canvas">
      <div className="min-h-0 flex-1 overflow-auto px-2 py-1">
        {s.console_.map((l, i) => (
          <div key={i} className="num flex gap-2 text-[11px] leading-[15px]">
            {l.kind !== "cmd" && <span className="text-subtle">{l.t}</span>}
            <span
              className={cn(
                l.kind === "warn" && "text-warning",
                l.kind === "err" && "text-critical",
                l.kind === "cmd" && "text-primary",
                !l.kind && "text-muted-foreground"
              )}
            >
              {l.text}
            </span>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <form onSubmit={submit} className="flex items-center gap-2 border-t border-border bg-background px-2 py-1">
        <span className="num text-[11px] text-primary">axiom&gt;</span>
        <input
          value={cmd}
          onChange={(e) => setCmd(e.target.value)}
          aria-label="Command input"
          className="num w-full bg-transparent text-[11px] text-foreground focus:outline-none"
        />
      </form>
    </div>
  );
}

function Problems() {
  const s = useStore();
  const rows = [
    { sev: "WARN", code: "SCH-102", msg: "Possible floating gate", obj: "M7.G" },
    { sev: "WARN", code: "SCH-118", msg: "Unconnected terminal on symbol", obj: "XCMFB.VCM" },
    { sev: "PASS", code: "SCH-000", msg: "Connectivity check complete", obj: "ota_core" },
  ];
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr>
          {["Severity", "Code", "Description", "Object"].map((h) => (
            <th key={h} className={th}>
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr
            key={r.code}
            onClick={() => s.setSelection({ kind: "instance", id: r.obj.split(".")[0] })}
            className="cursor-default hover:bg-raised/60"
          >
            <td className={td}>
              <StatusCell status={r.sev} />
            </td>
            <td className={cn(td, "num")}>{r.code}</td>
            <td className={td}>{r.msg}</td>
            <td className={cn(td, "num text-primary")}>{r.obj}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Jobs() {
  const s = useStore();
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr>
          {["Job", "Type", "Cell", "Host", "Status", "Progress", "Runtime"].map((h) => (
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
            <td className={td}>{j.type}</td>
            <td className={cn(td, "num")}>{j.cell}</td>
            <td className={cn(td, "num")}>{j.host}</td>
            <td className={td}>
              <span className="flex items-center gap-1.5">
                <StatusDot status={j.status} />
                {j.status}
              </span>
            </td>
            <td className={cn(td, "num")}>{j.progress}%</td>
            <td className={cn(td, "num text-right")}>{j.runtime}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Markers() {
  const s = useStore();
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr>
          {["ID", "Rule", "Layer", "Severity", "X", "Y"].map((h) => (
            <th key={h} className={th}>
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {DRC_VIOLATIONS.map((v) => (
          <tr
            key={v.id}
            onClick={() => {
              s.setActiveDrc(v.id);
              s.openTab({ id: "layout", label: "ota_core : layout" });
            }}
            className={cn("cursor-default hover:bg-raised/60", s.activeDrc === v.id && "bg-primary/10")}
          >
            <td className={cn(td, "num")}>{v.id}</td>
            <td className={cn(td, "num")}>{v.rule}</td>
            <td className={cn(td, "num")}>{v.layer}</td>
            <td className={td}>
              <StatusCell status={v.severity} />
            </td>
            <td className={cn(td, "num text-right")}>{v.x.toFixed(2)}</td>
            <td className={cn(td, "num text-right")}>{v.y.toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function BottomDock({ onCollapse }: { onCollapse: () => void }) {
  const s = useStore();
  return (
    <div className="flex min-h-0 flex-1 flex-col border-t border-border bg-panel">
      <div className="flex h-[26px] shrink-0 items-stretch border-b border-border bg-chrome">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => s.setBottomTab(t)}
            className={cn(
              "px-3 text-[11px]",
              s.bottomTab === t
                ? "bg-panel text-foreground shadow-[inset_0_-2px_0_var(--color-primary)]"
                : "text-subtle hover:text-foreground"
            )}
          >
            {t}
            {t === "Problems" && <span className="num ml-1.5 text-warning">2</span>}
            {t === "Verification" && s.drcDone && <span className="num ml-1.5 text-critical">7</span>}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-1 pr-1">
          <button aria-label="Collapse panel" onClick={onCollapse} className="text-subtle hover:text-foreground">
            <ChevronDown className="h-[13px] w-[13px]" />
          </button>
          <button aria-label="Close panel" onClick={onCollapse} className="text-subtle hover:text-foreground">
            <X className="h-[13px] w-[13px]" />
          </button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {s.bottomTab === "Console" && <Console />}
        {s.bottomTab === "Problems" && <Problems />}
        {s.bottomTab === "Jobs" && <Jobs />}
        {s.bottomTab === "Markers" && <Markers />}
        {s.bottomTab === "Verification" && (s.drcDone ? <Markers /> : <Empty text="No DRC run in this session. Run DRC to populate markers." />)}
        {s.bottomTab === "Simulation" && (
          <div className="num p-2 text-[11px] leading-[16px] text-muted-foreground">
            {[
              "Netlisting tb_ota_ac",
              "Checking hierarchy",
              "Launching simulation",
              "Reading results",
              "Evaluating 7 expressions",
              `Simulation ${s.simPhase.toLowerCase()}`,
            ].map((l, i) => (
              <div key={i}>
                <span className="text-subtle">17:58:2{i} </span>
                {l}
              </div>
            ))}
          </div>
        )}
        {s.bottomTab === "Search" && <Empty text="No search results. Press Ctrl+Shift+F to search the design." />}
      </div>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="flex h-full items-center justify-center px-4 text-center text-[11px] text-subtle">{text}</div>
  );
}
