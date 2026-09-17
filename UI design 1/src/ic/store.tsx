import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { LAYERS, OUTPUTS, DRC_VIOLATIONS, type Status } from "./data";
import {
  ApiError,
  cancelJob,
  comparePostlayout as requestCompare,
  createCell,
  createProject,
  createSpec,
  getJob,
  getSchematic,
  getWaveforms,
  health,
  instantiate,
  listCells,
  listJobs,
  listTrials,
  measure,
  renameCell,
  runCorners as requestCorners,
  runDemo,
  startStudy as requestStudy,
  type CellSummary,
  type CompareOut,
  type CornerRun,
  type JobDetail,
  type JobSummary,
  type Schematic,
  type Trial,
  type Waveforms,
} from "./api";

export type WorkspaceId =
  | "start"
  | "project"
  | "library"
  | "schematic"
  | "layout"
  | "sim"
  | "assembler"
  | "waveforms"
  | "pv"
  | "tech"
  | "config"
  | "intent"
  | "jobs"
  | "settings"
  | "split-sl"
  | "split-ds"
  | "split-lv";

export type Tab = { id: WorkspaceId; label: string; dirty?: boolean };

export type ConsoleLine = { t: string; text: string; kind?: "info" | "warn" | "err" | "cmd" };

export type Job = {
  id: string;
  type: string;
  cell: string;
  host: string;
  status: "Running" | "Complete" | "Queued" | "Failed";
  progress: number;
  runtime: string;
};

export type Notif = { title: string; body: string; time: string; kind: Status | "INFO" };

export type SimPhase = "READY" | "NETLISTING" | "QUEUED" | "RUNNING" | "EVALUATING" | "COMPLETE";

function now() {
  const d = new Date();
  return d.toTimeString().slice(0, 8);
}

const START_LINES: ConsoleLine[] = [
  { t: "17:41:00", text: "Axiom IC Studio 4.2" },
  { t: "17:41:00", text: "Loading project aurora_65..." },
  { t: "17:41:01", text: "Loading technology gpdk65..." },
  { t: "17:41:01", text: "Initializing connectivity..." },
  { t: "17:41:02", text: "Loading 38 cells..." },
  { t: "17:41:02", text: "Opened ota_core/schematic" },
  { t: "17:41:03", text: "Connectivity database loaded." },
  { t: "17:41:05", text: "38 instances, 52 nets." },
  { t: "17:41:18", text: "Checking schematic..." },
  { t: "17:41:18", text: "INFO: 0 errors, 2 warnings.", kind: "warn" },
  { t: "17:41:24", text: "Saved ota_core/schematic." },
  { t: "17:41:24", text: "Ready." },
];

export type Selection =
  | { kind: "instance"; id: string }
  | { kind: "net"; id: string }
  | { kind: "layoutDevice"; id: string }
  | { kind: "constraint"; id: string }
  | null;

/** Map one ledger summary onto the Job-queue row shape (display only). */
function mapLedgerJob(j: JobSummary): Job {
  return {
    id: j.job_id,
    type: j.kind,
    cell: "—",
    host: "localhost",
    status:
      j.status === "succeeded"
        ? "Complete"
        : j.status === "failed"
          ? "Failed"
          : j.status === "running"
            ? "Running"
            : "Queued",
    progress: j.status === "succeeded" || j.status === "failed" ? 100 : j.status === "running" ? 50 : 0,
    runtime: "—",
  };
}

/** Ledger status onto the explorer phase vocabulary. */
function phaseFor(status: string): SimPhase {
  if (status === "succeeded") return "EVALUATING";
  if (status === "failed") return "READY";
  if (status === "running") return "RUNNING";
  return "QUEUED";
}

function useStoreValue() {
  const [activeWs, setActiveWs] = useState<WorkspaceId>("schematic");
  const [tabs, setTabs] = useState<Tab[]>([
    { id: "library", label: "Library" },
    { id: "schematic", label: "ota_core : schematic" },
    { id: "layout", label: "ota_core : layout" },
    { id: "sim", label: "Simulation Explorer" },
    { id: "waveforms", label: "Waveform Analyzer" },
  ]);
  const [selection, setSelection] = useState<Selection>({ kind: "instance", id: "M1" });
  const [hierPath, setHierPath] = useState<string[]>(["aurora_65", "ota_core"]);
  const [tool, setTool] = useState("Select");
  const [command, setCommand] = useState<{ name: string; hint: string } | null>(null);
  const [annotate, setAnnotate] = useState<string>("None");
  const [console_, setConsole] = useState<ConsoleLine[]>(START_LINES);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [cells, setCells] = useState<CellSummary[]>([]);
  const [activeCellId, setActiveCellId] = useState<string | null>(null);
  const [activeSchematic, setActiveSchematic] = useState<Schematic | null>(null);
  const [liveWave, setLiveWave] = useState<Waveforms | null>(null);
  const [lastJobId, setLastJobId] = useState<string | null>(null);
  const [cornerRuns, setCornerRuns] = useState<CornerRun[]>([]);
  const [cornerWaves, setCornerWaves] = useState<Record<string, Waveforms>>({});
  const [cornerPhase, setCornerPhase] = useState<"IDLE" | "RUNNING" | "DONE">("IDLE");
  const [compareData, setCompareData] = useState<CompareOut | null>(null);
  const [comparePhase, setComparePhase] = useState<"IDLE" | "RUNNING" | "DONE">("IDLE");
  const [demoCellId, setDemoCellId] = useState<string | null>(null);
  const [measuredGain, setMeasuredGain] = useState<{ value: number; unit: string } | null>(null);
  const [measuredBandwidth, setMeasuredBandwidth] = useState<{ value: number; unit: string } | null>(
    null,
  );
  const [studyJobId, setStudyJobId] = useState<string | null>(null);
  const [studyId, setStudyId] = useState<string | null>(null);
  const [trials, setTrials] = useState<Trial[]>([]);
  const [studyPhase, setStudyPhase] = useState<"IDLE" | "OPTIMIZING" | "DONE">("IDLE");
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const [simPhase, setSimPhase] = useState<SimPhase>("READY");
  const [simProgress, setSimProgress] = useState(0);
  const [outputs, setOutputs] = useState(OUTPUTS);
  const [ibias, setIbias] = useState(200);
  const [drcDone, setDrcDone] = useState(false);
  const [pexDone, setPexDone] = useState(false);
  const [postLayout, setPostLayout] = useState(false);
  const [lvsMismatch, setLvsMismatch] = useState(false);
  const [activeDrc, setActiveDrc] = useState<string | null>(null);
  const [visibleLayers, setVisibleLayers] = useState<string[]>(LAYERS.map((l) => l.name));
  const [overlay, setOverlay] = useState("None");
  const [ratlines, setRatlines] = useState(false);
  const [dirty, setDirty] = useState(true);
  const [theme, setTheme] = useState("graphite");
  const [notifications, setNotifications] = useState<Notif[]>([
    { title: "DRC completed", body: "7 violations detected", time: "17:44", kind: "FAIL" },
    { title: "Simulation completed", body: "tb_ota_ac", time: "17:42", kind: "PASS" },
    { title: "Monte Carlo", body: "Yield below target: 97.5%", time: "17:36", kind: "WARN" },
  ]);
  const [bottomTab, setBottomTab] = useState("Console");
  const [rightTab, setRightTab] = useState("Properties");
  const [railPanel, setRailPanel] = useState("Project");
  const [panelsVisible, setPanelsVisible] = useState(true);
  const [statusMsg, setStatusMsg] = useState("READY");
  const [zoom, setZoom] = useState(1);
  const timers = useRef<number[]>([]);
  const runToken = useRef(0);
  const studyToken = useRef(0);
  const cornerToken = useRef(0);
  const compareToken = useRef(0);

  const log = useCallback((text: string, kind?: ConsoleLine["kind"]) => {
    setConsole((c) => [...c, { t: now(), text, kind }].slice(-400));
  }, []);

  const openTab = useCallback((tab: Tab) => {
    setTabs((t) => (t.some((x) => x.id === tab.id) ? t : [...t, tab]));
    setActiveWs(tab.id);
  }, []);

  const closeTab = useCallback(
    (id: WorkspaceId) => {
      setTabs((t) => {
        const next = t.filter((x) => x.id !== id);
        if (id === activeWs && next.length) setActiveWs(next[next.length - 1].id);
        return next;
      });
    },
    [activeWs]
  );

  const notify = useCallback((n: Notif) => setNotifications((x) => [n, ...x].slice(0, 12)), []);

  const refreshCells = useCallback(async (): Promise<CellSummary[]> => {
    try {
      const rows = await listCells();
      setBackendUp(true);
      setCells(rows);
      return rows;
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        setBackendUp(false);
      } else {
        log(`Cell refresh failed: ${err instanceof Error ? err.message : String(err)}`, "warn");
      }
      return [];
    }
  }, [log]);

  const refreshJobs = useCallback(async () => {
    try {
      const rows = await listJobs();
      setBackendUp(true);
      setJobs(rows.map(mapLedgerJob));
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        setBackendUp(false);
      } else {
        log(`Jobs refresh failed: ${err instanceof Error ? err.message : String(err)}`, "warn");
      }
    }
  }, [log]);

  /** Select a cell and fetch its live schematic (auto-layout downstream). */
  const selectCell = useCallback(
    async (cellId: string | null) => {
      setActiveCellId(cellId);
      if (cellId === null) {
        setActiveSchematic(null);
        return;
      }
      try {
        const schem = await getSchematic(cellId);
        setBackendUp(true);
        setActiveSchematic(schem);
        setTabs((t) =>
          t.map((tab) => (tab.id === "schematic" ? { ...tab, label: `${schem.cell_name} : schematic` } : tab)),
        );
      } catch (err) {
        setActiveSchematic(null);
        log(`Schematic load failed: ${err instanceof Error ? err.message : String(err)}`, "err");
      }
    },
    [log],
  );

  /** Create a project, anchor cell, and template-instantiated cell (backend defaults). */
  const createTemplateCell = useCallback(
    async (projectName: string, cellName: string, templateId: string): Promise<string> => {
      const project = await createProject(projectName);
      const anchor = await createCell(project.project_id, `${cellName}_anchor`);
      const out = await instantiate(anchor.cell_id, templateId, {});
      await renameCell(out.cell_id, cellName);
      setBackendUp(true);
      await refreshCells();
      await selectCell(out.cell_id);
      return out.cell_id;
    },
    [refreshCells, selectCell],
  );

  const runSimulation = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    runToken.current += 1;
    const token = runToken.current;
    setLiveWave(null);
    setMeasuredGain(null);
    setMeasuredBandwidth(null);
    setSimPhase("NETLISTING");
    setSimProgress(5);
    log("Run: POST /testbenches/run inverter_tran");
    void (async () => {
      let jobId: string;
      let demoCell: string;
      try {
        const out = await runDemo("inverter_tran", 21);
        setBackendUp(true);
        jobId = out.job_id;
        demoCell = out.cell_id;
        setDemoCellId(demoCell);
      } catch (err) {
        if (token !== runToken.current) return;
        setSimPhase("READY");
        setSimProgress(0);
        const msg = err instanceof ApiError ? err.detail : String(err);
        if (err instanceof ApiError && err.status === 0) setBackendUp(false);
        log(`Run failed to launch: ${msg}`, "err");
        notify({
          title: "Simulation failed to launch",
          body: msg.slice(0, 80),
          time: now().slice(0, 5),
          kind: "FAIL",
        });
        return;
      }
      if (token !== runToken.current) return;
      setLastJobId(jobId);
      setSimPhase("QUEUED");
      setSimProgress(10);
      log(`Job ${jobId.slice(0, 8)}… queued; polling ledger`);
      const later = (fn: () => void, ms: number) =>
        timers.current.push(window.setTimeout(fn, ms) as unknown as number);
      const poll = async (tries: number): Promise<void> => {
        if (token !== runToken.current) return;
        if (tries <= 0) {
          setSimPhase("READY");
          setSimProgress(0);
          log(`Job ${jobId.slice(0, 8)}… poll timed out`, "err");
          return;
        }
        let detail: JobDetail;
        try {
          detail = await getJob(jobId);
        } catch (err) {
          if (err instanceof ApiError && err.status === 0) {
            setBackendUp(false);
            setSimPhase("READY");
            setSimProgress(0);
            log("Backend lost during poll", "err");
            return;
          }
          later(() => void poll(tries - 1), 400);
          return;
        }
        if (token !== runToken.current) return;
        if (detail.status === "succeeded") {
          setSimPhase("EVALUATING");
          setSimProgress(90);
          log(`Job ${jobId.slice(0, 8)}… succeeded; reading waveforms`);
          try {
            const wave = await getWaveforms(jobId);
            if (token !== runToken.current) return;
            setLiveWave(wave);
            setSimPhase("COMPLETE");
            setSimProgress(100);
            log(`Waveforms: ${wave.traces.length} traces over ${wave.x.length} points`);
            notify({
              title: "Simulation completed",
              body: `${wave.analysis} — ${wave.traces.length} traces live`,
              time: now().slice(0, 5),
              kind: "PASS",
            });
            try {
              const m = await measure(demoCell, "dc_gain");
              if (token !== runToken.current) return;
              setMeasuredGain({ value: m.value, unit: m.unit });
              log(`Measured DC gain: ${m.value.toFixed(2)} ${m.unit}`);
            } catch (merr) {
              if (token !== runToken.current) return;
              log(
                `Gain measure skipped: ${merr instanceof Error ? merr.message : String(merr)}`,
                "warn",
              );
            }
            try {
              const b = await measure(demoCell, "bandwidth");
              if (token !== runToken.current) return;
              setMeasuredBandwidth({ value: b.value, unit: b.unit });
              log(`Measured bandwidth: ${(b.value / 1e6).toFixed(2)} MHz`);
            } catch (merr) {
              if (token !== runToken.current) return;
              log(
                `Bandwidth measure skipped: ${merr instanceof Error ? merr.message : String(merr)}`,
                "warn",
              );
            }
          } catch (err) {
            if (token !== runToken.current) return;
            setSimPhase("READY");
            setSimProgress(0);
            log(`Waveform read failed: ${err instanceof Error ? err.message : String(err)}`, "err");
          }
          void refreshJobs();
          return;
        }
        if (detail.status === "failed") {
          setSimPhase("READY");
          setSimProgress(0);
          const first = (detail.error ?? "unknown failure").split("\n")[0];
          log(`Job ${jobId.slice(0, 8)}… failed: ${first}`, "err");
          notify({
            title: "Simulation failed",
            body: first.slice(0, 80),
            time: now().slice(0, 5),
            kind: "FAIL",
          });
          void refreshJobs();
          return;
        }
        setSimPhase(phaseFor(detail.status));
        setSimProgress(detail.status === "running" ? 50 : 10);
        later(() => void poll(tries - 1), 400);
      };
      void poll(150);
    })();
  }, [log, notify, refreshJobs]);

  const stopSimulation = useCallback(() => {
    runToken.current += 1;
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setSimPhase("READY");
    setSimProgress(0);
    log("Run cancelled by user", "warn");
    if (lastJobId) {
      const jid = lastJobId;
      void (async () => {
        try {
          const res = await cancelJob(jid);
          log(`Backend job ${jid.slice(0, 8)}… ${res.status}`);
        } catch (err) {
          log(
            `Backend cancel failed: ${err instanceof Error ? err.message : String(err)}`,
            "warn",
          );
        }
      })();
    }
  }, [log, lastJobId]);

  /** PVT sweep: POST /corners/run for the checked envelope ids, then pull
   * one wave per succeeded corner. Display only — no metric math here;
   * per-corner faults arrive as rows (fail-soft) and render as-is. */
  const runCorners = useCallback(
    (processes: string[]) => {
      cornerToken.current += 1;
      const token = cornerToken.current;
      setCornerRuns([]);
      setCornerPhase("RUNNING");
      log(`Corners: POST /corners/run [${processes.join(", ")}]`);
      void (async () => {
        let runs: CornerRun[];
        try {
          const out = await requestCorners(processes, 21);
          setBackendUp(true);
          runs = out.runs;
        } catch (err) {
          if (token !== cornerToken.current) return;
          setCornerPhase("IDLE");
          const msg = err instanceof ApiError ? err.detail : String(err);
          if (err instanceof ApiError && err.status === 0) setBackendUp(false);
          log(`Corners run failed: ${msg}`, "err");
          return;
        }
        if (token !== cornerToken.current) return;
        setCornerRuns(runs);
        const waves: Record<string, Waveforms> = {};
        for (const run of runs) {
          if (run.status !== "succeeded" || !run.job_id) {
            log(`Corner ${run.process}: ${run.status} — ${run.message.split("\n")[0]}`, "warn");
            continue;
          }
          try {
            waves[run.process] = await getWaveforms(run.job_id);
          } catch (err) {
            if (token !== cornerToken.current) return;
            log(
              `Corner ${run.process} wave read failed: ${err instanceof Error ? err.message : String(err)}`,
              "warn",
            );
          }
        }
        if (token !== cornerToken.current) return;
        setCornerWaves(waves);
        const first = runs.find((r) => waves[r.process] !== undefined);
        if (first) setLiveWave(waves[first.process]);
        setCornerPhase("DONE");
        const ok = runs.filter((r) => r.status === "succeeded").length;
        log(`Corners done: ${ok}/${runs.length} succeeded`);
        notify({
          title: "Corner sweep completed",
          body: `${ok}/${runs.length} corners live`,
          time: now().slice(0, 5),
          kind: ok === runs.length ? "PASS" : "WARN",
        });
        void refreshJobs();
      })();
    },
    [log, notify, refreshJobs],
  );

  /** Show one swept corner's wave in the analyzer (display routing only). */
  const showCorner = useCallback(
    (process: string) => {
      const wave = cornerWaves[process];
      if (wave) setLiveWave(wave);
      else log(`Corner ${process} has no wave (run the sweep first)`, "warn");
    },
    [cornerWaves, log],
  );

  /** Pre/post-layout comparison: one blocking POST (~2-3 min), table render.
   * Display only — every number arrives measured from the backend. */
  const runCompare = useCallback(() => {
    compareToken.current += 1;
    const token = compareToken.current;
    setCompareData(null);
    setComparePhase("RUNNING");
    log("Pre/Post: POST /postlayout/compare (canonical CS stage)");
    void (async () => {
      try {
        const out = await requestCompare(21);
        setBackendUp(true);
        if (token !== compareToken.current) return;
        setCompareData(out);
        setComparePhase("DONE");
        log(
          `Pre/Post done: DC ${out.pre.dc_gain.toFixed(2)}→${out.post.dc_gain.toFixed(2)} V/V, ` +
            `UGB drop ${(out.ugb_drop_frac * 100).toFixed(1)}%`,
        );
        notify({
          title: "Pre/post comparison completed",
          body: `UGB drop ${(out.ugb_drop_frac * 100).toFixed(1)}%`,
          time: now().slice(0, 5),
          kind: "PASS",
        });
      } catch (err) {
        if (token !== compareToken.current) return;
        setComparePhase("IDLE");
        const msg = err instanceof ApiError ? err.detail : String(err);
        if (err instanceof ApiError && err.status === 0) setBackendUp(false);
        log(`Pre/Post run failed: ${msg}`, "err");
      }
    })();
  }, [log, notify]);

  const startStudy = useCallback(() => {
    if (!demoCellId) {
      log("Optimize needs a completed simulation first — press Run", "warn");
      return;
    }
    studyToken.current += 1;
    const token = studyToken.current;
    setTrials([]);
    setStudyPhase("OPTIMIZING");
    log("Study: demo CS gain≥5 + UGBW≥1MHz, 3 trials (spec authored live)");
    void (async () => {
      let jobId = "";
      let sid = "";
      try {
        const spec = await createSpec(demoCellId, "demo-gain-bw", [
          { metric: "dc_gain", operator: ">=", threshold: 5.0 },
          { metric: "bandwidth", operator: ">=", threshold: 1e6 },
        ]);
        if (token !== studyToken.current) return;
        const out = await requestStudy({
          template_id: "common_source",
          spec_id: spec.spec_id,
          space: { w_n: [0.5e-6, 2e-6], w_p: [1e-6, 4e-6] },
          seed: 7,
          max_trials: 3,
          objective: "spec",
        });
        setBackendUp(true);
        jobId = out.job_id;
        sid = out.study_id;
      } catch (err) {
        if (token !== studyToken.current) return;
        setStudyPhase("IDLE");
        const msg = err instanceof ApiError ? err.detail : String(err);
        if (err instanceof ApiError && err.status === 0) setBackendUp(false);
        log(`Study failed to launch: ${msg}`, "err");
        return;
      }
      if (token !== studyToken.current) return;
      setStudyJobId(jobId);
      setStudyId(sid);
      log(`Study ${sid.slice(0, 8)}… running; polling trials`);
      const later = (fn: () => void, ms: number) =>
        timers.current.push(window.setTimeout(fn, ms) as unknown as number);
      const poll = async (): Promise<void> => {
        if (token !== studyToken.current) return;
        try {
          const [detail, rows] = await Promise.all([
            getJob(jobId),
            listTrials(sid).catch(() => [] as Trial[]),
          ]);
          if (token !== studyToken.current) return;
          setTrials(rows);
          if (
            detail.status === "succeeded" ||
            detail.status === "failed" ||
            detail.status === "cancelled"
          ) {
            setStudyPhase("DONE");
            const best = rows.reduce<Trial | null>(
              (b, t) => (b === null || t.score > b.score ? t : b),
              null,
            );
            log(
              `Study ${detail.status}: ${rows.length} trials` +
                (best ? `, best trial ${best.trial} score ${best.score.toExponential(2)}` : ""),
              detail.status === "succeeded" ? undefined : "warn",
            );
            void refreshJobs();
            return;
          }
        } catch (err) {
          if (err instanceof ApiError && err.status === 0) {
            setBackendUp(false);
            setStudyPhase("IDLE");
            log("Backend lost during study poll", "err");
            return;
          }
        }
        later(() => void poll(), 2000);
      };
      void poll();
    })();
  }, [demoCellId, log, refreshJobs]);

  const stopStudy = useCallback(() => {
    studyToken.current += 1;
    setStudyPhase("IDLE");
    log("Study cancelled by user (trials kept)", "warn");
    if (studyJobId) {
      const jid = studyJobId;
      void (async () => {
        try {
          const res = await cancelJob(jid);
          log(`Backend study ${jid.slice(0, 8)}… ${res.status}`);
          void refreshJobs();
        } catch (err) {
          log(
            `Backend cancel failed: ${err instanceof Error ? err.message : String(err)}`,
            "warn",
          );
        }
      })();
    }
  }, [log, studyJobId, refreshJobs]);

  useEffect(() => {
    void (async () => {
      try {
        await health();
        setBackendUp(true);
      } catch {
        setBackendUp(false);
      }
      await refreshJobs();
      const rows = await refreshCells();
      const first = rows.find((c) => !c.cell_name.endsWith("_anchor")) ?? rows[0];
      if (first) await selectCell(first.cell_id);
    })();
    return () => {
      runToken.current += 1;
      studyToken.current += 1;
      timers.current.forEach(clearTimeout);
    };
  }, [refreshCells, refreshJobs, selectCell]);

  const runDrc = useCallback(() => {
    setDrcDone(false);
    log("Running DRC: gpdk65.drc on ota_core");
    setJobs((j) => [
      {
        id: "drc_" + Math.floor(Math.random() * 900 + 100),
        type: "DRC",
        cell: "ota_core",
        host: "compute03",
        status: "Running",
        progress: 40,
        runtime: "00:04",
      },
      ...j,
    ]);
    window.setTimeout(() => {
      setDrcDone(true);
      setJobs((j) => j.map((x, i) => (i === 0 ? { ...x, status: "Complete", progress: 100 } : x)));
      log(`DRC complete: ${DRC_VIOLATIONS.length} violations, 3 rules`, "warn");
      notify({
        title: "DRC completed",
        body: "7 violations detected",
        time: now().slice(0, 5),
        kind: "FAIL",
      });
    }, 2200);
  }, [log, notify]);

  const value = {
    activeWs,
    setActiveWs,
    tabs,
    setTabs,
    openTab,
    closeTab,
    selection,
    setSelection,
    hierPath,
    setHierPath,
    tool,
    setTool,
    command,
    setCommand,
    annotate,
    setAnnotate,
    console_,
    setConsole,
    log,
    jobs,
    setJobs,
    refreshJobs,
    cells,
    refreshCells,
    activeCellId,
    activeSchematic,
    selectCell,
    createTemplateCell,
    liveWave,
    lastJobId,
    cornerRuns,
    cornerWaves,
    cornerPhase,
    runCorners,
    showCorner,
    compareData,
    comparePhase,
    runCompare,
    demoCellId,
    measuredGain,
    measuredBandwidth,
    backendUp,
    simPhase,
    setSimPhase,
    simProgress,
    outputs,
    setOutputs,
    ibias,
    setIbias,
    runSimulation,
    stopSimulation,
    studyJobId,
    studyId,
    trials,
    studyPhase,
    startStudy,
    stopStudy,
    drcDone,
    runDrc,
    setDrcDone,
    pexDone,
    setPexDone,
    postLayout,
    setPostLayout,
    lvsMismatch,
    setLvsMismatch,
    activeDrc,
    setActiveDrc,
    visibleLayers,
    setVisibleLayers,
    overlay,
    setOverlay,
    ratlines,
    setRatlines,
    dirty,
    setDirty,
    theme,
    setTheme,
    notifications,
    notify,
    bottomTab,
    setBottomTab,
    rightTab,
    setRightTab,
    railPanel,
    setRailPanel,
    panelsVisible,
    setPanelsVisible,
    statusMsg,
    setStatusMsg,
    zoom,
    setZoom,
  };
  return value;
}

type Store = ReturnType<typeof useStoreValue>;
const Ctx = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const value = useStoreValue();
  const memo = useMemo(() => value, [value]);
  return <Ctx.Provider value={memo}>{children}</Ctx.Provider>;
}

export function useStore() {
  const s = useContext(Ctx);
  if (!s) throw new Error("useStore outside provider");
  return s;
}
