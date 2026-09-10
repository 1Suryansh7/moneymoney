import { useEffect, useState } from "react";
import { Group, Panel, Separator } from "react-resizable-panels";
import { TooltipProvider } from "@/components/ui/tooltip";
import { StoreProvider, useStore } from "./store";
import { TitleBar } from "./chrome/TitleBar";
import { MenuBar } from "./chrome/MenuBar";
import { GlobalToolbar } from "./chrome/GlobalToolbar";
import { WorkspaceTabs } from "./chrome/WorkspaceTabs";
import { ActivityRail } from "./chrome/ActivityRail";
import { LeftDock } from "./chrome/LeftDock";
import { RightDock } from "./chrome/RightDock";
import { BottomDock } from "./chrome/BottomDock";
import { StatusBar } from "./chrome/StatusBar";
import { AssistPanel, CommandPalette, GlobalSearch, NewCellDialog, ShortcutOverlay } from "./chrome/Overlays";
import { SchematicEditor } from "./workspaces/SchematicEditor";
import { LayoutEditor } from "./workspaces/LayoutEditor";
import { SimulationExplorer } from "./workspaces/SimulationExplorer";
import { WaveformAnalyzer } from "./workspaces/WaveformAnalyzer";
import { VerificationAssembler } from "./workspaces/VerificationAssembler";
import { PhysicalVerification } from "./workspaces/PhysicalVerification";
import {
  DesignIntent,
  HierarchyConfig,
  JobMonitor,
  LibraryManager,
  ProjectDashboard,
  SettingsWorkspace,
  StartPage,
  TechnologyBrowser,
} from "./workspaces/Misc";

function Workspace() {
  const s = useStore();
  switch (s.activeWs) {
    case "schematic":
      return <SchematicEditor />;
    case "layout":
      return <LayoutEditor />;
    case "sim":
      return <SimulationExplorer />;
    case "waveforms":
      return <WaveformAnalyzer />;
    case "assembler":
      return <VerificationAssembler />;
    case "pv":
      return <PhysicalVerification />;
    case "library":
      return <LibraryManager />;
    case "project":
      return <ProjectDashboard />;
    case "tech":
      return <TechnologyBrowser />;
    case "config":
      return <HierarchyConfig />;
    case "intent":
      return <DesignIntent />;
    case "jobs":
      return <JobMonitor />;
    case "settings":
      return <SettingsWorkspace />;
    case "start":
      return <StartPage />;
    case "split-sl":
      return (
        <Group orientation="horizontal">
          <Panel defaultSize="50" minSize="20">
            <SchematicEditor dense />
          </Panel>
          <Separator className="w-px bg-border hover:bg-primary" />
          <Panel defaultSize="50" minSize="20">
            <LayoutEditor dense />
          </Panel>
        </Group>
      );
    case "split-ds":
      return (
        <Group orientation="horizontal">
          <Panel defaultSize="55" minSize="20">
            <SchematicEditor dense />
          </Panel>
          <Separator className="w-px bg-border hover:bg-primary" />
          <Panel defaultSize="45" minSize="20">
            <SimulationExplorer dense />
          </Panel>
        </Group>
      );
    case "split-lv":
      return (
        <Group orientation="horizontal">
          <Panel defaultSize="50" minSize="20">
            <LayoutEditor dense />
          </Panel>
          <Separator className="w-px bg-border hover:bg-primary" />
          <Panel defaultSize="50" minSize="20">
            <WaveformAnalyzer />
          </Panel>
        </Group>
      );
    default:
      return <StartPage />;
  }
}

function Shell() {
  const s = useStore();
  const [palette, setPalette] = useState(false);
  const [search, setSearch] = useState(false);
  const [shortcuts, setShortcuts] = useState(false);
  const [newCell, setNewCell] = useState(false);
  const [assist, setAssist] = useState(false);
  const [bottomOpen, setBottomOpen] = useState(true);
  const [coords] = useState({ x: 12.45, y: 8.32 });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey;
      const tag = (e.target as HTMLElement)?.tagName;
      const typing = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";
      if (mod && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPalette(true);
      } else if (mod && e.key.toLowerCase() === "f") {
        e.preventDefault();
        setSearch(true);
      } else if (mod && e.key.toLowerCase() === "r") {
        e.preventDefault();
        s.runSimulation();
      } else if (mod && e.key.toLowerCase() === "s") {
        e.preventDefault();
        s.setDirty(false);
        s.log("Saved ota_core/schematic.");
        s.setStatusMsg("SAVED");
      } else if (!typing && !mod) {
        if (e.key === "?") setShortcuts(true);
        if (e.key === "f") s.setStatusMsg("Zoom fit");
        if (e.key === "Escape") {
          s.setCommand(null);
          s.setTool("Select");
          s.setStatusMsg("READY");
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [s]);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("theme-light", "theme-contrast");
    if (s.theme === "light") root.classList.add("theme-light");
    if (s.theme === "contrast") root.classList.add("theme-contrast");
  }, [s.theme]);

  return (
    <div className="flex h-screen min-h-0 flex-col overflow-hidden bg-background text-foreground select-none">
      <TitleBar onAssist={() => setAssist(true)} />
      <MenuBar onShortcuts={() => setShortcuts(true)} onPalette={() => setPalette(true)} onNewCell={() => setNewCell(true)} />
      <GlobalToolbar onSearch={() => setSearch(true)} onNewCell={() => setNewCell(true)} />
      <WorkspaceTabs />
      <div className="flex min-h-0 flex-1">
        <ActivityRail />
        <Group orientation="horizontal" className="min-h-0 flex-1">
          {s.panelsVisible && (
            <>
              <Panel defaultSize="17" minSize="10" maxSize="30">
                <LeftDock />
              </Panel>
              <Separator className="w-px bg-border hover:bg-primary" />
            </>
          )}
          <Panel minSize="30">
            <Group orientation="vertical">
              <Panel minSize="25">
                <div className="flex h-full min-h-0 flex-col">
                  <Workspace />
                </div>
              </Panel>
              {bottomOpen && (
                <>
                  <Separator className="h-px bg-border hover:bg-primary" />
                  <Panel defaultSize="26" minSize="8" maxSize="60">
                    <BottomDock onCollapse={() => setBottomOpen(false)} />
                  </Panel>
                </>
              )}
            </Group>
          </Panel>
          {s.panelsVisible && (
            <>
              <Separator className="w-px bg-border hover:bg-primary" />
              <Panel defaultSize="19" minSize="12" maxSize="34">
                <RightDock />
              </Panel>
            </>
          )}
        </Group>
      </div>
      {!bottomOpen && (
        <button
          onClick={() => setBottomOpen(true)}
          className="h-[18px] border-t border-border bg-chrome text-[10px] tracking-wider text-subtle uppercase hover:text-foreground"
        >
          Show console
        </button>
      )}
      <StatusBar coords={coords} />

      <CommandPalette open={palette} onOpenChange={setPalette} />
      <GlobalSearch open={search} onOpenChange={setSearch} />
      <ShortcutOverlay open={shortcuts} onOpenChange={setShortcuts} />
      <NewCellDialog open={newCell} onOpenChange={setNewCell} />
      <AssistPanel open={assist} onClose={() => setAssist(false)} />
    </div>
  );
}

export function ICStudioApp() {
  return (
    <StoreProvider>
      <TooltipProvider delayDuration={300}>
        <Shell />
      </TooltipProvider>
    </StoreProvider>
  );
}
