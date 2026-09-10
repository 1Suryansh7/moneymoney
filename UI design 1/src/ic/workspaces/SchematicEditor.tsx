import { useRef, useState } from "react";
import { type Instance } from "../data";
import { validate } from "../api";
import { useStore } from "../store";
import { IconBtn, Sep, Tip } from "../ui";
import { cn } from "@/lib/utils";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import {
  ArrowDownToLine,
  ArrowUpToLine,
  Cable,
  Check,
  Circle,
  Copy,
  Crosshair,
  FlipHorizontal2,
  Grid3x3,
  Move,
  MousePointer2,
  Redo2,
  RotateCw,
  Ruler,
  Search,
  Square,
  Tag,
  Trash2,
  Undo2,
  Maximize2,
} from "lucide-react";

const TOOLS = [
  ["Select", MousePointer2, "Esc"],
  ["Wire", Cable, "W"],
  ["Instance", Square, "I"],
  ["Pin", Circle, "P"],
  ["Label", Tag, "L"],
  ["Move", Move, "M"],
  ["Copy", Copy, "C"],
  ["Rotate", RotateCw, "R"],
  ["Mirror", FlipHorizontal2, "Shift+M"],
  ["Stretch", ArrowUpToLine, "S"],
  ["Delete", Trash2, "Del"],
  ["Zoom", Search, "Z"],
  ["Measure", Ruler, "K"],
  ["Probe", Crosshair, "X"],
] as const;

function MosSymbol({ inst, selected, onSelect }: { inst: Instance; selected: boolean; onSelect: () => void }) {
  const s = useStore();
  const p = inst.type === "pmos";
  const stroke = selected ? "var(--color-primary)" : "var(--color-foreground)";
  const annotate = s.annotate;
  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <g
          transform={`translate(${inst.x},${inst.y})`}
          onClick={(e) => {
            e.stopPropagation();
            onSelect();
          }}
          className="cursor-pointer"
        >
          {selected && <rect x={-24} y={-42} width={78} height={86} fill="var(--color-primary)" opacity={0.08} stroke="var(--color-primary)" strokeDasharray="3 2" />}
          {/* gate */}
          <line x1={-14} y1={-20} x2={-14} y2={20} stroke={stroke} strokeWidth={1.4} />
          <line x1={-30} y1={0} x2={-14} y2={0} stroke={stroke} strokeWidth={1.2} />
          {/* channel */}
          <line x1={-8} y1={-22} x2={-8} y2={-8} stroke={stroke} strokeWidth={1.4} />
          <line x1={-8} y1={-6} x2={-8} y2={6} stroke={stroke} strokeWidth={1.4} />
          <line x1={-8} y1={8} x2={-8} y2={22} stroke={stroke} strokeWidth={1.4} />
          {/* drain / source */}
          <path d={`M -8 -16 H 14 V -40`} fill="none" stroke={stroke} strokeWidth={1.2} />
          <path d={`M -8 16 H 14 V 40`} fill="none" stroke={stroke} strokeWidth={1.2} />
          <path d={`M -8 0 H 14`} fill="none" stroke={stroke} strokeWidth={1.2} />
          {/* bulk arrow */}
          {p ? (
            <path d="M 4 4 L 12 0 L 4 -4 Z" fill={stroke} transform="translate(-2,0)" />
          ) : (
            <path d="M 12 -4 L 4 0 L 12 4 Z" fill={stroke} transform="translate(-2,0)" />
          )}
          {selected &&
            [
              [-24, -42],
              [54, -42],
              [-24, 44],
              [54, 44],
            ].map(([hx, hy], i) => (
              <rect key={i} x={hx - 2} y={hy - 2} width={4} height={4} fill="var(--color-primary)" />
            ))}
          <text x={20} y={-24} fontSize={11} className="num" fill={selected ? "var(--color-primary)" : "var(--color-cyan)"}>
            {inst.id}
          </text>
          <text x={20} y={-12} fontSize={9} className="num" fill="var(--color-subtle)">
            W={String(inst.params.W)} L={String(inst.params.L)}
          </text>
          {(inst.params.nf !== undefined || inst.params.m !== undefined) && (
            <text x={20} y={-2} fontSize={9} className="num" fill="var(--color-subtle)">
              nf={String(inst.params.nf ?? "—")} m={String(inst.params.m ?? "—")}
            </text>
          )}
          {annotate === "Operating Region" && (
            <text x={20} y={22} fontSize={9} className="num" fill="var(--color-success)">
              sat
            </text>
          )}
          {annotate === "Device Currents" && (
            <text x={20} y={22} fontSize={9} className="num" fill="var(--color-warning)">
              {inst.op?.IDS}
            </text>
          )}
          {annotate === "gm/gds" && (
            <text x={20} y={22} fontSize={9} className="num" fill="var(--color-purple)">
              {inst.op?.gm} / {inst.op?.gds}
            </text>
          )}
          {inst.warn && (
            <g transform="translate(-30,-30)">
              <path d="M 0 -6 L 6 0 L 0 6 L -6 0 Z" fill="var(--color-warning)" opacity={0.9} />
              <title>{inst.warn}</title>
            </g>
          )}
        </g>
      </ContextMenuTrigger>
      <ContextMenuContent className="min-w-[190px] text-[11px]">
        {["Properties", "Move", "Copy", "Delete", "Rotate", "Mirror"].map((i) => (
          <ContextMenuItem key={i} className="text-[11px]">
            {i}
          </ContextMenuItem>
        ))}
        <ContextMenuSeparator />
        {["Connectivity", "Trace Net", "Probe", "Highlight"].map((i) => (
          <ContextMenuItem key={i} className="text-[11px]">
            {i}
          </ContextMenuItem>
        ))}
        <ContextMenuSeparator />
        <ContextMenuItem className="text-[11px]">Open Master</ContextMenuItem>
        <ContextMenuItem className="text-[11px]">Descend</ContextMenuItem>
        <ContextMenuItem className="text-[11px]">Show In Browser</ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuItem className="text-[11px]">Create Constraint</ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}

function OtherSymbol({ inst, selected, onSelect, onDescend }: { inst: Instance; selected: boolean; onSelect: () => void; onDescend: () => void }) {
  const stroke = selected ? "var(--color-primary)" : "var(--color-foreground)";
  return (
    <g
      transform={`translate(${inst.x},${inst.y})`}
      className="cursor-pointer"
      onClick={(e) => {
        e.stopPropagation();
        onSelect();
      }}
      onDoubleClick={onDescend}
    >
      {inst.type === "block" && (
        <>
          <rect x={-34} y={-30} width={68} height={60} fill="var(--color-raised)" stroke={stroke} strokeWidth={1.2} />
          <text x={0} y={-2} fontSize={10} textAnchor="middle" className="num" fill={stroke}>
            {inst.id}
          </text>
          <text x={0} y={12} fontSize={9} textAnchor="middle" className="num" fill="var(--color-subtle)">
            {inst.cell}
          </text>
        </>
      )}
      {inst.type === "cap" && (
        <>
          <line x1={0} y1={-24} x2={0} y2={-6} stroke={stroke} />
          <line x1={-12} y1={-6} x2={12} y2={-6} stroke={stroke} strokeWidth={1.6} />
          <line x1={-12} y1={2} x2={12} y2={2} stroke={stroke} strokeWidth={1.6} />
          <line x1={0} y1={2} x2={0} y2={24} stroke={stroke} />
          <text x={16} y={-6} fontSize={9} className="num" fill="var(--color-cyan)">
            {inst.id}
          </text>
          <text x={16} y={5} fontSize={9} className="num" fill="var(--color-subtle)">
            {String(inst.params.c)}
          </text>
        </>
      )}
      {inst.type === "res" && (
        <>
          <line x1={-24} y1={0} x2={-12} y2={0} stroke={stroke} />
          <rect x={-12} y={-6} width={24} height={12} fill="none" stroke={stroke} strokeWidth={1.3} />
          <line x1={12} y1={0} x2={24} y2={0} stroke={stroke} />
          <text x={-6} y={-10} fontSize={9} className="num" fill="var(--color-cyan)">
            {inst.id}
          </text>
          <text x={18} y={-10} fontSize={9} className="num" fill="var(--color-subtle)">
            {String(inst.params.r)}
          </text>
        </>
      )}
      {inst.type === "isrc" && (
        <>
          <circle r={13} fill="none" stroke={stroke} strokeWidth={1.3} />
          <line x1={0} y1={-6} x2={0} y2={6} stroke={stroke} />
          <path d="M -4 0 L 0 -7 L 4 0 Z" fill={stroke} />
          <text x={16} y={-4} fontSize={9} className="num" fill="var(--color-cyan)">
            {inst.id}
          </text>
          <text x={16} y={7} fontSize={9} className="num" fill="var(--color-subtle)">
            {String(inst.params.dc)}
          </text>
        </>
      )}
      {selected && <rect x={-38} y={-34} width={76} height={68} fill="var(--color-primary)" opacity={0.08} stroke="var(--color-primary)" strokeDasharray="3 2" />}
    </g>
  );
}

/** Display-only engineering notation for SI floats (backend stays canonical). */
function fmtEng(v: number, unit: string): string {
  const steps: [number, string][] = [
    [1e6, "M"],
    [1e3, "k"],
    [1, ""],
    [1e-3, "m"],
    [1e-6, "u"],
    [1e-9, "n"],
    [1e-12, "p"],
    [1e-15, "f"],
  ];
  for (const [f, p] of steps) {
    if (Math.abs(v) >= f) return `${parseFloat((v / f).toPrecision(3)).toString()}${p}${unit}`;
  }
  return `${v}${unit}`;
}

function fmtParam(name: string, v: number): string {
  if (name === "W" || name === "L") return fmtEng(v, "m");
  if (name === "c" || name === "C") return fmtEng(v, "F");
  if (name === "r" || name === "R") return fmtEng(v, "Ω");
  return String(v);
}

export function SchematicEditor({ dense = false }: { dense?: boolean }) {
  const s = useStore();
  const svgRef = useRef<SVGSVGElement>(null);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [wirePts, setWirePts] = useState<[number, number][]>([]);
  const [cursor, setCursor] = useState<[number, number]>([0, 0]);
  const [newWires, setNewWires] = useState<[number, number][][]>([]);
  const [flash, setFlash] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const selInst = s.selection?.kind === "instance" ? s.selection.id : null;
  const selNet = s.selection?.kind === "net" ? s.selection.id : null;
  const schem = s.activeSchematic;

  const liveInstances: Instance[] = (schem?.instances ?? [])
    .slice()
    .sort((a, b) => (a.instance_name < b.instance_name ? -1 : 1))
    .map((inst, i) => {
      const sym = inst.symbol_name;
      const type: Instance["type"] = sym.startsWith("nfet")
        ? "nmos"
        : sym.startsWith("pfet")
          ? "pmos"
          : sym.startsWith("cap")
            ? "cap"
            : sym.startsWith("res")
              ? "res"
              : "block";
      const params: Record<string, string | number> = {};
      for (const [k, v] of Object.entries(inst.parameters)) {
        params[k] = fmtParam(k, v);
      }
      const conn: Record<string, string> = {};
      for (const p of schem?.ports ?? []) {
        if (p.instance_name === inst.instance_name && p.net_name) conn[p.port_name] = p.net_name;
      }
      return {
        id: inst.instance_name,
        type,
        x: 200 + i * 260,
        y: 300,
        cell: sym,
        params,
        conn,
      };
    });

  const netMembers = (net: string): string[] =>
    (schem?.ports ?? [])
      .filter((p) => p.net_name === net)
      .map((p) => (p.instance_name ? `${p.instance_name}.${p.port_name}` : `pin.${p.port_name}`));

  const livePins = (schem?.ports ?? []).filter((p) => p.instance_name === null);

  const runCheck = () => {
    const id = s.activeCellId;
    if (!id || checking) return;
    setChecking(true);
    void (async () => {
      try {
        const r = await validate(id);
        s.log(
          r.valid ? "Check: 0 violations" : `Check: ${r.violations.length} violations — ${r.violations[0] ?? ""}`,
          r.valid ? undefined : "warn",
        );
      } catch (err) {
        s.log(`Check failed: ${err instanceof Error ? err.message : String(err)}`, "err");
      } finally {
        setChecking(false);
      }
    })();
  };

  const toSvg = (e: React.MouseEvent) => {
    const r = svgRef.current!.getBoundingClientRect();
    const scale = 1000 / r.width;
    return [
      Math.round(((e.clientX - r.left) * scale) / s.zoom - pan.x),
      Math.round(((e.clientY - r.top) * scale) / s.zoom - pan.y),
    ] as [number, number];
  };

  const onCanvasClick = (e: React.MouseEvent) => {
    const p = toSvg(e);
    if (s.tool === "Wire") {
      const next = [...wirePts, p];
      setWirePts(next);
      s.setCommand({ name: "WIRE", hint: "Click next point · Double-click to finish · Esc to cancel" });
    } else {
      s.setSelection(null);
    }
  };

  const finishWire = () => {
    if (wirePts.length > 1) {
      setNewWires((w) => [...w, wirePts]);
      s.log("Net created");
      s.setStatusMsg("Net created");
      s.setDirty(true);
    }
    setWirePts([]);
    s.setCommand(null);
    s.setTool("Select");
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-background">
      {/* horizontal toolbar */}
      <div className="flex h-[28px] shrink-0 items-center gap-1 border-b border-border bg-chrome px-2 text-[11px]">
        <select
          aria-label="Active cell"
          value={s.activeCellId ?? ""}
          onChange={(e) => void s.selectCell(e.target.value || null)}
          className="num h-[22px] max-w-[220px] rounded-[3px] border border-border bg-background px-1 text-[11px]"
        >
          <option value="">— pick a cell —</option>
          {s.cells.map((c) => (
            <option key={c.cell_id} value={c.cell_id}>
              {c.cell_name}
            </option>
          ))}
        </select>
        <Sep />
        <span className="num text-muted-foreground">Snap: 0.0625</span>
        <Sep />
        <IconBtn label="Grid"><Grid3x3 className="h-[13px] w-[13px]" /></IconBtn>
        <IconBtn label="Orthogonal routing" active><Cable className="h-[13px] w-[13px]" /></IconBtn>
        <IconBtn label="Connect"><Crosshair className="h-[13px] w-[13px]" /></IconBtn>
        <IconBtn label="Check" onClick={runCheck}>
          <Check className="h-[13px] w-[13px]" />
        </IconBtn>
        <Sep />
        <IconBtn label="Hierarchy Up" onClick={() => s.setHierPath(["aurora_65", "ota_core"])}>
          <ArrowUpToLine className="h-[13px] w-[13px]" />
        </IconBtn>
        <IconBtn label="Hierarchy Down" onClick={() => s.setHierPath([...s.hierPath, "XBIAS", "bias_gen"])}>
          <ArrowDownToLine className="h-[13px] w-[13px]" />
        </IconBtn>
        <Sep />
        <IconBtn label="Undo"><Undo2 className="h-[13px] w-[13px]" /></IconBtn>
        <IconBtn label="Redo"><Redo2 className="h-[13px] w-[13px]" /></IconBtn>
        <IconBtn label="Zoom Fit" keys="F" onClick={() => { s.setZoom(1); setPan({ x: 0, y: 0 }); }}>
          <Maximize2 className="h-[13px] w-[13px]" />
        </IconBtn>
        <div className="num ml-auto flex items-center gap-2 text-[10px] text-subtle">
          <span>{s.hierPath.join(" > ")}</span>
          <span className="text-foreground">{liveInstances.length} instances</span>
          <span className="text-foreground">{schem?.nets.length ?? 0} nets</span>
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        {/* vertical tool strip */}
        <div className="flex w-[30px] shrink-0 flex-col items-center gap-0.5 border-r border-border bg-chrome py-1">
          {TOOLS.map(([name, Icon, keys]) => (
            <IconBtn
              key={name}
              label={name}
              keys={keys}
              active={s.tool === name}
              onClick={() => {
                s.setTool(name);
                s.setCommand(
                  name === "Select"
                    ? null
                    : { name: name.toUpperCase(), hint: name === "Wire" ? "Click start point · Esc to cancel" : "Esc to cancel" }
                );
              }}
            >
              <Icon className="h-[14px] w-[14px]" />
            </IconBtn>
          ))}
        </div>

        <ContextMenu>
          <ContextMenuTrigger asChild>
            <div className="relative min-h-0 min-w-0 flex-1 overflow-hidden">
              <svg
                ref={svgRef}
                role="application"
                aria-label="Schematic canvas"
                viewBox="0 0 1000 600"
                className="h-full w-full grid-canvas"
                onClick={onCanvasClick}
                onDoubleClick={() => s.tool === "Wire" && finishWire()}
                onMouseMove={(e) => setCursor(toSvg(e))}
                onWheel={(e) => s.setZoom(Math.max(0.3, Math.min(5, s.zoom * (e.deltaY > 0 ? 0.94 : 1.06))))}
              >
                <g transform={`scale(${s.zoom}) translate(${pan.x},${pan.y})`}>
                  {/* nets: connectivity list (auto-layout canvas carries no routed wires) */}
                  {(schem?.nets ?? []).slice().sort().map((net, i) => {
                    const members = netMembers(net);
                    const hot =
                      selNet === net || (selInst !== null && members.some((m) => m.startsWith(`${selInst}.`)));
                    return (
                      <g key={net}>
                        <text
                          x={40}
                          y={478 + i * 16}
                          fontSize={9}
                          className="num cursor-pointer"
                          fill={hot ? "var(--color-cyan)" : "var(--color-subtle)"}
                          onClick={(e) => {
                            e.stopPropagation();
                            s.setSelection({ kind: "net", id: net });
                          }}
                        >
                          {net}: {members.join(", ")}
                        </text>
                      </g>
                    );
                  })}

                  {/* cell-level ports (direction unknown server-side: neutral markers) */}
                  {livePins.map((p, i) => (
                    <g key={p.port_name} transform={`translate(80,${140 + i * 44})`}>
                      <circle r={4} fill="none" stroke="var(--color-success)" strokeWidth={1.2} />
                      <text x={10} y={3.5} fontSize={9} className="num" fill="var(--color-success)">
                        {p.port_name}
                      </text>
                    </g>
                  ))}

                  {/* instances */}
                  {liveInstances.map((inst) =>
                    inst.type === "nmos" || inst.type === "pmos" ? (
                      <MosSymbol
                        key={inst.id}
                        inst={inst}
                        selected={selInst === inst.id || flash === inst.id}
                        onSelect={() => s.setSelection({ kind: "instance", id: inst.id })}
                      />
                    ) : (
                      <OtherSymbol
                        key={inst.id}
                        inst={inst}
                        selected={selInst === inst.id}
                        onSelect={() => s.setSelection({ kind: "instance", id: inst.id })}
                        onDescend={() => {
                          if (inst.type === "block") {
                            s.setHierPath(["aurora_65", "ota_core", inst.id, inst.cell]);
                            s.log(`Descend into ${inst.id} (${inst.cell}/schematic)`);
                            setFlash(inst.id);
                            window.setTimeout(() => setFlash(null), 800);
                          }
                        }}
                      />
                    )
                  )}

                  {/* user wires */}
                  {newWires.map((w, i) => (
                    <polyline key={i} points={w.map((p) => p.join(",")).join(" ")} fill="none" stroke="var(--color-cyan)" strokeWidth={1.4} />
                  ))}
                  {wirePts.length > 0 && (
                    <polyline
                      points={[...wirePts, [cursor[0], wirePts[wirePts.length - 1][1]], cursor].map((p) => p.join(",")).join(" ")}
                      fill="none"
                      stroke="var(--color-primary)"
                      strokeDasharray="4 3"
                      strokeWidth={1.3}
                    />
                  )}
                </g>
              </svg>

              {/* canvas overlays */}
              <div className="num pointer-events-none absolute top-1.5 left-2 text-[10px] text-subtle">
                {schem ? `${schem.cell_name} : schematic — sky130 — auto-layout` : "no cell selected"}
              </div>
              {!schem && (
                <div className="num absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-[4px] border border-border bg-panel px-4 py-3 text-center text-[11px] text-subtle">
                  No live cell on the canvas.
                  <br />
                  File → New Cell View to create one, or pick a cell above.
                </div>
              )}
              {s.command && (
                <div className="num absolute bottom-2 left-2 rounded-[3px] border border-border bg-chrome/95 px-2 py-1 text-[10px]">
                  <span className="text-primary">{s.command.name}</span>{" "}
                  <span className="text-subtle">{s.command.hint}</span>
                </div>
              )}
              {!dense && (
                <div className="num absolute right-2 bottom-2 flex gap-3 rounded-[3px] border border-border bg-chrome/95 px-2 py-1 text-[10px] text-subtle">
                  <span>x {cursor[0]}</span>
                  <span>y {cursor[1]}</span>
                  <span>zoom {(s.zoom * 100).toFixed(0)}%</span>
                </div>
              )}
            </div>
          </ContextMenuTrigger>
          <ContextMenuContent className="min-w-[200px] text-[11px]">
            {["Highlight Net", "Trace Connectivity", "Plot", "Add to Outputs", "Annotate DC Voltage", "Calculate Parasitics"].map(
              (i) => (
                <ContextMenuItem key={i} className="text-[11px]" onSelect={() => s.log(i)}>
                  {i}
                </ContextMenuItem>
              )
            )}
            <ContextMenuSeparator />
            <ContextMenuItem className="text-[11px]" onSelect={() => s.setZoom(1)}>
              Zoom Fit
            </ContextMenuItem>
          </ContextMenuContent>
        </ContextMenu>
      </div>
    </div>
  );
}

export function SchematicToolTip() {
  return <Tip label="Schematic"><span className={cn("hidden")} /></Tip>;
}
