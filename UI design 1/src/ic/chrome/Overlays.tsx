import { useState } from "react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { useCommands } from "../commands";
import { useStore } from "../store";
import { SEARCH_INDEX } from "../data";
import { SectionTitle } from "../ui";

export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const cmds = useCommands();
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[560px] gap-0 rounded-[5px] border-border bg-popover p-0">
        <Command className="bg-popover">
          <CommandInput placeholder="> Type a command..." className="h-[34px] text-[12px]" />
          <CommandList className="max-h-[340px]">
            <CommandEmpty className="p-3 text-[11px] text-subtle">No matching command.</CommandEmpty>
            <CommandGroup heading="Commands">
              {cmds.map((c) => (
                <CommandItem
                  key={c.id}
                  value={c.label}
                  onSelect={() => {
                    c.run();
                    onOpenChange(false);
                  }}
                  className="h-[26px] text-[12px]"
                >
                  {c.label}
                  <span className="num ml-auto text-[10px] text-subtle">{c.keys}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}

export function GlobalSearch({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const s = useStore();
  const [q, setQ] = useState("VOUT");
  const res = SEARCH_INDEX.filter((r) => (r.name + r.where).toLowerCase().includes(q.toLowerCase()));
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[620px] gap-0 rounded-[5px] border-border bg-popover p-0">
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search design..."
          className="h-[34px] w-full border-b border-border bg-transparent px-3 text-[12px] focus:outline-none"
        />
        <div className="max-h-[360px] overflow-auto">
          {res.map((r, i) => (
            <button
              key={i}
              onClick={() => {
                const map: Record<string, [never, string]> = {} as never;
                void map;
                if (r.ws === "layout") s.openTab({ id: "layout", label: "ota_core : layout" });
                else if (r.ws === "sim") s.openTab({ id: "sim", label: "Simulation Explorer" });
                else if (r.ws === "waveforms") s.openTab({ id: "waveforms", label: "Waveform Analyzer" });
                else if (r.ws === "pv") s.openTab({ id: "pv", label: "Physical Verification" });
                else if (r.ws === "library") s.openTab({ id: "library", label: "Library" });
                else s.openTab({ id: "schematic", label: "ota_core : schematic" });
                onOpenChange(false);
              }}
              className="flex w-full items-center gap-3 border-b border-border/40 px-3 py-1.5 text-left text-[11px] hover:bg-raised/60"
            >
              <span className="w-[70px] text-[10px] text-subtle">{r.kind}</span>
              <span className="num text-foreground">{r.name}</span>
              <span className="num ml-auto text-[10px] text-subtle">{r.where}</span>
            </button>
          ))}
          {!res.length && <div className="p-3 text-[11px] text-subtle">No matches.</div>}
        </div>
      </DialogContent>
    </Dialog>
  );
}

const SHORTCUTS: [string, string][] = [
  ["I", "Instance"],
  ["W", "Wire"],
  ["P", "Pin"],
  ["L", "Label"],
  ["M", "Move"],
  ["C", "Copy"],
  ["Delete", "Delete"],
  ["F", "Zoom Fit"],
  ["Z", "Zoom"],
  ["Shift+Z", "Zoom Out"],
  ["Ctrl+S", "Save"],
  ["Ctrl+K", "Command Palette"],
  ["Ctrl+Shift+F", "Global Search"],
  ["Ctrl+Shift+B", "Toggle Side Panels"],
  ["Esc", "Cancel Command"],
];

export function ShortcutOverlay({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[460px] gap-0 rounded-[5px] border-border bg-popover p-0">
        <SectionTitle>Common shortcuts</SectionTitle>
        <div className="grid grid-cols-2 gap-x-6 p-3">
          {SHORTCUTS.map(([k, v]) => (
            <div key={k} className="flex items-baseline justify-between border-b border-border/40 py-[5px] text-[11px]">
              <span className="num rounded-[2px] border border-border bg-raised px-1.5 text-[10px]">{k}</span>
              <span className="text-muted-foreground">{v}</span>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

import { ApiError } from "../api";

// Registered topology template ids (identifiers only — sizing defaults
// come from the backend, never duplicated here).
const TEMPLATES = [
  "current_mirror",
  "diff_pair",
  "common_source",
  "cascode",
  "folded_cascode",
  "two_stage_miller",
] as const;

export function NewCellDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const s = useStore();
  const [project, setProject] = useState("my_project");
  const [cell, setCell] = useState("");
  const [template, setTemplate] = useState<string>(TEMPLATES[2]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canCreate = !busy && cell.trim().length > 0 && project.trim().length > 0;
  const create = () => {
    if (!canCreate) return;
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        const cellId = await s.createTemplateCell(project.trim(), cell.trim(), template);
        s.log(`Created ${project.trim()}/${cell.trim()} from ${template} → ${cellId.slice(0, 8)}…`);
        onOpenChange(false);
      } catch (err) {
        setError(err instanceof ApiError ? err.detail : String(err));
      } finally {
        setBusy(false);
      }
    })();
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[400px] gap-0 rounded-[5px] border-border bg-popover p-0">
        <SectionTitle>New Cell View</SectionTitle>
        <div className="space-y-2 p-3">
          <label className="flex items-center gap-3 text-[11px]">
            <span className="w-[60px] text-muted-foreground">Project</span>
            <input
              value={project}
              onChange={(e) => setProject(e.target.value)}
              className="num h-[24px] flex-1 rounded-[3px] border border-border bg-background px-2 text-[11px] focus:outline-none"
            />
          </label>
          <label className="flex items-center gap-3 text-[11px]">
            <span className="w-[60px] text-muted-foreground">Cell</span>
            <input
              value={cell}
              onChange={(e) => setCell(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && create()}
              placeholder="e.g. my_amp"
              className="num h-[24px] flex-1 rounded-[3px] border border-border bg-background px-2 text-[11px] focus:outline-none"
            />
          </label>
          <label className="flex items-center gap-3 text-[11px]">
            <span className="w-[60px] text-muted-foreground">Template</span>
            <select
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              className="num h-[24px] flex-1 rounded-[3px] border border-border bg-background px-2 text-[11px]"
            >
              {TEMPLATES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <div className="num text-[10px] text-subtle">Backend sizing defaults apply.</div>
          {error && <div className="num text-[11px] text-critical">{error}</div>}
        </div>
        <div className="flex justify-end gap-2 border-t border-border p-2">
          <button onClick={() => onOpenChange(false)} className="h-[24px] rounded-[3px] border border-border px-3 text-[11px] hover:bg-raised">
            Cancel
          </button>
          <button
            onClick={create}
            disabled={!canCreate}
            className="h-[24px] rounded-[3px] bg-primary px-3 text-[11px] text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "Creating…" : "Create"}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function AssistPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [asked, setAsked] = useState<string | null>(null);
  if (!open) return null;
  return (
    <aside className="flex w-[320px] shrink-0 flex-col border-l border-border bg-panel">
      <div className="panel-hd">
        Axiom Assist
        <button onClick={onClose} className="ml-auto text-subtle hover:text-foreground">
          ✕
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-2 text-[11px] leading-[16px] text-muted-foreground">
        {asked ? (
          <>
            <div className="mb-2 rounded-[3px] border border-border bg-raised px-2 py-1 text-foreground">{asked}</div>
            <p>
              The SS / 125 °C / 1.08 V corner fails the phase-margin requirement by 4.7°. The largest change relative to
              nominal is associated with increased output-stage gm variation and approximately 18% higher parasitic
              capacitance at VOUTP/VOUTN.
            </p>
            <p className="mt-2">Suggested next step: increase Ccomp to 1.8 pF or raise IBIAS by 15% and re-run the SS corner.</p>
          </>
        ) : (
          <p>Ask about this design — corners, margins, DRC results or extraction deltas.</p>
        )}
      </div>
      <div className="border-t border-border p-2">
        <div className="mb-1 text-[10px] tracking-wider text-subtle uppercase">Suggested</div>
        {[
          "Explain this DRC error",
          "Summarize failing corners",
          "Find worst specification margin",
          "Compare nominal vs extracted",
          "Identify largest parasitic contributors",
        ].map((q) => (
          <button
            key={q}
            onClick={() => setAsked(q)}
            className="mb-1 block w-full rounded-[3px] border border-border px-2 py-1 text-left text-[11px] text-muted-foreground hover:bg-raised hover:text-foreground"
          >
            {q}
          </button>
        ))}
        <input
          placeholder="Ask about this design..."
          className="mt-1 h-[26px] w-full rounded-[3px] border border-border bg-background px-2 text-[11px] focus:outline-none"
        />
      </div>
    </aside>
  );
}
