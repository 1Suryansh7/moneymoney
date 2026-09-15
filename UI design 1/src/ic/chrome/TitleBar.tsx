import {
  Bell,
  ChevronDown,
  Circle,
  Cpu,
  Minus,
  Settings,
  Square,
  X,
  Sparkles,
} from "lucide-react";
import { useStore } from "../store";
import { IconBtn, StatusDot, Tip } from "../ui";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

export function TitleBar({ onAssist }: { onAssist: () => void }) {
  const s = useStore();
  const running = s.jobs.filter((j) => j.status === "Running").length;
  return (
    <header className="flex h-[34px] shrink-0 items-center gap-2 border-b border-border bg-chrome px-2">
      <div className="flex items-center gap-2 pr-2">
        <Cpu className="h-[15px] w-[15px] text-primary" />
        <span className="text-[12px] font-semibold tracking-[0.02em]">Axiom IC Studio</span>
        <span className="hidden text-[10px] text-subtle lg:inline">
          Custom IC Design Environment
        </span>
      </div>
      <div className="num flex items-center gap-1 border-l border-border pl-3 text-[11px] text-muted-foreground">
        <span className="text-foreground">aurora_65</span>
        <span className="text-subtle">/</span>
        <span>ota_core</span>
        <span className="text-subtle">/</span>
        <span className="text-primary">schematic</span>
      </div>
      <div className="num mx-auto hidden text-[11px] text-subtle xl:block">
        aurora_65 — ota_core : schematic
      </div>
      <div className="ml-auto flex items-center gap-2 text-[11px]">
        <span className="flex items-center gap-1.5 text-muted-foreground">
          <StatusDot status={s.dirty ? "WARN" : "SAVED"} />
          {s.dirty ? "Modified" : "Saved"}
        </span>
        <DropdownMenu>
          <DropdownMenuTrigger className="flex items-center gap-1 rounded-[3px] px-1.5 py-0.5 text-muted-foreground hover:bg-raised">
            Local <ChevronDown className="h-3 w-3" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-[180px] text-[11px]">
            {["Local", "Workstation", "Compute Farm", "Cloud"].map((c) => (
              <DropdownMenuItem key={c} className="text-[11px]">
                {c}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <span className="text-subtle">License: 4 seats</span>
        <button
          onClick={() => s.setBottomTab("Jobs")}
          className="rounded-[3px] px-1.5 py-0.5 text-muted-foreground hover:bg-raised"
        >
          Jobs <span className="num text-foreground">{running}</span>
        </button>
        <Popover>
          <PopoverTrigger className="relative flex h-[24px] w-[24px] items-center justify-center rounded-[3px] text-muted-foreground hover:bg-raised">
            <Bell className="h-[14px] w-[14px]" />
            <span className="num absolute -top-0.5 -right-0.5 rounded-[2px] bg-primary px-[3px] text-[9px] text-primary-foreground">
              {s.notifications.length}
            </span>
          </PopoverTrigger>
          <PopoverContent
            align="end"
            className="w-[320px] rounded-[4px] border-border bg-popover p-0"
          >
            <div className="panel-hd">Notifications</div>
            <div className="max-h-[300px] overflow-auto">
              {s.notifications.map((n, i) => (
                <div key={i} className="border-b border-border/50 px-2 py-1.5">
                  <div className="flex items-center gap-1.5 text-[11px]">
                    <StatusDot status={n.kind} />
                    <span className="font-medium">{n.title}</span>
                    <span className="num ml-auto text-[10px] text-subtle">{n.time}</span>
                  </div>
                  <div className="pl-3 text-[11px] text-muted-foreground">{n.body}</div>
                </div>
              ))}
            </div>
          </PopoverContent>
        </Popover>
        <IconBtn label="Axiom Assist" onClick={onAssist}>
          <Sparkles className="h-[14px] w-[14px]" />
        </IconBtn>
        <IconBtn
          label="Settings"
          onClick={() => s.openTab({ id: "settings", label: "Settings" })}
        >
          <Settings className="h-[14px] w-[14px]" />
        </IconBtn>
        <Tip label="Yash Sidhu — 2 users viewing">
          <span className="num flex h-[20px] w-[20px] items-center justify-center rounded-full bg-primary/20 text-[10px] text-primary">
            YS
          </span>
        </Tip>
        <div className="ml-1 hidden items-center gap-1 border-l border-border pl-2 text-subtle md:flex">
          <Minus className="h-3 w-3" />
          <Square className="h-[9px] w-[9px]" />
          <X className="h-3 w-3" />
          <Circle className="hidden h-0 w-0" />
        </div>
      </div>
    </header>
  );
}
