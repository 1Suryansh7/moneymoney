import { useMemo } from "react";
import { useStore, type WorkspaceId } from "./store";

export type Command = { id: string; label: string; keys?: string; run: () => void };

export function useCommands(): Command[] {
  const s = useStore();
  return useMemo(() => {
    const open = (id: WorkspaceId, label: string) => () => s.openTab({ id, label });
    return [
      { id: "drc", label: "Run DRC on Current Cell", keys: "", run: () => { s.openTab({ id: "pv", label: "Physical Verification" }); s.runDrc(); } },
      { id: "layout", label: "Open Layout", keys: "", run: open("layout", "ota_core : layout") },
      { id: "schematic", label: "Open Schematic", run: open("schematic", "ota_core : schematic") },
      { id: "sim", label: "Open Simulation Explorer", run: open("sim", "Simulation Explorer") },
      { id: "run", label: "Run Simulation", keys: "F5", run: () => { s.openTab({ id: "sim", label: "Simulation Explorer" }); s.runSimulation(); } },
      { id: "wave", label: "Open Waveform Analyzer", run: open("waveforms", "Waveform Analyzer") },
      { id: "assembler", label: "Open Verification Assembler", run: open("assembler", "Verification Assembler") },
      { id: "instance", label: "Create Instance", keys: "I", run: () => s.setTool("Instance") },
      { id: "wire", label: "Create Wire", keys: "W", run: () => s.setTool("Wire") },
      { id: "fit", label: "Zoom Fit", keys: "F", run: () => s.setZoom(1) },
      { id: "jobs", label: "Show Jobs", run: () => { s.setBottomTab("Jobs"); } },
      { id: "layers", label: "Toggle Layer Palette", run: () => s.setRailPanel("Layers") },
      { id: "split", label: "Schematic ↔ Layout Split", run: open("split-sl", "Schematic ↔ Layout") },
      { id: "splitds", label: "Design ↔ Simulation Split", run: open("split-ds", "Design ↔ Simulation") },
      { id: "splitlv", label: "Layout ↔ Verification Split", run: open("split-lv", "Layout ↔ Verification") },
      { id: "tech", label: "Open Technology Browser", run: open("tech", "Technology") },
      { id: "config", label: "Open Hierarchy Configuration", run: open("config", "Hierarchy Configuration") },
      { id: "intent", label: "Open Design Intent", run: open("intent", "Design Intent") },
      { id: "project", label: "Open Project Overview", run: open("project", "Project") },
      { id: "library", label: "Open Library Manager", run: open("library", "Library") },
      { id: "settings", label: "Open Settings", keys: "Ctrl+,", run: open("settings", "Settings") },
      { id: "theme", label: "Switch Theme", run: () => s.setTheme(s.theme === "graphite" ? "light" : s.theme === "light" ? "contrast" : "graphite") },
      { id: "save", label: "Save Current View", keys: "Ctrl+S", run: () => { s.setDirty(false); s.setStatusMsg("Saved ota_core/schematic"); s.log("Saved ota_core/schematic."); } },
      { id: "panels", label: "Toggle Side Panels", keys: "Ctrl+Shift+B", run: () => s.setPanelsVisible(!s.panelsVisible) },
    ];
  }, [s]);
}
