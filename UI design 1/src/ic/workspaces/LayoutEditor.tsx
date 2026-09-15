import { useRef, useState } from "react";
import { DRC_VIOLATIONS, LAYERS, LAYOUT_SHAPES, RATLINES } from "../data";
import { useStore } from "../store";
import { IconBtn, Sep } from "../ui";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Boxes,
  ChevronDown,
  Combine,
  Copy,
  Crosshair,
  Grid2x2,
  Hexagon,
  Layers,
  Move,
  MousePointer2,
  PenLine,
  Route,
  Ruler,
  Scissors,
  Shield,
  Square,
  StretchHorizontal,
  Circle as CircleIcon,
  AlignVerticalJustifyCenter,
} from "lucide-react";
import { cn } from "@/lib/utils";

const TOOLS = [
  ["Select", MousePointer2],
  ["Rectangle", Square],
  ["Polygon", Hexagon],
  ["Path", PenLine],
  ["Via", Grid2x2],
  ["Create Pin", CircleIcon],
  ["Instance", Boxes],
  ["Array", Combine],
  ["Move", Move],
  ["Stretch", StretchHorizontal],
  ["Chop", Scissors],
  ["Merge", Combine],
  ["Align", AlignVerticalJustifyCenter],
  ["Ruler", Ruler],
  ["Measure", Crosshair],
  ["Route", Route],
  ["Clone", Copy],
  ["Guard Ring", Shield],
] as const;

const OVERLAYS = ["None", "DRC", "Connectivity", "Current Density", "IR Drop", "Device Matching", "Parasitics", "Metal Density"];

export function LayoutEditor({ dense = false }: { dense?: boolean }) {
  const s = useStore();
  const svgRef = useRef<SVGSVGElement>(null);
  const [cursor, setCursor] = useState<[number, number]>([128.44, 82.175]);
  const [ruler, setRuler] = useState<[number, number][]>([]);
  const [rects, setRects] = useState<{ x: number; y: number; w: number; h: number }[]>([]);
  const [drawStart, setDrawStart] = useState<[number, number] | null>(null);
  const selDevice = s.selection?.kind === "layoutDevice" ? s.selection.id : null;
  const selSchem = s.selection?.kind === "instance" ? s.selection.id : null;
  const selNet = s.selection?.kind === "net" ? s.selection.id : null;
  const drc = DRC_VIOLATIONS.find((v) => v.id === s.activeDrc);

  const toSvg = (e: React.MouseEvent): [number, number] => {
    const r = svgRef.current!.getBoundingClientRect();
    const k = 760 / r.width;
    return [((e.clientX - r.left) * k) / s.zoom, ((e.clientY - r.top) * k) / s.zoom];
  };

  const onClick = (e: React.MouseEvent) => {
    const p = toSvg(e);
    if (s.tool === "Measure" || s.tool === "Ruler") {
      const next = [...ruler, p].slice(-2) as [number, number][];
      setRuler(next);
      s.setCommand({ name: "MEASURE", hint: next.length < 2 ? "Click second point" : "Esc to cancel" });
    } else if (s.tool === "Rectangle") {
      if (!drawStart) {
        setDrawStart(p);
        s.setCommand({ name: "RECTANGLE", hint: "Click opposite corner · Esc to cancel" });
      } else {
        setRects((r) => [
          ...r,
          { x: Math.min(drawStart[0], p[0]), y: Math.min(drawStart[1], p[1]), w: Math.abs(p[0] - drawStart[0]), h: Math.abs(p[1] - drawStart[1]) },
        ]);
        setDrawStart(null);
        s.setCommand(null);
        s.log("Created M1 rectangle");
      }
    } else {
      s.setSelection(null);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col bg-background">
      <div className="flex h-[28px] shrink-0 items-center gap-1 border-b border-border bg-chrome px-2 text-[11px]">
        <span className="num text-muted-foreground">Grid 0.005 µm</span>
        <Sep />
        <button
          onClick={() => s.setRatlines(!s.ratlines)}
          className={cn("rounded-[3px] border border-border px-2 py-[2px] text-[11px]", s.ratlines ? "bg-raised text-primary" : "text-subtle")}
        >
          Connectivity
        </button>
        <DropdownMenu>
          <DropdownMenuTrigger className="flex items-center gap-1 rounded-[3px] border border-border px-2 py-[2px] text-[11px] text-muted-foreground">
            Overlays: <span className="text-foreground">{s.overlay}</span>
            <ChevronDown className="h-3 w-3" />
          </DropdownMenuTrigger>
          <DropdownMenuContent className="text-[11px]">
            {OVERLAYS.map((o) => (
              <DropdownMenuItem key={o} className="text-[11px]" onSelect={() => s.setOverlay(o)}>
                {o}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <Sep />
        <IconBtn label="Layer Palette" onClick={() => s.setRailPanel("Layers")}>
          <Layers className="h-[13px] w-[13px]" />
        </IconBtn>
        <span className="num ml-auto text-[10px] text-subtle">
          148.2 µm × 93.6 µm · 0.0139 mm²{s.ratlines && " · Unrouted connections: 3"}
        </span>
      </div>

      <div className="flex min-h-0 flex-1">
        <div className="flex w-[30px] shrink-0 flex-col items-center gap-0.5 overflow-y-auto border-r border-border bg-chrome py-1">
          {TOOLS.map(([name, Icon]) => (
            <IconBtn
              key={name}
              label={name}
              active={s.tool === name}
              onClick={() => {
                s.setTool(name);
                s.setCommand(name === "Select" ? null : { name: name.toUpperCase(), hint: "Click start point · Esc to cancel" });
              }}
            >
              <Icon className="h-[14px] w-[14px]" />
            </IconBtn>
          ))}
        </div>

        <ContextMenu>
          <ContextMenuTrigger asChild>
            <div className="relative min-h-0 min-w-0 flex-1 overflow-hidden bg-canvas">
              <svg
                ref={svgRef}
                role="application"
                aria-label="Layout canvas"
                viewBox="0 0 760 470"
                className="h-full w-full"
                onClick={onClick}
                onMouseMove={(e) => {
                  const p = toSvg(e);
                  setCursor([p[0] * 0.195, p[1] * 0.195]);
                }}
                onWheel={(e) => s.setZoom(Math.max(0.3, Math.min(6, s.zoom * (e.deltaY > 0 ? 0.94 : 1.06))))}
              >
                <defs>
                  <pattern id="lgrid" width="20" height="20" patternUnits="userSpaceOnUse">
                    <path d="M 20 0 L 0 0 0 20" fill="none" stroke="var(--color-grid)" strokeWidth="0.5" />
                  </pattern>
                  <linearGradient id="heat" x1="0" y1="0" x2="1" y2="1">
                    <stop offset="0%" stopColor="#45c486" stopOpacity="0.15" />
                    <stop offset="55%" stopColor="#e8b45a" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="#ef6464" stopOpacity="0.5" />
                  </linearGradient>
                </defs>
                <rect width="760" height="470" fill="url(#lgrid)" />
                <g transform={`scale(${s.zoom})`}>
                  {LAYOUT_SHAPES.map((sh, i) => {
                    const layer = LAYERS.find((l) => l.name === sh.layer);
                    if (!layer || !s.visibleLayers.includes(sh.layer)) return null;
                    const hot =
                      (sh.device && (sh.device === selDevice || sh.device === selSchem)) ||
                      (sh.net && sh.net === selNet);
                    return (
                      <rect
                        key={i}
                        x={sh.x}
                        y={sh.y}
                        width={sh.w}
                        height={sh.h}
                        fill={layer.color}
                        fillOpacity={hot ? Math.min(1, layer.fill + 0.35) : layer.fill}
                        stroke={hot ? "var(--color-primary)" : layer.color}
                        strokeWidth={hot ? 1.4 : 0.4}
                        className={sh.device || sh.net ? "cursor-pointer" : undefined}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (sh.device && sh.device !== "DUMMY") s.setSelection({ kind: "layoutDevice", id: sh.device });
                          else if (sh.net) s.setSelection({ kind: "net", id: sh.net });
                        }}
                      />
                    );
                  })}
                  {LAYOUT_SHAPES.filter((sh) => sh.label && s.visibleLayers.includes(sh.layer)).map((sh, i) => (
                    <text key={i} x={sh.x + 3} y={sh.y + 9} fontSize={7} className="num" fill="var(--color-foreground)">
                      {sh.label}
                    </text>
                  ))}
                  {rects.map((r, i) => (
                    <rect key={i} x={r.x} y={r.y} width={r.w} height={r.h} fill="#4b93ff" fillOpacity={0.5} stroke="#4b93ff" />
                  ))}
                  {s.ratlines &&
                    RATLINES.map((r, i) => (
                      <g key={i}>
                        <line x1={r.x1} y1={r.y1} x2={r.x2} y2={r.y2} stroke="var(--color-warning)" strokeWidth={0.8} strokeDasharray="3 3" opacity={0.8} />
                        <circle cx={r.x1} cy={r.y1} r={2} fill="var(--color-warning)" />
                        <circle cx={r.x2} cy={r.y2} r={2} fill="var(--color-warning)" />
                      </g>
                    ))}
                  {s.overlay === "Current Density" && <rect x={0} y={0} width={740} height={440} fill="url(#heat)" />}
                  {s.overlay === "IR Drop" && <rect x={0} y={0} width={740} height={440} fill="url(#heat)" opacity={0.6} />}
                  {s.overlay === "DRC" &&
                    DRC_VIOLATIONS.map((v) => (
                      <rect key={v.id} x={v.x * 3.1} y={v.y * 3.6} width={16} height={12} fill="none" stroke="var(--color-critical)" strokeWidth={1.4} />
                    ))}
                  {drc && (
                    <g>
                      <rect x={drc.x * 3.1 - 8} y={drc.y * 3.6 - 8} width={30} height={26} fill="var(--color-critical)" fillOpacity={0.15} stroke="var(--color-critical)" strokeWidth={1.6} />
                      <text x={drc.x * 3.1 + 26} y={drc.y * 3.6} fontSize={8} className="num" fill="var(--color-critical)">
                        {drc.rule}
                      </text>
                    </g>
                  )}
                  {ruler.length === 2 && (
                    <g stroke="var(--color-cyan)">
                      <line x1={ruler[0][0]} y1={ruler[0][1]} x2={ruler[1][0]} y2={ruler[1][1]} />
                      <text
                        x={(ruler[0][0] + ruler[1][0]) / 2}
                        y={(ruler[0][1] + ruler[1][1]) / 2 - 6}
                        fontSize={8}
                        className="num"
                        fill="var(--color-cyan)"
                        stroke="none"
                      >
                        ΔX={(Math.abs(ruler[1][0] - ruler[0][0]) * 0.195).toFixed(3)} ΔY=
                        {(Math.abs(ruler[1][1] - ruler[0][1]) * 0.195).toFixed(3)} D=
                        {(Math.hypot(ruler[1][0] - ruler[0][0], ruler[1][1] - ruler[0][1]) * 0.195).toFixed(3)} µm
                      </text>
                    </g>
                  )}
                </g>
              </svg>

              {s.overlay === "Current Density" && (
                <div className="num absolute top-2 right-2 rounded-[3px] border border-border bg-chrome/95 px-2 py-1 text-[10px] text-subtle">
                  0 <span className="mx-1 tracking-[-1px] text-foreground">▁▂▃▄▅▆▇█</span> 4.2 mA/µm
                </div>
              )}
              {!dense && (
                <div className="absolute right-2 bottom-2 h-[86px] w-[130px] border border-border bg-chrome/90 p-1">
                  <div className="num mb-0.5 text-[9px] text-subtle">Minimap</div>
                  <svg viewBox="0 0 760 470" className="h-[62px] w-full">
                    <rect width="760" height="470" fill="var(--color-canvas)" />
                    {LAYOUT_SHAPES.filter((_, i) => i % 3 === 0).map((sh, i) => (
                      <rect key={i} x={sh.x} y={sh.y} width={sh.w} height={sh.h} fill={LAYERS.find((l) => l.name === sh.layer)?.color} opacity={0.6} />
                    ))}
                    <rect x={20} y={20} width={700 / s.zoom} height={420 / s.zoom} fill="none" stroke="var(--color-primary)" strokeWidth={6} />
                  </svg>
                </div>
              )}
              <div className="num pointer-events-none absolute top-1.5 left-2 text-[10px] text-subtle">
                ota_core : layout — gpdk65
              </div>
            </div>
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
            <ContextMenuItem className="text-[11px]">Create Constraint</ContextMenuItem>
          </ContextMenuContent>
        </ContextMenu>
      </div>

      <div className="num flex h-[22px] shrink-0 items-center gap-4 border-t border-border bg-chrome px-2 text-[10px] text-muted-foreground">
        <span>X: {cursor[0].toFixed(3)} µm</span>
        <span>Y: {cursor[1].toFixed(3)} µm</span>
        <span>dx: 0.000</span>
        <span>dy: 0.000</span>
        <span>Grid 0.005 µm</span>
        <span>Snap orthogonal</span>
        <span>Selection {s.selection ? 1 : 0}</span>
        <span className="ml-auto">Scale 4.20 µm/div</span>
      </div>
    </div>
  );
}
