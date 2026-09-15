import {
  Bookmark,
  Boxes,
  FileStack,
  FolderTree,
  Layers,
  ListTree,
  Play,
  Search,
  Settings2,
  ShieldCheck,
  Terminal,
  Cpu,
} from "lucide-react";
import { useStore } from "../store";
import { Tip } from "../ui";
import { cn } from "@/lib/utils";

const ITEMS = [
  { id: "Project", icon: FolderTree },
  { id: "Libraries", icon: Boxes },
  { id: "Hierarchy", icon: ListTree },
  { id: "Layers", icon: Layers },
  { id: "Search", icon: Search },
  { id: "Simulation", icon: Play },
  { id: "Verification", icon: ShieldCheck },
  { id: "Jobs", icon: Cpu },
  { id: "Files", icon: FileStack },
  { id: "Bookmarks", icon: Bookmark },
  { id: "Console", icon: Terminal },
];

export function ActivityRail() {
  const s = useStore();
  return (
    <nav className="flex w-[44px] shrink-0 flex-col items-center gap-0.5 border-r border-border bg-chrome py-1">
      {ITEMS.map(({ id, icon: Icon }) => (
        <Tip key={id} label={id}>
          <button
            aria-label={id}
            onClick={() => {
              if (id === "Console") s.setBottomTab("Console");
              else if (id === "Jobs") s.setBottomTab("Jobs");
              s.setRailPanel(id);
              if (!s.panelsVisible) s.setPanelsVisible(true);
            }}
            className={cn(
              "flex h-[30px] w-[30px] items-center justify-center rounded-[3px] text-subtle hover:bg-raised hover:text-foreground",
              s.railPanel === id && "bg-raised text-primary"
            )}
          >
            <Icon className="h-[15px] w-[15px]" />
          </button>
        </Tip>
      ))}
      <div className="mt-auto">
        <Tip label="Settings">
          <button
            aria-label="Settings"
            onClick={() => s.openTab({ id: "settings", label: "Settings" })}
            className="flex h-[30px] w-[30px] items-center justify-center rounded-[3px] text-subtle hover:bg-raised hover:text-foreground"
          >
            <Settings2 className="h-[15px] w-[15px]" />
          </button>
        </Tip>
      </div>
    </nav>
  );
}
