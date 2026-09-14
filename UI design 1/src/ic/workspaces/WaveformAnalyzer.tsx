import { useEffect, useState } from "react";
import { useStore } from "../store";
import { IconBtn, SectionTitle, Sep } from "../ui";
import { cn } from "@/lib/utils";
import {
  Calculator,
  Crosshair,
  Download,
  Eye,
  EyeOff,
  Layers,
  Maximize2,
  Minus,
  Move,
  Plus,
  Rows3,
  ScanLine,
  Trash2,
} from "lucide-react";

export type Plot = { title: string; unit: string; logX: boolean; series: { name: string; color: string; pts: Pt[] }[]; yMin: number; yMax: number; xMin: number; xMax: number };

type Pt = { x: number; y: number };

const PALETTE = ["#4b93ff", "#ef6464", "#58d6e8", "#b68cff", "#7dd87d", "#e8c458"];

function toPts(x: number[], y: number[]): Pt[] {
  return x.map((v, i) => ({ x: v, y: y[i] }));
}

function nearestIdx(xs: number[], v: number): number {
  let best = 0;
  for (let i = 1; i < xs.length; i++) {
    if (Math.abs(xs[i] - v) < Math.abs(xs[best] - v)) best = i;
  }
  return best;
}

function extent(pts: Pt[], logX: boolean): { xMin: number; xMax: number; yMin: number; yMax: number } {
  if (pts.length === 0) return { xMin: logX ? 1 : 0, xMax: logX ? 10 : 1, yMin: 0, yMax: 1 };
  let xMin = Infinity;
  let xMax = -Infinity;
  let yMin = Infinity;
  let yMax = -Infinity;
  for (const p of pts) {
    if (p.x < xMin) xMin = p.x;
    if (p.x > xMax) xMax = p.x;
    if (p.y < yMin) yMin = p.y;
    if (p.y > yMax) yMax = p.y;
  }
  const yPad = yMax === yMin ? Math.abs(yMax) * 0.1 + 1e-12 : (yMax - yMin) * 0.1;
  return {
    xMin: logX && xMin <= 0 ? xMax / 1000 : xMin,
    xMax,
    yMin: yMin - yPad,
    yMax: yMax + yPad,
  };
}

function fmtHz(f: number) {
  if (f >= 1e9) return `${(f / 1e9).toFixed(f >= 1e10 ? 0 : 1)} GHz`;
  if (f >= 1e6) return `${(f / 1e6).toFixed(0)} MHz`;
  if (f >= 1e3) return `${(f / 1e3).toFixed(0)} kHz`;
  return `${f.toFixed(0)} Hz`;
}

export function PlotPane({ plot, cursorX, onCursor }: { plot: Plot; cursorX: number; onCursor: (v: number) => void }) {
  const W = 1000;
  const H = 190;
  const L = 54;
  const B = 22;
  const sx = (x: number) =>
    plot.logX
      ? L + ((Math.log10(x) - Math.log10(plot.xMin)) / (Math.log10(plot.xMax) - Math.log10(plot.xMin))) * (W - L - 12)
      : L + ((x - plot.xMin) / (plot.xMax - plot.xMin)) * (W - L - 12);
  const sy = (y: number) => 8 + (1 - (y - plot.yMin) / (plot.yMax - plot.yMin)) * (H - B - 8);
  const ticksY = Array.from({ length: 5 }, (_, i) => plot.yMin + ((plot.yMax - plot.yMin) * i) / 4);
  const ticksX = plot.logX
    ? Array.from({ length: 6 }, (_, i) => Math.pow(10, Math.log10(plot.xMin) + ((Math.log10(plot.xMax) - Math.log10(plot.xMin)) * i) / 5))
    : Array.from({ length: 6 }, (_, i) => plot.xMin + ((plot.xMax - plot.xMin) * i) / 5);

  return (
    <div className="relative border-b border-border bg-canvas">
      <div className="num absolute top-1 left-2 z-10 text-[10px] text-subtle">{plot.title}</div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-[190px] w-full"
        role="img"
        aria-label={plot.title}
        onClick={(e) => {
          const r = (e.target as SVGElement).ownerSVGElement?.getBoundingClientRect() ?? (e.currentTarget as SVGSVGElement).getBoundingClientRect();
          const px = ((e.clientX - r.left) / r.width) * W;
          const t = (px - L) / (W - L - 12);
          onCursor(plot.logX ? Math.pow(10, Math.log10(plot.xMin) + t * (Math.log10(plot.xMax) - Math.log10(plot.xMin))) : plot.xMin + t * (plot.xMax - plot.xMin));
        }}
      >
        {ticksY.map((t, i) => (
          <g key={i}>
            <line x1={L} y1={sy(t)} x2={W - 12} y2={sy(t)} stroke="var(--color-grid)" strokeWidth={0.7} />
            <text x={L - 6} y={sy(t) + 3} fontSize={9} textAnchor="end" className="num" fill="var(--color-subtle)">
              {t.toFixed(plot.unit === "V" ? 2 : 0)}
            </text>
          </g>
        ))}
        {ticksX.map((t, i) => (
          <g key={i}>
            <line x1={sx(t)} y1={8} x2={sx(t)} y2={H - B} stroke="var(--color-grid)" strokeWidth={0.7} />
            <text x={sx(t)} y={H - B + 12} fontSize={9} textAnchor="middle" className="num" fill="var(--color-subtle)">
              {plot.logX ? fmtHz(t) : `${(t * 1e9).toFixed(0)} ns`}
            </text>
          </g>
        ))}
        <text x={8} y={14} fontSize={9} className="num" fill="var(--color-subtle)" transform={`rotate(-90 10 ${H / 2})`}>
          {plot.unit}
        </text>
        {plot.series.map((s) => (
          <polyline
            key={s.name}
            fill="none"
            stroke={s.color}
            strokeWidth={1.3}
            points={s.pts.filter((p) => p.x >= plot.xMin && p.x <= plot.xMax).map((p) => `${sx(p.x)},${sy(p.y)}`).join(" ")}
          />
        ))}
        <line x1={sx(cursorX)} y1={8} x2={sx(cursorX)} y2={H - B} stroke="var(--color-warning)" strokeDasharray="4 3" />
        <text x={sx(cursorX) + 4} y={18} fontSize={9} className="num" fill="var(--color-warning)">
          {plot.logX ? fmtHz(cursorX) : `${(cursorX * 1e9).toFixed(1)} ns`}
        </text>
        <line x1={L} y1={H - B} x2={W - 12} y2={H - B} stroke="var(--color-border)" />
        <line x1={L} y1={8} x2={L} y2={H - B} stroke="var(--color-border)" />
      </svg>
    </div>
  );
}

export function WaveformAnalyzer() {
  const s = useStore();
  const wave = s.liveWave;
  const [cursor1, setCursor1] = useState(0);
  const [cursor2, setCursor2] = useState(0);
  const [hidden, setHidden] = useState<string[]>([]);
  const [calc, setCalc] = useState(false);
  const [fn, setFn] = useState("dB20");
  const [stacked, setStacked] = useState(true);

  useEffect(() => {
    if (wave && wave.x.length > 0) {
      setCursor1(wave.x[Math.floor(wave.x.length / 2)]);
      setCursor2(wave.x[Math.floor(wave.x.length / 4)]);
      setHidden([]);
    }
  }, [wave]);

  const isAc = wave?.analysis === "ac";
  const traces = wave?.traces ?? [];
  const wx = wave?.x ?? [];
  const colorOf = (name: string): string => {
    const idx = traces.map((t) => t.name).indexOf(name);
    return PALETTE[((idx % PALETTE.length) + PALETTE.length) % PALETTE.length];
  };
  const visible = (name: string): boolean => !hidden.includes(name);
  const jobShort = wave ? `${wave.job_id.slice(0, 8)}…` : "—";

  const magSeries = (wave && isAc ? traces : []).map((t) => ({
    name: t.name,
    color: colorOf(t.name),
    pts: toPts(wx, t.magnitude_db ?? []),
  })).filter((x) => visible(x.name) && x.pts.length > 0);
  const phaseSeries = (wave && isAc ? traces : []).map((t) => ({
    name: t.name,
    color: colorOf(t.name),
    pts: toPts(wx, t.phase_deg ?? []),
  })).filter((x) => visible(x.name) && x.pts.length > 0);
  const tranSeries = (wave && !isAc ? traces : []).map((t) => ({
    name: t.name,
    color: colorOf(t.name),
    pts: toPts(wx, t.y ?? []),
  })).filter((x) => visible(x.name) && x.pts.length > 0);

  const magLim = extent(magSeries.flatMap((x) => x.pts), true);
  const phaseLim = extent(phaseSeries.flatMap((x) => x.pts), true);
  const tranLim = extent(tranSeries.flatMap((x) => x.pts), false);

  const atX = (v: number): number => (wave && wave.x.length > 0 ? nearestIdx(wave.x, v) : 0);
  const fmtX = (v: number): string => (isAc ? fmtHz(v) : `${(v * 1e9).toFixed(1)} ns`);

  const acPlots: Plot[] = [
    {
      title: `Magnitude (dB) — live ${jobShort}`,
      unit: "dB",
      logX: true,
      ...magLim,
      series: magSeries,
    },
    {
      title: `Phase (deg) — live ${jobShort}`,
      unit: "deg",
      logX: true,
      ...phaseLim,
      series: phaseSeries,
    },
  ];
  const trPlots: Plot[] = [
    {
      title: `Transient (V) — live ${jobShort}`,
      unit: "V",
      logX: false,
      ...tranLim,
      series: tranSeries,
    },
  ];
  const plots = !wave ? [] : isAc ? (stacked ? acPlots : [acPlots[0]]) : trPlots;

  return (
    <div className="flex min-h-0 flex-1 bg-background">
      {/* results browser */}
      <div className="flex w-[210px] shrink-0 flex-col border-r border-border bg-panel">
        <div className="panel-hd">Results Browser</div>
        <div className="min-h-0 flex-1 overflow-auto">
          {wave ? (
            <div>
              <div className="num border-b border-border/40 px-2 py-[4px] text-[11px] text-foreground">
                job {jobShort}
              </div>
              <div className="num px-4 text-[11px] text-subtle">
                {wave.analysis} · {wave.x.length} pts
              </div>
              {traces.map((t) => (
                <button
                  key={t.name}
                  onClick={() =>
                    setHidden(hidden.includes(t.name) ? hidden.filter((x) => x !== t.name) : [...hidden, t.name])
                  }
                  className="block w-full border-b border-border/30 py-[3px] pl-7 text-left text-[11px] text-muted-foreground hover:bg-raised/60 hover:text-foreground"
                >
                  {t.name}
                </button>
              ))}
            </div>
          ) : (
            <div className="num px-2 py-2 text-[11px] text-subtle">
              No live run — press Run in Simulation Explorer.
            </div>
          )}
        </div>
        <SectionTitle>Legend</SectionTitle>
        {traces.map((t) => (
          <div key={t.name} className="flex items-center gap-2 border-b border-border/40 px-2 py-[4px] text-[11px]">
            <span className="h-[3px] w-[14px]" style={{ background: colorOf(t.name) }} />
            <span className="num">{t.name}</span>
            <span className="ml-auto flex gap-1">
              <button aria-label={`toggle ${t.name}`} onClick={() => setHidden(hidden.includes(t.name) ? hidden.filter((x) => x !== t.name) : [...hidden, t.name])}>
                {hidden.includes(t.name) ? <EyeOff className="h-[12px] w-[12px] text-subtle" /> : <Eye className="h-[12px] w-[12px] text-subtle" />}
              </button>
              <button aria-label={`delete ${t.name}`}>
                <Trash2 className="h-[12px] w-[12px] text-subtle hover:text-critical" />
              </button>
            </span>
          </div>
        ))}
      </div>

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="flex h-[28px] shrink-0 items-center gap-1 border-b border-border bg-chrome px-2">
          <IconBtn label="Add Signal"><Plus className="h-[13px] w-[13px]" /></IconBtn>
          <IconBtn label="Delete Signal"><Minus className="h-[13px] w-[13px]" /></IconBtn>
          <IconBtn label="Calculator" active={calc} onClick={() => setCalc(!calc)}><Calculator className="h-[13px] w-[13px]" /></IconBtn>
          <Sep />
          <IconBtn label="Cursor"><Crosshair className="h-[13px] w-[13px]" /></IconBtn>
          <IconBtn label="Vertical Marker"><ScanLine className="h-[13px] w-[13px]" /></IconBtn>
          <IconBtn label="Horizontal Marker"><ScanLine className="h-[13px] w-[13px] rotate-90" /></IconBtn>
          <Sep />
          <IconBtn label="Zoom Box"><Maximize2 className="h-[13px] w-[13px]" /></IconBtn>
          <IconBtn label="Pan"><Move className="h-[13px] w-[13px]" /></IconBtn>
          <IconBtn label="Stack" active={stacked} onClick={() => setStacked(true)}><Rows3 className="h-[13px] w-[13px]" /></IconBtn>
          <IconBtn label="Overlay" active={!stacked} onClick={() => setStacked(false)}><Layers className="h-[13px] w-[13px]" /></IconBtn>
          <IconBtn label="Export"><Download className="h-[13px] w-[13px]" /></IconBtn>
          <div className="ml-auto flex gap-1 text-[11px]">
            <span className="num rounded-[3px] border border-border px-2 py-[2px] text-primary">
              {wave ? wave.analysis : "no data"}
            </span>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-auto">
          {plots.map((p, i) => (
            <PlotPane key={i} plot={p} cursorX={i === 0 ? cursor1 : cursor2} onCursor={i === 0 ? setCursor1 : setCursor2} />
          ))}

          {wave && (
            <div className="grid grid-cols-2 gap-px bg-border">
              {[
                ["M1", cursor1],
                ["M2", cursor2],
              ].map(([label, cur]) => {
                const c = cur as number;
                const idx = atX(c);
                return (
                  <div key={label as string} className="bg-panel p-2">
                    <div className="mb-1 text-[10px] tracking-wider text-subtle uppercase">Marker {label as string}</div>
                    <div className="num text-[11px]">x = {fmtX(c)}</div>
                    {traces.filter((t) => visible(t.name)).map((t) => (
                      <div key={t.name} className="num text-[11px] text-subtle">
                        {isAc
                          ? `${t.name}: ${(t.magnitude_db ?? [])[idx]?.toFixed(2) ?? "—"} dB, ${(t.phase_deg ?? [])[idx]?.toFixed(1) ?? "—"} °`
                          : `${t.name} = ${(t.y ?? [])[idx]?.toFixed(3) ?? "—"} ${t.unit ?? ""}`}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {calc && isAc && wave && (
        <div className="flex w-[250px] shrink-0 flex-col border-l border-border bg-panel">
          <div className="panel-hd">Calculator</div>
          <div className="space-y-2 p-2 text-[11px]">
            <label className="block">
              <span className="text-subtle">Signal</span>
              <select className="num mt-0.5 h-[24px] w-full rounded-[3px] border border-border bg-background px-1 text-[11px]">
                {traces.map((t) => (
                  <option key={t.name}>{t.name}</option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-subtle">Function</span>
              <select
                value={fn}
                onChange={(e) => setFn(e.target.value)}
                className="num mt-0.5 h-[24px] w-full rounded-[3px] border border-border bg-background px-1 text-[11px]"
              >
                {["abs", "phase", "dB20", "deriv", "integral", "average", "rms", "max", "min", "cross", "value", "bandwidth"].map((f) => (
                  <option key={f}>{f}</option>
                ))}
              </select>
            </label>
            <div>
              <span className="text-subtle">Expression</span>
              <div className="num mt-0.5 rounded-[3px] border border-border bg-background px-2 py-1 text-[11px] text-cyan">
                {fn}({traces[0]?.name ?? "—"}) @ M1
              </div>
            </div>
            <div className="flex gap-1">
              {["Evaluate", "Plot", "Add Output"].map((b) => (
                <button
                  key={b}
                  onClick={() => s.log(`Calculator: ${b} ${fn}(${traces[0]?.name ?? "—"}) @ M1`)}
                  className="h-[22px] flex-1 rounded-[3px] border border-border text-[10px] hover:bg-raised"
                >
                  {b}
                </button>
              ))}
            </div>
            <div className="num rounded-[3px] border border-border bg-canvas p-2 text-[11px] text-success">
              result = {(traces.filter((t) => visible(t.name))[0]?.magnitude_db ?? [])[atX(cursor1)]?.toFixed(3) ?? "—"} dB
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
