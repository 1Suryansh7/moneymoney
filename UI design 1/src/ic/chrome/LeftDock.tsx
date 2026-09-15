import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  CircuitBoard,
  Filter,
  FolderTree,
  Layers as LayersIcon,
  ListTree,
  MoreHorizontal,
  Search,
  Square,
  Boxes,
  FileStack,
  Bookmark,
} from "lucide-react";
import { DESIGN_TREE, LAYERS, LIBRARIES, REVISIONS, SEARCH_INDEX, type TreeNode } from "../data";
import { useStore } from "../store";
import { IconBtn, SectionTitle, StatusDot } from "../ui";
import { cn } from "@/lib/utils";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";

function Row({
  depth,
  node,
  open,
  toggle,
}: {
  depth: number;
  node: TreeNode;
  open: Set<string>;
  toggle: (id: string) => void;
}) {
  const s = useStore();
  const expandable = !!node.children?.length;
  const isOpen = open.has(node.id);
  const selectedInst = s.selection?.kind === "instance" ? s.selection.id : null;
  const highlight =
    node.kind === "cell" &&
    (node.label === "ota_core" || node.label === selectedInst?.toLowerCase());
  return (
    <>
      <ContextMenu>
        <ContextMenuTrigger asChild>
          <div
            role="treeitem"
            aria-expanded={expandable ? isOpen : undefined}
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && toggle(node.id)}
            onClick={() => {
              if (expandable) toggle(node.id);
              if (node.kind === "view") {
                if (node.view === "layout") s.openTab({ id: "layout", label: "ota_core : layout" });
                else s.openTab({ id: "schematic", label: "ota_core : schematic" });
                s.log(`Opened ${node.id.replace(":", "/")}`);
              }
            }}
            className={cn(
              "flex h-[22px] cursor-default items-center gap-1 px-1 text-[12px] hover:bg-raised/70",
              highlight && "text-foreground",
              !highlight && "text-muted-foreground"
            )}
            style={{ paddingLeft: 4 + depth * 12 }}
          >
            {expandable ? (
              isOpen ? (
                <ChevronDown className="h-3 w-3 shrink-0 text-subtle" />
              ) : (
                <ChevronRight className="h-3 w-3 shrink-0 text-subtle" />
              )
            ) : (
              <span className="w-3" />
            )}
            {node.kind === "library" && <Boxes className="h-[12px] w-[12px] text-primary" />}
            {node.kind === "group" && <FolderTree className="h-[12px] w-[12px] text-subtle" />}
            {node.kind === "cell" && <CircuitBoard className="h-[12px] w-[12px] text-cyan" />}
            {node.kind === "view" && (
              <span
                className={cn(
                  "num text-[10px]",
                  node.view === "layout"
                    ? "text-purple"
                    : node.view === "extracted"
                      ? "text-warning"
                      : "text-success"
                )}
              >
                ◇
              </span>
            )}
            <span className="truncate">{node.label}</span>
          </div>
        </ContextMenuTrigger>
        <ContextMenuContent className="min-w-[190px] text-[11px]">
          {["Open", "Open Read Only", "New View...", "Copy...", "Rename...", "Delete..."].map((i) => (
            <ContextMenuItem key={i} className="text-[11px]" onSelect={() => s.log(`${i} ${node.label}`)}>
              {i}
            </ContextMenuItem>
          ))}
          <ContextMenuSeparator />
          <ContextMenuItem className="text-[11px]">Properties</ContextMenuItem>
          <ContextMenuItem className="text-[11px]">Create Testbench...</ContextMenuItem>
          <ContextMenuItem
            className="text-[11px]"
            onSelect={() => {
              s.openTab({ id: "pv", label: "Physical Verification" });
              s.runDrc();
            }}
          >
            Run Verification...
          </ContextMenuItem>
        </ContextMenuContent>
      </ContextMenu>
      {isOpen &&
        node.children?.map((c) => (
          <Row key={c.id} node={c} depth={depth + 1} open={open} toggle={toggle} />
        ))}
    </>
  );
}

function DesignBrowser() {
  const [open, setOpen] = useState<Set<string>>(
    new Set(["aurora_65", "analog", "ota_core", "testbenches"])
  );
  const [q, setQ] = useState("");
  const toggle = (id: string) =>
    setOpen((o) => {
      const n = new Set(o);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="panel-hd">
        Design Browser
        <span className="ml-auto flex gap-0.5">
          <IconBtn label="Collapse All" onClick={() => setOpen(new Set())}>
            <ListTree className="h-[13px] w-[13px]" />
          </IconBtn>
          <IconBtn label="Filter">
            <Filter className="h-[13px] w-[13px]" />
          </IconBtn>
          <IconBtn label="More">
            <MoreHorizontal className="h-[13px] w-[13px]" />
          </IconBtn>
        </span>
      </div>
      <div className="flex h-[26px] items-center gap-1.5 border-b border-border px-2">
        <Search className="h-[12px] w-[12px] text-subtle" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search hierarchy..."
          className="w-full bg-transparent text-[11px] text-foreground placeholder:text-subtle focus:outline-none"
        />
      </div>
      <div role="tree" className="min-h-0 flex-1 overflow-auto py-0.5">
        {DESIGN_TREE.map((n) => (
          <Row key={n.id} node={n} depth={0} open={open} toggle={toggle} />
        ))}
      </div>
      <div className="border-t border-border">
        <SectionTitle>Revisions</SectionTitle>
        <div className="max-h-[130px] overflow-auto">
          {REVISIONS.map((r) => (
            <div key={r.rev} className="border-b border-border/40 px-2 py-1">
              <div className="flex items-center gap-2 text-[11px]">
                <span className="num text-primary">{r.rev}</span>
                <span className="num ml-auto text-[10px] text-subtle">
                  {r.who} {r.when}
                </span>
              </div>
              <div className="truncate text-[11px] text-muted-foreground">{r.msg}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function LayerPalette() {
  const s = useStore();
  const [q, setQ] = useState("");
  const toggle = (n: string) =>
    s.setVisibleLayers(
      s.visibleLayers.includes(n) ? s.visibleLayers.filter((x) => x !== n) : [...s.visibleLayers, n]
    );
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="panel-hd">
        Layer Palette
        <span className="ml-auto">
          <IconBtn label="Filter layers">
            <Filter className="h-[13px] w-[13px]" />
          </IconBtn>
        </span>
      </div>
      <div className="flex h-[26px] items-center gap-1.5 border-b border-border px-2">
        <Search className="h-[12px] w-[12px] text-subtle" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter layers..."
          className="w-full bg-transparent text-[11px] placeholder:text-subtle focus:outline-none"
        />
      </div>
      <div className="flex flex-wrap gap-1 border-b border-border px-2 py-1 text-[10px]">
        {[
          ["All On", () => s.setVisibleLayers(LAYERS.map((l) => l.name))],
          ["All Off", () => s.setVisibleLayers([])],
          ["Routing Only", () => s.setVisibleLayers(["M1", "M2", "M3", "M4", "V1", "V2"])],
          ["Devices Only", () => s.setVisibleLayers(["NWELL", "DIFF", "POLY", "CONT"])],
          ["Pins", () => s.setVisibleLayers(["PIN"])],
        ].map(([label, fn]) => (
          <button
            key={label as string}
            onClick={fn as () => void}
            className="rounded-[2px] border border-border px-1.5 py-[1px] text-subtle hover:bg-raised hover:text-foreground"
          >
            {label as string}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-x-2 border-b border-border bg-chrome px-2 py-1 text-[10px] tracking-wider text-subtle uppercase">
        <span>Layer / purpose</span>
        <span>V</span>
        <span>S</span>
        <span>L</span>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {LAYERS.filter((l) => l.name.toLowerCase().includes(q.toLowerCase())).map((l) => (
          <div
            key={l.name}
            className="grid grid-cols-[1fr_auto_auto_auto] items-center gap-x-2 border-b border-border/40 px-2 py-[3px] text-[11px] hover:bg-raised/60"
          >
            <span className="flex items-center gap-1.5">
              <span
                className="h-[10px] w-[10px] rounded-[1px] border border-border"
                style={{ background: l.color, opacity: 0.85 }}
              />
              <span className="num">{l.name}</span>
              <span className="text-[10px] text-subtle">{l.purpose}</span>
            </span>
            <input
              type="checkbox"
              aria-label={`${l.name} visible`}
              checked={s.visibleLayers.includes(l.name)}
              onChange={() => toggle(l.name)}
              className="h-[11px] w-[11px] accent-[color:var(--color-primary)]"
            />
            <input type="checkbox" aria-label={`${l.name} selectable`} defaultChecked className="h-[11px] w-[11px] accent-[color:var(--color-primary)]" />
            <input type="checkbox" aria-label={`${l.name} locked`} className="h-[11px] w-[11px] accent-[color:var(--color-primary)]" />
          </div>
        ))}
      </div>
    </div>
  );
}

function LibraryList() {
  const s = useStore();
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="panel-hd">Libraries</div>
      {LIBRARIES.map((l) => (
        <button
          key={l.name}
          onClick={() => s.openTab({ id: "library", label: "Library" })}
          className="flex items-center gap-2 border-b border-border/40 px-2 py-[5px] text-left text-[11px] hover:bg-raised/60"
        >
          <Boxes className="h-[12px] w-[12px] text-primary" />
          <span className="num">{l.name}</span>
          <span className="num ml-auto text-[10px] text-subtle">{l.cells}</span>
          <StatusDot status={l.writable ? "PASS" : "NOT RUN"} />
        </button>
      ))}
    </div>
  );
}

function SearchPanel() {
  const s = useStore();
  const [q, setQ] = useState("VOUT");
  const res = SEARCH_INDEX.filter((r) => r.name.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="panel-hd">Search Design</div>
      <div className="flex h-[26px] items-center gap-1.5 border-b border-border px-2">
        <Search className="h-[12px] w-[12px] text-subtle" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="w-full bg-transparent text-[11px] focus:outline-none"
        />
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        {res.map((r, i) => (
          <button
            key={i}
            onClick={() => {
              if (r.ws === "layout") s.openTab({ id: "layout", label: "ota_core : layout" });
              else if (r.ws === "sim") s.openTab({ id: "sim", label: "Simulation Explorer" });
              else if (r.ws === "waveforms") s.openTab({ id: "waveforms", label: "Waveform Analyzer" });
              else if (r.ws === "pv") s.openTab({ id: "pv", label: "Physical Verification" });
              else s.openTab({ id: "schematic", label: "ota_core : schematic" });
            }}
            className="flex w-full items-center gap-2 border-b border-border/40 px-2 py-[5px] text-left text-[11px] hover:bg-raised/60"
          >
            <span className="w-[64px] shrink-0 text-[10px] text-subtle">{r.kind}</span>
            <span className="num text-foreground">{r.name}</span>
            <span className="ml-auto truncate text-[10px] text-subtle">{r.where}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function Simple({ title, rows, icon: Icon }: { title: string; rows: string[]; icon: typeof Square }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="panel-hd">{title}</div>
      {rows.map((r) => (
        <div key={r} className="flex items-center gap-2 border-b border-border/40 px-2 py-[5px] text-[11px] text-muted-foreground">
          <Icon className="h-[12px] w-[12px] text-subtle" />
          <span className="num truncate">{r}</span>
        </div>
      ))}
    </div>
  );
}

export function LeftDock() {
  const s = useStore();
  switch (s.railPanel) {
    case "Layers":
      return <LayerPalette />;
    case "Libraries":
      return <LibraryList />;
    case "Search":
      return <SearchPanel />;
    case "Simulation":
      return (
        <Simple
          title="Results Browser"
          icon={LayersIcon}
          rows={["tb_ota_ac / ac / VOUT", "tb_ota_ac / ac / gain", "tb_ota_ac / ac / phase", "tb_ota_tran / tran / VOUTP", "tb_ota_tran / tran / VOUTN"]}
        />
      );
    case "Verification":
      return (
        <Simple
          title="Verification"
          icon={LayersIcon}
          rows={["DRC — gpdk65.drc", "LVS — gpdk65.lvs", "ERC — connectivity", "PEX — RC + coupling"]}
        />
      );
    case "Jobs":
      return <Simple title="Job Queue" icon={LayersIcon} rows={s.jobs.map((j) => `${j.id}  ${j.status}`)} />;
    case "Files":
      return (
        <Simple
          title="Files"
          icon={FileStack}
          rows={["aurora_65.lib", "gpdk65.drc", "gpdk65.lvs", "tb_ota_ac.scs", "ota_core.gds", "ota_core.spf"]}
        />
      );
    case "Bookmarks":
      return <Simple title="Bookmarks" icon={Bookmark} rows={["ota_core input pair", "VOUTP routing", "SS corner failure", "DRC 001"]} />;
    default:
      return <DesignBrowser />;
  }
}
