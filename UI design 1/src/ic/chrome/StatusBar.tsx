import { useStore } from "../store";
import { StatusDot } from "../ui";

export function StatusBar({ coords }: { coords: { x: number; y: number } }) {
  const s = useStore();
  const selCount = s.selection ? 1 : 0;
  return (
    <footer className="flex h-[22px] shrink-0 items-center gap-3 border-t border-border bg-chrome px-2 text-[10px] text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <StatusDot status={s.command ? "RUNNING" : s.simPhase === "RUNNING" ? "RUNNING" : "PASS"} />
        <span className="num text-foreground">{s.command ? s.command.name : s.statusMsg}</span>
        {s.command && <span className="text-subtle">{s.command.hint}</span>}
      </span>
      <span className="num">X: {coords.x.toFixed(3)} µm</span>
      <span className="num">Y: {coords.y.toFixed(3)} µm</span>
      <span className="num">dx: 0.000</span>
      <span className="num">dy: 0.000</span>
      <span className="num">Grid 0.005 µm</span>
      <span className="num">Snap orthogonal</span>
      <span className="num">Selection {selCount}</span>
      <span className="num">Zoom {(s.zoom * 100).toFixed(0)}%</span>
      <span className="num">Scale 4.20 µm/div</span>
      <span className="num">Hierarchy {s.hierPath.join(" > ")}</span>
      <span className="ml-auto num">Tool: {s.tool}</span>
      <span className="num">CPU 34%</span>
      <span className="num">Mem 1.28 GB</span>
      <span className="num">{s.dirty ? "DIRTY" : "SAVED"}</span>
    </footer>
  );
}
