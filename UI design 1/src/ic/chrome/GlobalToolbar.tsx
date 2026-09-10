import {
  Check,
  ChevronDown,
  Copy,
  FileCode2,
  FilePlus2,
  FolderOpen,
  Grid3x3,
  Layers,
  Play,
  Redo2,
  Save,
  Search,
  ShieldCheck,
  Square,
  Undo2,
  ZoomIn,
  ZoomOut,
  Maximize2,
} from "lucide-react";
import { IconBtn, Sep } from "../ui";
import { useStore } from "../store";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function GlobalToolbar({ onSearch, onNewCell }: { onSearch: () => void; onNewCell: () => void }) {
  const s = useStore();
  return (
    <div className="flex h-[34px] shrink-0 items-center gap-0.5 border-b border-border bg-background px-2">
      <IconBtn label="New Cell View" onClick={onNewCell}><FilePlus2 className="h-[14px] w-[14px]" /></IconBtn>
      <IconBtn label="Open" keys="Ctrl+O" onClick={() => s.openTab({ id: "library", label: "Library" })}>
        <FolderOpen className="h-[14px] w-[14px]" />
      </IconBtn>
      <IconBtn
        label="Check and Save"
        keys="Ctrl+Shift+S"
        onClick={() => {
          s.setDirty(false);
          s.log("Checking schematic...");
          s.log("Completed: 0 errors, 2 warnings.", "warn");
        }}
      >
        <Save className="h-[14px] w-[14px]" />
      </IconBtn>
      <Sep />
      <IconBtn label="Undo" keys="Ctrl+Z"><Undo2 className="h-[14px] w-[14px]" /></IconBtn>
      <IconBtn label="Redo" keys="Ctrl+Y"><Redo2 className="h-[14px] w-[14px]" /></IconBtn>
      <IconBtn label="Copy" keys="C"><Copy className="h-[14px] w-[14px]" /></IconBtn>
      <Sep />
      <IconBtn label="Zoom In" keys="Z" onClick={() => s.setZoom(Math.min(6, s.zoom * 1.25))}>
        <ZoomIn className="h-[14px] w-[14px]" />
      </IconBtn>
      <IconBtn label="Zoom Out" keys="Shift+Z" onClick={() => s.setZoom(Math.max(0.2, s.zoom / 1.25))}>
        <ZoomOut className="h-[14px] w-[14px]" />
      </IconBtn>
      <IconBtn label="Zoom Fit" keys="F" onClick={() => s.setZoom(1)}>
        <Maximize2 className="h-[14px] w-[14px]" />
      </IconBtn>
      <IconBtn label="Toggle Grid"><Grid3x3 className="h-[14px] w-[14px]" /></IconBtn>
      <Sep />
      <IconBtn label="Open Schematic" onClick={() => s.openTab({ id: "schematic", label: "ota_core : schematic" })}>
        <FileCode2 className="h-[14px] w-[14px]" />
      </IconBtn>
      <IconBtn label="Open Layout" onClick={() => s.openTab({ id: "layout", label: "ota_core : layout" })}>
        <Layers className="h-[14px] w-[14px]" />
      </IconBtn>
      <Sep />
      <IconBtn
        label="Netlist and Run"
        keys="F5"
        onClick={() => {
          s.openTab({ id: "sim", label: "Simulation Explorer" });
          s.runSimulation();
        }}
      >
        <Play className="h-[14px] w-[14px] text-success" />
      </IconBtn>
      <IconBtn label="Stop Simulation" onClick={() => s.setSimPhase("READY")}>
        <Square className="h-[12px] w-[12px]" />
      </IconBtn>
      <IconBtn
        label="Run DRC"
        onClick={() => {
          s.openTab({ id: "pv", label: "Physical Verification" });
          s.runDrc();
        }}
      >
        <ShieldCheck className="h-[14px] w-[14px]" />
      </IconBtn>
      <IconBtn label="Check Schematic" onClick={() => s.log("Checking schematic... 0 errors, 2 warnings.", "warn")}>
        <Check className="h-[14px] w-[14px]" />
      </IconBtn>
      <Sep />
      <DropdownMenu>
        <DropdownMenuTrigger className="flex h-[22px] items-center gap-1 rounded-[3px] border border-border bg-panel px-2 text-[11px] text-muted-foreground hover:text-foreground">
          Annotate: <span className="text-foreground">{s.annotate}</span>
          <ChevronDown className="h-3 w-3" />
        </DropdownMenuTrigger>
        <DropdownMenuContent className="text-[11px]">
          {["None", "DC Node Voltages", "Device Currents", "Operating Region", "gm/gds", "Power"].map((o) => (
            <DropdownMenuItem key={o} className="text-[11px]" onSelect={() => s.setAnnotate(o)}>
              {o}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
      <div className="ml-auto flex items-center gap-1">
        <button
          onClick={onSearch}
          className="flex h-[22px] items-center gap-1.5 rounded-[3px] border border-border bg-panel px-2 text-[11px] text-subtle hover:text-foreground"
        >
          <Search className="h-[12px] w-[12px]" /> Search design...
          <span className="num ml-4 text-[10px]">Ctrl+Shift+F</span>
        </button>
      </div>
    </div>
  );
}
