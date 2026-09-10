import {
  Menubar,
  MenubarContent,
  MenubarItem,
  MenubarMenu,
  MenubarSeparator,
  MenubarShortcut,
  MenubarTrigger,
} from "@/components/ui/menubar";
import { useStore } from "../store";
import { useCommands } from "../commands";

type Entry = string | { label: string; keys?: string; cmd?: string };

const MENUS: Record<string, Entry[]> = {
  File: [
    { label: "New Cell View...", cmd: "newcell" },
    { label: "Open...", keys: "Ctrl+O", cmd: "library" },
    "Open Recent",
    { label: "Save", keys: "Ctrl+S", cmd: "save" },
    "Save All",
    { label: "Check & Save", keys: "Ctrl+Shift+S", cmd: "check" },
    "Revert",
    "—",
    "Import",
    "Export",
    "Close View",
    "Close Workspace",
    "—",
    "Exit",
  ],
  Edit: [
    { label: "Undo", keys: "Ctrl+Z" },
    { label: "Redo", keys: "Ctrl+Y" },
    "—",
    { label: "Copy", keys: "C" },
    { label: "Move", keys: "M" },
    { label: "Stretch", keys: "S" },
    { label: "Delete", keys: "Del" },
    "—",
    "Properties...",
    "Select All",
  ],
  View: [
    { label: "Zoom Fit", keys: "F", cmd: "fit" },
    { label: "Zoom In", keys: "Z" },
    { label: "Zoom Out", keys: "Shift+Z" },
    "—",
    { label: "Toggle Side Panels", keys: "Ctrl+Shift+B", cmd: "panels" },
    "Show Grid",
    "Show Nets",
    { label: "Layer Palette", cmd: "layers" },
  ],
  Create: [
    { label: "Instance", keys: "I", cmd: "instance" },
    { label: "Wire", keys: "W", cmd: "wire" },
    { label: "Pin", keys: "P" },
    { label: "Label", keys: "L" },
    "Shape",
    "Via",
    "Path",
    "Rectangle",
    "Polygon",
    "Ruler",
    "Text",
  ],
  Design: [
    { label: "Project Overview", cmd: "project" },
    { label: "Library Manager", cmd: "library" },
    { label: "Design Intent", cmd: "intent" },
    { label: "Hierarchy Configuration", cmd: "config" },
    "—",
    "Design Variables...",
    "Revision History",
  ],
  Hierarchy: [
    "Descend Read",
    "Descend Edit",
    "Hierarchy Up",
    "Hierarchy Down",
    "—",
    "Return to Top",
    "Edit In Place",
  ],
  Simulation: [
    { label: "Simulation Explorer", cmd: "sim" },
    { label: "Verification Assembler", cmd: "assembler" },
    { label: "Waveform Analyzer", cmd: "wave" },
    "—",
    { label: "Netlist and Run", keys: "F5", cmd: "run" },
    "Stop",
    "Monte Carlo...",
    "Corners...",
    "Simulator Options...",
  ],
  Verification: [
    "Check Schematic",
    { label: "Run DRC...", cmd: "drc" },
    "Run LVS...",
    "Run ERC...",
    "Connectivity Check",
    "—",
    "View Markers",
    "Clear Markers",
  ],
  Extraction: ["Run PEX...", "Extraction Options...", "Open Extracted View", "—", "Post-Layout Simulation"],
  Tools: [
    { label: "Technology Browser", cmd: "tech" },
    "Layer Stack Viewer",
    "Calculator",
    "Job Monitor",
    { label: "Command Palette", keys: "Ctrl+K", cmd: "palette" },
  ],
  Window: [
    { label: "Split Editor Right", cmd: "split" },
    { label: "Design ↔ Simulation", cmd: "splitds" },
    { label: "Layout ↔ Verification", cmd: "splitlv" },
    "Move Tab to New Group",
    "Close Group",
    "Close Others",
    "—",
    "Reset Workspace",
    "Save Workspace Layout",
  ],
  Help: [
    { label: "Keyboard Shortcuts", keys: "?" },
    "Documentation",
    "Release Notes",
    "About Axiom IC Studio",
  ],
};

export function MenuBar({ onShortcuts, onPalette, onNewCell }: { onShortcuts: () => void; onPalette: () => void; onNewCell: () => void }) {
  const s = useStore();
  const cmds = useCommands();
  const run = (cmd?: string) => {
    if (!cmd) return;
    if (cmd === "palette") return onPalette();
    if (cmd === "newcell") return onNewCell();
    if (cmd === "check") {
      s.log("Checking schematic...");
      s.log("Completed: 0 errors, 2 warnings.", "warn");
      s.setDirty(false);
      return;
    }
    cmds.find((c) => c.id === cmd)?.run();
  };
  return (
    <Menubar className="h-[28px] shrink-0 gap-0 rounded-none border-0 border-b border-border bg-chrome px-1">
      {Object.entries(MENUS).map(([name, items]) => (
        <MenubarMenu key={name}>
          <MenubarTrigger className="h-[22px] rounded-[3px] px-2 text-[12px] font-normal data-[state=open]:bg-raised">
            {name}
          </MenubarTrigger>
          <MenubarContent className="min-w-[220px] rounded-[4px] border-border bg-popover p-1">
            {items.map((it, i) =>
              it === "—" ? (
                <MenubarSeparator key={i} className="bg-border" />
              ) : typeof it === "string" ? (
                <MenubarItem key={i} className="h-[24px] text-[12px]" onSelect={() => s.log(`${name} → ${it}`)}>
                  {it}
                </MenubarItem>
              ) : (
                <MenubarItem
                  key={i}
                  className="h-[24px] text-[12px]"
                  onSelect={() => (it.cmd ? run(it.cmd) : s.log(`${name} → ${it.label}`))}
                >
                  {it.label}
                  {it.keys && <MenubarShortcut className="num text-[10px]">{it.keys}</MenubarShortcut>}
                </MenubarItem>
              )
            )}
            {name === "Help" && (
              <MenubarItem className="h-[24px] text-[12px]" onSelect={onShortcuts}>
                Show Shortcut Overlay
              </MenubarItem>
            )}
          </MenubarContent>
        </MenubarMenu>
      ))}
    </Menubar>
  );
}
