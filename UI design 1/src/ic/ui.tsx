import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ReactNode } from "react";
import type { Status } from "./data";

export function Panel({
  title,
  actions,
  children,
  className,
}: {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex min-h-0 min-w-0 flex-col bg-panel", className)}>
      {title && (
        <div className="panel-hd">
          <span className="truncate">{title}</span>
          <span className="ml-auto flex items-center gap-1">{actions}</span>
        </div>
      )}
      <div className="min-h-0 flex-1 overflow-auto">{children}</div>
    </div>
  );
}

export function Tip({ label, keys, children }: { label: string; keys?: string; children: ReactNode }) {
  return (
    <TooltipProvider delayDuration={250}>
      <Tooltip delayDuration={250}>
        <TooltipTrigger asChild>{children}</TooltipTrigger>
        <TooltipContent
          side="bottom"
          className="rounded-[3px] border border-border bg-popover px-2 py-1 text-[11px] text-foreground shadow-md"
        >
          <span>{label}</span>
          {keys && <span className="ml-2 num text-[10px] text-subtle">{keys}</span>}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function IconBtn({
  label,
  keys,
  active,
  onClick,
  children,
  className,
}: {
  label: string;
  keys?: string;
  active?: boolean;
  onClick?: () => void;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Tip label={label} keys={keys}>
      <button
        type="button"
        aria-label={label}
        onClick={onClick}
        className={cn(
          "flex h-[24px] w-[24px] items-center justify-center rounded-[3px] border border-transparent text-muted-foreground transition-colors hover:bg-raised hover:text-foreground focus-visible:ring-1 focus-visible:ring-ring focus-visible:outline-none",
          active && "border-border bg-raised text-primary",
          className
        )}
      >
        {children}
      </button>
    </Tip>
  );
}

export function Sep() {
  return <span className="mx-1 h-4 w-px bg-border" />;
}

export function StatusDot({ status }: { status: Status | string }) {
  const map: Record<string, string> = {
    PASS: "bg-success",
    COMPLETE: "bg-success",
    SAVED: "bg-success",
    FAIL: "bg-critical",
    FAILED: "bg-critical",
    Failed: "bg-critical",
    Error: "bg-critical",
    WARN: "bg-warning",
    Warning: "bg-warning",
    RUNNING: "bg-primary",
    Running: "bg-primary",
    Queued: "bg-subtle",
    "NOT RUN": "bg-subtle",
  };
  return (
    <span
      className={cn("inline-block h-[6px] w-[6px] shrink-0 rounded-full", map[status] ?? "bg-subtle")}
    />
  );
}

export function StatusCell({ status }: { status: Status | string }) {
  const tone: Record<string, string> = {
    PASS: "text-success",
    FAIL: "text-critical",
    WARN: "text-warning",
    Error: "text-critical",
    Warning: "text-warning",
    "NOT RUN": "text-subtle",
  };
  const glyph: Record<string, string> = {
    PASS: "✓",
    FAIL: "✕",
    WARN: "!",
    Error: "✕",
    Warning: "!",
    "NOT RUN": "·",
  };
  return (
    <span className={cn("num inline-flex items-center gap-1 text-[11px]", tone[status] ?? "text-subtle")}>
      <span aria-hidden>{glyph[status] ?? "·"}</span>
      {status}
    </span>
  );
}

export function Field({
  label,
  value,
  mono = true,
  tone,
}: {
  label: string;
  value: ReactNode;
  mono?: boolean;
  tone?: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-border/50 px-2 py-[5px]">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <span className={cn("text-[11px] text-foreground", mono && "num", tone)}>{value}</span>
    </div>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-[22px] items-center bg-chrome px-2 text-[10px] font-semibold tracking-[0.09em] text-subtle uppercase">
      {children}
    </div>
  );
}

export function Bar({ pct, tone = "bg-primary" }: { pct: number; tone?: string }) {
  return (
    <span className="inline-block h-[5px] w-full max-w-[80px] overflow-hidden rounded-[1px] bg-raised align-middle">
      <span className={cn("block h-full", tone)} style={{ width: `${Math.max(2, Math.min(100, pct))}%` }} />
    </span>
  );
}

export const th =
  "sticky top-0 z-10 h-[24px] bg-chrome px-2 text-left text-[10px] font-semibold tracking-[0.06em] text-subtle uppercase border-b border-border select-none";
export const td = "h-[28px] px-2 text-[11px] text-foreground/90 border-b border-border/40 truncate";
