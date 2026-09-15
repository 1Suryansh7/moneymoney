import { X } from "lucide-react";
import { useStore, type WorkspaceId } from "../store";
import { cn } from "@/lib/utils";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";

export function WorkspaceTabs() {
  const s = useStore();
  return (
    <div className="flex h-[30px] shrink-0 items-stretch overflow-x-auto border-b border-border bg-chrome">
      {s.tabs.map((t) => {
        const active = t.id === s.activeWs;
        const dirty = t.id === "schematic" && s.dirty;
        return (
          <ContextMenu key={t.id}>
            <ContextMenuTrigger asChild>
              <div
                role="tab"
                tabIndex={0}
                aria-selected={active}
                onClick={() => s.setActiveWs(t.id)}
                onKeyDown={(e) => e.key === "Enter" && s.setActiveWs(t.id)}
                onAuxClick={(e) => {
                  if (e.button === 1) s.closeTab(t.id);
                }}
                className={cn(
                  "group flex shrink-0 cursor-default items-center gap-1.5 border-r border-border px-3 text-[11px] whitespace-nowrap",
                  active
                    ? "bg-panel text-foreground shadow-[inset_0_-2px_0_var(--color-primary)]"
                    : "text-muted-foreground hover:bg-raised/60"
                )}
              >
                {t.label}
                {dirty && <span className="h-[5px] w-[5px] rounded-full bg-warning" />}
                <button
                  aria-label={`Close ${t.label}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    s.closeTab(t.id);
                  }}
                  className="opacity-0 transition-opacity group-hover:opacity-100"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            </ContextMenuTrigger>
            <ContextMenuContent className="min-w-[180px] text-[11px]">
              <ContextMenuItem className="text-[11px]" onSelect={() => s.closeTab(t.id)}>
                Close
              </ContextMenuItem>
              <ContextMenuItem
                className="text-[11px]"
                onSelect={() => s.setTabs(s.tabs.filter((x) => x.id === t.id))}
              >
                Close Others
              </ContextMenuItem>
              <ContextMenuSeparator />
              <ContextMenuItem
                className="text-[11px]"
                onSelect={() => s.openTab({ id: "split-sl" as WorkspaceId, label: "Schematic ↔ Layout" })}
              >
                Split Editor Right
              </ContextMenuItem>
              <ContextMenuItem className="text-[11px]">Move Tab to New Group</ContextMenuItem>
            </ContextMenuContent>
          </ContextMenu>
        );
      })}
    </div>
  );
}
