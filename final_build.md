# **Open-Source AI-Native Analog IC Design Platform**

> **Implementation Readiness Patch (September 2026):** v3.2 preserves the v3.1 architecture and AI Expansion, but closes the seven load-bearing implementation gaps found in the final system audit: metric contracts, libngspice concurrency/isolation proof, statistical robustness protocol, reproducibility identity, CACE canonical-authority boundaries, AI data residency/privacy, and model-alias/config discipline. It also makes the end-user workflow and physical-backend technology spike explicit. No existing capability is removed. 

_Master Build Plan (v3.1) — A Virtuoso / Spectre Alternative_ 

**_What changed in v3.1_** _— one addition only: §12, a human-in-the-loop protocol for building this with heavy AI assistance. This is not a fifth architecture review — §11 already closed that loop, and nothing below in §0–§11 changed. This is an operating rule for the implementation phase: it takes the "Done when" criteria that already exist in §4 and gives them a concrete enforcement mechanism, so an AI coding agent has a literal, specified moment to stop and say "this needs your eyes" instead of silently marking a stage complete. Checkpoints are tagged inline below where they apply; §12 at the end defines the alert format and the full list._

**_Addendum — five implementation-level additions (compatible with v3.1)_** _— a subsequent review pass flagged five things worth making explicit before implementation, plus two small sequencing clarifications. None of it reopens §0–§11 or changes anything already written above: an explicit LLM provider abstraction (§1), a structured machine-readable schema for AI proposals (§2, §4 Stage 6), first-class provenance for AI-generated actions (§2), a fuller reproducibility/environment-hash definition (§2), and Design Engine API versioning (§3) — plus a Stage 5 / Stage 4.5 dependency note (§4) and a commit-level breakdown of the first concrete commit (§10). Each is marked **[ADDENDUM]** inline at the point where it applies._ 

## **What changed from v2, and a note on process** 

v2's core restructuring (headless loop before GUI) held up under a second, deeper review. What it was still missing: a canonical unit system, an explicit Design Engine API contract, a lightweight execution model for many simulation trials, hard/soft/weighted objectives (analog is a trade-off problem, not pure pass/fail), PVT/Monte Carlo as first-class rather than bolted on later, a failure taxonomy, and a corrected (tolerance-based, not byte-identical) equivalence test between the UI and the API. All of that is folded in below, each tagged [V0/V0.1 — build now] or [defer] so the document itself keeps the scope honest instead of reading as one long “must-add” list. 

One process note, stated plainly because it matters: this is the fourth consecutive review-and-revise pass. Each one caught something real. That streak will not run out on its own — a fresh review will always surface another defensible addition, because “more rigor” never has a natural ceiling in the abstract. The ceiling has to come from the builder. See §11. 

## **0. Product reframing (unchanged)** 

Build the design loop (spec → topology → sizing → simulation → measurement → optimization → verification) headlessly first. GUI is a client, built last. Target user: open-source-silicon designers, researchers, students in Sky130 — not “replace Virtuoso for professionals” as a v1 claim. 

## **1. Foundational decisions (updated)** 

- **PDK:** Sky130 first, behind a PDKAdapter interface. 

- **Simulator:** ngspice via libngspice, behind a Simulator interface. 

- **Layout:** KLayout primary, behind a LayoutBackend interface (Magic/Netgen as adapters). 

• **Execution model** [V0.1 — build now, scoped small]: a Job record (id, type, status, inputs, artifacts) and a simple local async task runner — not a distributed queue. It remains a **single-machine** runner, but v3.2 no longer assumes that libngspice jobs are safe to execute concurrently inside one process. Stage 2 must stress-test 1, 2, and 4 independent simultaneous simulations for state leakage, callback contamination, cleanup failures, crashes, and nondeterministic cross-run coupling. If the exact pinned libngspice wrapper does not pass, keep the same Job API and switch the execution backend to isolated worker **processes**. The abstraction survives; only the worker implementation changes. 

• **Units** [V0 — build now]: everything stored internally in SI base units (farads, ohms, Hz, volts, amps, seconds). Display formatting (“10 MHz”) is a UI-layer concern only, never the stored representation. This is a half-day of work now that prevents a category of bug that's expensive to retrofit later. 

- **Reproducibility:** Docker/Podman, pinned Sky130 + ngspice + KLayout + Python deps, `make setup &&` 

- `make test && make run-example` . 

• **AI architecture** (unchanged, sharpened further): the LLM is one client of the Design Engine (§3). It proposes; it never commits directly. 

- **LLM provider abstraction [ADDENDUM]:** the AI-architecture bullet above says the LLM is a replaceable client of the Design Engine — this is the interface that replaceability actually depends on, so it exists in code from the point the LLM is first called (Stage 5), not just as an architectural intention:

```
LLMProvider (abstract)
 ├── GeminiProvider
 ├── OpenAIProvider
 ├── LocalProvider      # self-hosted, e.g. a 7–8B model per Playbook §1.2/§1.4
 └── MockProvider       # deterministic, for tests — never hits a real API

methods: generate(), structured_generate(), embed()

metadata recorded per call: model, provider, prompt_version, temperature,
seed, token usage, timestamp, request id
```

  Every call into an LLM — Stage 5's explainer, Stage 6's topology proposer, the embeddings model once Stage 6's Knowledge Base retrieval exists — goes through this interface, never a bare SDK call inline in application code. This is what lets "swap Gemini for a local model" stay a config change instead of a rewrite, and it's also where the AIAction provenance record below gets its model_provider / model_name / model_version fields from.

## **2. Core data model (expanded)** 

- Project, Library, Cell/Schematic, Symbol, Instance, Port, Net, Parameter 

- Technology (PDK binding), ModelBinding 

- **Specification** — now explicit about the kind of target, not just “a target”: 

   - I hard constraints (must pass — e.g. gain ≥ 60 dB) 

   - I soft objectives (better-is-better — e.g. maximize bandwidth) 

   - I weighted objectives (e.g. a figure-of-merit combining gain × bandwidth / power) 

   - I each with tolerance and priority 

I each evaluated across nominal → PVT corners → Monte Carlo — not nominal-only. This is the single most important analog-specific correction in this round: a spec that only checks typical-case gain isn't a real spec. 

- Testbench, Analysis, Job (new — see §1) 

- **SimulationRun** — netlist, versions, inputs, raw output, and three deliberately separate reproducibility concepts:

  1. **design_identity_hash** — SHA-256 of a canonical encoding of the normalized netlist plus the logical simulation configuration that defines the requested experiment. This answers: *is this the same design/test intent?*
  2. **execution_environment_hash** — SHA-256 of a canonical encoding of simulator version/build, PDK version, model-file hashes, container image digest, relevant backend/library versions, and analysis implementation version. This answers: *did it run in the same tool environment?*
  3. **comparison_policy_id** — a versioned tolerance/comparison policy. Numerical tolerance is **not** part of the circuit's identity; it is the rule for deciding whether two numerical outputs are equivalent enough for a given regression.

  Persist a full canonical run record and derive `reproducibility_id = SHA256(canonical_encode({design_identity_hash, execution_environment_hash, random_seed, analysis_settings}))`. Store the comparison policy alongside the run, but do not confuse it with design identity. Simulator output is compared numerically under that policy; it is never required to be byte-identical. 

- **Measurement** — structured metric results with pass/fail per Specification.

- **MetricContract [V0.1 — Stage 3, mandatory before implementation]:** the canonical definition of what each metric means and how it is legally measured. Each contract stores at least: `metric_id`, semantic definition, required `Analysis` type, required testbench capability, stimulus, observed nodes/ports, formula, sign convention, SI units, extraction window, reference condition, interpolation/crossing rule where relevant, invalid-data behavior, comparison policy, and golden-fixture ID. The same named metric must not mean different things in different subsystems.

- Experiment/OptimizationRun — one row per trial (see §5) 

- Constraint, DesignRevision (table exists now; branching/diff UI deferred — see §5, §7), **ErrorRecord** with a failure taxonomy [V0.1 — build now, it's just an enum]: Syntax → Schema → Netlist → SPICE convergence → Operating point → Constraint → PVT → Monte Carlo → DRC → LVS → PEX → Post-layout performance. Classifying which kind of failure something is, is what lets the Stage 5 explainer say “this is a bias-point headroom problem” instead of “simulation failed.” 

- Artifact (pointer to on-disk file) 

- **AIAction [ADDENDUM — provenance, wired up starting Stage 5/6]:** every AI-generated action — an explanation, a topology proposal, a sizing suggestion — gets its own row, separate from the Experiment Ledger and ErrorRecord tables it may reference:

```
AIAction
- id
- action_type            # e.g. explain_failure, propose_topology, propose_sizing
- model_provider          # from LLMProvider, §1 addendum
- model_name
- model_version
- prompt_version
- input_context_hash
- output_hash
- source_artifacts        # ErrorRecord / Measurement / Experiment IDs it drew on
- resulting_design_revision   # if it led to one
- human_decision          # accept / reject / edited / n/a
- timestamp
```

  This is what answers "why did this design exist," "which model produced the bad topology," and "did results improve after prompt v17" — questions the Experiment Ledger alone can't answer once more than one model or prompt version is in play. A minimal version is fine to start; the point is that it exists from the first AI action onward, not retrofitted later.

**Validation gate** (unchanged from v2, still correct): nothing — human-entered or AI-proposed — reaches ngspice without passing schema + connectivity + unit + model-binding checks first. 

## **3. The Design Engine API [V0.1 — build now]** 

This was implicit in v2 (“the LLM is one client,” “the GUI is one more client”) but never written down as an actual contract. Writing it down now, because it's what makes every later “X is just a client of the engine” claim true instead of aspirational: 

```
create_project() create_cell() instantiate()
validate() netlist() simulate()
check_constraints() optimize() run_drc()
extract() compare()
```

CLI, Python API, GUI (Stage 7), and the AI copilot (Stage 5–6) are all callers of this surface — none of them get a private side door into ngspice, KLayout, or the schema. This is a bigger architectural decision than React-vs-Qt, and it's the one to get right first. 

**[ADDENDUM] API versioning:** because every client (CLI, Python API, GUI, AI copilot) depends on this exact surface, treat it as a versioned protocol rather than "whatever functions happen to exist this week" — call it `DesignEngine v0.1` starting at Stage 0. Rule: additive changes (new optional parameters, new methods) don't bump the major version; anything that changes an existing method's signature or behavior does, and ships with a migration note in the same commit. Record `engine_api_version` alongside SimulationRun and AIAction rows so a design revision's provenance includes which contract produced it. This matters most once Stage 6's AI copilot and Stage 7's GUI are both calling the same engine — without a version discipline, they can silently drift into depending on incompatible assumptions about the same function.

## **4. Stage-by-stage plan** 

### **Stage 0 — Architecture & Packaging [build now]** 

Docker image, pinned versions, CI smoke test, interface stubs (Simulator, LayoutBackend, PDKAdapter), the Design Engine API skeleton (§3, empty implementations). **Done when:** fresh clone + `make setup && make test` passes with zero manual steps. 

### **Stage 1 — Circuit Kernel [build now]** 

Schema (§2 minus Measurement/Experiment), netlist compiler, pre-sim validator, unit system live from the start. **Done when:** an NMOS instance compiles to a netlist matching a hand-written golden reference, byte-for-byte (netlists should be byte-identical — it's simulation output that shouldn't be). **[** I **HUMAN CHECKPOINT — see §12]** 

### **Stage 2 — Simulation Kernel [build now]** 

Simulator interface, NgspiceBackend, the Job runner from §1, and the v3.2 reproducibility contract. **Done when:** (a) the hand-built inverter runs through libngspice via a Job and returns a transient waveform entirely from schema data; **and** (b) a concurrency/isolation harness runs 1-, 2-, and 4-job workloads repeatedly and proves no cross-run state leakage, callback mix-ups, crash/cleanup corruption, or nondeterministic contamination. If the pinned shared-library integration fails that test, Stage 2 is still successful only after the Job executor is moved behind process isolation without changing the public Job/Simulator contract. **[** I **HUMAN CHECKPOINT — see §12]**

### **Stage 3 — Measurement & Specification Engine [build now]** 

Build the **Metric Contract + Analysis/Testbench Matrix first**, then implement measurements one contract at a time. `gain`, `bandwidth`, `phase margin`, `slew rate`, `power`, `offset`, and `settling time` are not generic waveform functions and must never share an implied test condition. Minimum canonical matrix:

| Metric | Required analysis | Canonical benchmark/testbench intent |
|---|---|---|
| DC / small-signal gain | DC/AC as declared by the contract | amplifier / differential amplifier |
| Bandwidth | AC | amplifier with declared gain reference and crossing rule |
| Phase margin | loop-gain / return-ratio analysis | a defined closed-loop feedback benchmark, **not** a current mirror |
| Slew rate | large-signal transient | closed-loop or declared step-response benchmark |
| Power | operating-point and/or transient average | circuit-specific supply-current convention and time window |
| Offset | DC and, when claimed, mismatch/MC | differential-input benchmark with declared methodology |
| Settling time | transient | closed-loop step with declared final-value estimator and error band |

Every metric has a formal definition, sign convention, units, required nodes/stimulus, invalid-data behavior, and a golden hand-check fixture. **Done when:** each MetricContract is individually hand-verified on an appropriate benchmark; no metric is accepted merely because it ran on the current-mirror/differential-pair fixtures. **[** I **HUMAN CHECKPOINT — see §12]**

### **Stage 4 — Optimization Layer [build now]** 

Optimizer interface, Optuna first. Every trial writes to the Experiment Ledger (§5) as a Job. Evaluated across nominal first, PVT corners next (Monte Carlo can wait for Stage 4.5 below). **Done when:** the common-source amplifier gets sized against a real spec via real simulations, reproducibly. This is still your first demoable product, before any GUI. 

### **Stage 4.5 — Robustness [V0.2, not V0.1]** 

Extend Stage 3/4 to evaluate PVT corners and Monte Carlo, not just nominal. This is what a Specification promises in §2 but Stage 4 alone doesn't deliver — don't skip it, but it is the next increment after nominal sizing works, not a parallel Stage 0 task. **Done when:** the two-stage Miller op-amp produces a reproducible robustness report under a **declared statistical protocol** containing, at minimum: sample count `N`, random seed(s), corner set, supply/temperature set, process-vs-mismatch variation mechanisms actually supplied by the PDK/model, sampling method, metric threshold, pass count, yield estimate, and a confidence interval or explicitly justified uncertainty statement. A sentence such as “95% pass” may appear only as an observed benchmark result, never as the universal acceptance target. **[** I **HUMAN CHECKPOINT — see §12]**

### **Stage 5 — AI Diagnostics & Copilot [build now, after Stage 4]** 

• Structured error explainer, built on the failure taxonomy from §2 — classify first, explain second. 

• Optimizer-result narration, grounded in real Stage 3/4 measurements. **Done when:** a failed convergence run and a completed optimization run each get a correct, data-grounded plain-English explanation. 

• **[ADDENDUM] Dependency note:** Stage 5 may begin as soon as Stage 4 is verified — it doesn't need to wait for Stage 4.5. But its explanations are only as complete as the ErrorRecords it can cite: until Stage 4.5 exists, it's correctly grounded only in nominal-run failures, not PVT/Monte Carlo ones. Production-quality robustness-aware explanations ("this fails at the SS corner but not TT") require Stage 4.5 to be built first. Don't let the explainer narrate a PVT/MC failure it has no ErrorRecord for in the meantime — the grounding rule already forces the correct behavior here (refuse rather than guess); this note just explains why that refusal will fire until 4.5 lands. 

### **Stage 6 — Topology Intelligence (Design Knowledge Base) [V0.2+]** 

Merges what were two separate ideas (a “topology library” and an “experiment ledger”) into one: a small set of known topologies (current mirror, diff pair, common-source, cascode, folded cascode, 2-stage Miller) each with a schematic template, parameters, constraints, known trade-offs — plus every historical experiment run against it, successful and failed. The AI searches this, fills a template, never invents connectivity from scratch. AI proposal workflow, now explicit (this was a sentence in v2, it's a real gate now): 

`AI proposes` → `schema validation` → `simulate` → `check_constraints` → `human approval (accept / reject / compare)` → `commit` 

AI never silently overwrites the current design. **Done when:** “design a 2-stage Miller op-amp, 60dB gain, 40MHz UGB” produces a template instantiation that passes validation, simulates, gets sized by Stage 4, and sits as a proposal awaiting your accept/reject. **[** I **HUMAN CHECKPOINT — see §12]** 

**[ADDENDUM] Structured proposal schema:** "AI proposes" above means AI returns one specific machine-readable object — the core system never parses prose to extract a proposal:

```json
{
  "topology_id": "two_stage_miller_v1",
  "parameters": {
    "w1": 2.0e-6,
    "l1": 5.0e-7,
    "w2": 8.0e-6
  },
  "reasoning": "...",
  "evidence_ids": ["EXP-102", "EXP-117"],
  "requested_spec_id": "SPEC-42"
}
```

  `topology_id` must resolve to a known template (§5 — no free-form connectivity, this is already the rule above); `evidence_ids` point at real Experiment Ledger rows, same grounding discipline as Stage 5. This object — not the reasoning prose — is what schema validation actually validates. Every proposal also writes an AIAction row (§2 addendum) before it reaches the human-approval gate, so accept/reject/compare has provenance attached. Template-only proposal generation (rather than free connectivity synthesis) is the right V1 scope, not a placeholder — novel topology exploration is explicitly a V2/V3 capability per §8's version ladder, not something missing from V1. 

### **Stage 7 — Schematic UI [V0.4]** 

One more client of the Design Engine API (§3). Corrected acceptance test: **Done when:** a design built in the UI and the same design built via the Python API produce matching netlist hashes and simulation results within defined numerical tolerance — not byte-identical output. This is also where DesignRevision branching/diffing (deferred from §2) becomes genuinely useful, since now there's something to visually diff against. 

### **Stage 8 — Physical Design [V0.5]** 

Before committing to KLayout as the primary physical implementation backend, run a **technology spike** through the existing `LayoutBackend` abstraction: one transistor/device → programmatic geometry → DRC → extraction → LVS → PEX → pre/post-layout simulation comparison. Record which backend performs each step. If KLayout is strong for viewing/geometry but Magic/Netgen is materially more reliable for a verification/extraction operation, use the better adapter rather than forcing one tool to own the whole flow. Then continue incrementally: viewer → geometry model → import → basic PCells → placement → DRC → LVS → extraction/PEX. **Done when:** the technology spike is reproducible and one benchmark circuit passes the defined physical-verification checks cleanly end to end. **[** I **HUMAN CHECKPOINT — see §12]**

### **Stage 9 — Post-Layout Physical Verification Loop [V0.5]** 

Post-layout parasitics feed back into Stage 3's measurement engine; pre- vs. post-layout deltas reported side by side. 

### **Stage 10 — Expansion [V2.0 / V3.0 — see §8]** 

Multi-PDK, AI-assisted layout/placement, surrogate models, RF/EM, cloud collaboration. Sandboxing becomes a real requirement starting here — once AI-generated netlists or third parties can trigger jobs without a human in the loop, isolate execution (resource limits, timeouts, no unnecessary network access). Not a Stage 0 concern for a single-user local tool; a hard requirement before any cloud/multi-user feature ships. 

## **5. The Design Knowledge Base — your actual moat (merged §5+§9 from prior reviews)** 

Every simulation and optimization trial, success or failure, logs to the Experiment Ledger from Stage 2 onward — parameters, measurements, verdict, reproducibility hash. Once Stage 6 exists, topology templates link to their own historical experiments (which sizings worked, which didn't, for which spec). The LLM, the optimizer, even ngspice are all replaceable. A growing, structured, reproducible library of Sky130 design experience tied to one validated schema is not something a competitor bolts on after the fact — and it's specifically what point-solution research tools (AnalogCoder-Pro, AaLLM, TopoSizing) don't have, because they're evaluated per-paper on fixed benchmarks, not as a running system that accumulates its own history. 

## **6. Benchmark ladder, now with a robustness dimension** 

|**Level**|**Circuit**|**Evaluated across**|
|---|---|---|
|0|CMOS inverter|Nominal|
|1|Current mirror, differential pair|Nominal→PVT|
|2|Common-source amp, cascode amp|Nominal→PVT→Monte Carlo|
|3|Two-stage Miller op-amp|Nominal→PVT→Monte Carlo→Layout + PEX|
|4|OTA / comparator / LDO|(V2.0)|
|5|Bandgap / VCO|(stretch, later)|



## **7. Positioning (updated with verified current research)** 

Two real 2026 systems are worth knowing about specifically: AnalogCoder-Pro (topology generation + Bayesian-optimization sizing with a multimodal diagnosis-and-repair loop, benchmarked on 13 circuit types) and AaLLM (open-source multi-agent topology+sizing workflow with a RAG-based knowledge base). Both are real, both are legitimate, both operate on a single design at a time with no persistent, growing, validated substrate underneath them. 

**Revised claim:** the opportunity isn't “we do AI topology+sizing” — that's now a populated research area. It's a reproducible, validated design engine (§3) with a growing knowledge base (§5) that AI methods — including ones like these — could plug into, rather than a fresh one-shot generation every time with no memory of what already failed. 

|**Existing approach**|**Strength**|**Weakness**|
|---|---|---|
|Xschem + ngspice|Open, mature|Fragmented UX, no shared data model|
|KLayout / Magic / Netgen|Strong open physical flow|Not one integrated environment|
|CACE|Real characterization automation|Not a complete design environment|
|AnalogCoder-Pro / AaLLM|Real end-to-end topology+sizing research|Per-design, no persistent validated<br>substrate|
|Commercial EDA|Extremely mature, AI already added|Expensive, proprietary, AI retrofitted<br>onto old workflows|
|This platform|Unified loop + growing knowledge base + AI<br>constrained by validation|Initially limited PDK/circuit coverage|



## **8. Version ladder (rescoped — V1.0 tightened, not expanded)** 

- **V0** — Engineering proof: Stages 0–2, inverter only, Docker + regression test. 

• **V0.1** — Circuit engine: Stages 1–3 fleshed out, all Level 0–1 benchmarks, Design Engine API complete for headless use, no GUI. 

- **V0.2** — Optimization + robustness: Stage 4 + 4.5, Level 2 benchmarks, Experiment Ledger live. 

- **V0.3** — AI copilot: Stage 5. 

• **V0.4** — Schematic editor + topology intelligence: Stage 6 + Stage 7 (built together makes sense — the human-approval workflow in Stage 6 needs some visual surface to approve against, even a minimal one). 

- **V0.5** — Physical design + post-layout physical verification: Stage 8 + 9. 

• **V1.0** — First real, coherent product: everything above, integrated: Sky130 → spec → topology → sizing → simulation → measurement → optimization → schematic → layout → DRC/LVS → PEX → post-layout verification, with AI assistance throughout. Not autonomous AI layout, not multi-PDK — those are explicitly out of V1.0 scope now, per this round's correction. 

• **V2.0:** GF180/IHP via PDKAdapter, Level 4 benchmarks, surrogate models, larger Knowledge Base, AI-assisted layout, sandboxed execution (required once this ships to more than one user). 

- **V3.0:** autonomous topology exploration, advanced placement/routing, RF, collaboration. 

## **9. Tooling (unchanged from v2, still correct)** 

Simulation: ngspice/libngspice (+Xyce later) behind Simulator. Layout: KLayout (+Magic/Netgen) behind LayoutBackend. **Characterization: the Design Engine's `Specification` + `MetricContract` + `Measurement` model is canonical; CACE is integrated as an adapter/import-export/execution bridge, never as a second source of truth for metric definitions or acceptance limits.** PDKs: Sky130 first, behind PDKAdapter. Optimization: Optuna first. Orchestration: plain functions for Stage 5, one framework (LangGraph) once Stage 6 needs real multi-step reasoning. LLM: local or hosted via LLMProvider, always optional. Testing: pytest + golden-netlist regression + CI from Stage 0.

## **10. First concrete commit (unchanged — still the right size)** 

SQLite schema subset + hand-built inverter + netlist compiler + libngspice call + waveform parse + one measurement function + one pytest regression test + Dockerfile. Add the unit system and the Job/ErrorRecord shape now since they're cheap — skip everything else tagged [defer] above. 

**[ADDENDUM] Commit-level breakdown:** the paragraph above describes the right *scope* for "first concrete deliverable," but don't land it as one literal git commit — split it so each piece is independently debuggable and revertible:

```text
Commit 1 — bootstrap (Dockerfile, Makefile, CI smoke test)
Commit 2 — interface stubs + Design Engine API skeleton (§3)
Commit 3 — SQLite schema (unit system + Job/ErrorRecord shape included)
Commit 4 — hand-built inverter + netlist compiler
Commit 5 — libngspice integration
Commit 6 — waveform parser
Commit 7 — first measurement function + pytest regression
```

  This lines up with Stage 0 → Stage 1 → Stage 2 → Stage 3 as already sequenced in §4, and matches the Playbook's "one task = one commit = one testable claim" rule (Playbook §0) — same scope, just not compressed into a single commit. 

## **11. On when to stop planning** 

Three rounds of AI review have each found something real. That's a genuine, useful signal — it means the plan was worth pressure-testing. It is not, however, a signal that a fifth round will find something equally load-bearing. Architecture review has no natural endpoint in the abstract; the endpoint has to be declared. Declaring it here: the plan is done. §0–§10 is buildable as written. The next artifact that will teach you more than another critique is a failing test from actual libngspice output on your actual inverter. Build Stage 0 and Stage 1 before asking anything — human or AI — to review this document again. 

## **12. Human-in-the-loop protocol (mandatory for AI-driven builds) [NEW — v3.1]** 

If most of this codebase gets written by an AI agent from this document, the risk isn't that the agent writes code that crashes — crashes are self-announcing. The risk is code that runs, produces a plausible-looking number, and is quietly wrong: a netlist with a swapped node order that still simulates, a measurement formula that's off by a sign convention, a PCell that's geometrically non-physical but LVS-clean. None of these throw an exception. This section defines the specific points where the agent must stop, alert you, and wait — rather than mark a stage “done” on its own judgment. 

### **Operating rule** 

**Default to flagging over guessing.** Any time the agent is about to trust output in a category below for the _first time_ — first golden reference, first instance of a given measurement formula, first clean DRC/LVS pass, first use of a new PDK construct — it stops and raises a checkpoint instead of proceeding. Once a specific pattern has been human-verified once, the agent does not need to re-flag every subsequent run of that _same, already-validated_ pattern — only new ones, or anomalous results from old ones. Flagging everything forever is as useless as flagging nothing; the point is to catch each new kind of thing exactly once. 

### **Alert format** 

When a checkpoint triggers, the agent's output should look like this — literally, not paraphrased — so it's unmistakable in a wall of build logs: 

I `HUMAN CHECKPOINT — <Stage / Component> Trigger: <what specifically caused this stop> Check: <the exact, concrete thing to verify — not "review this"> Status: BLOCKING — not proceeding until you confirm.` 

### **Mandatory checkpoints** 

|**Stage / Component**|**Trigger**|**What you must verify**|**Type**|
|---|---|---|---|
|Stage 1 — Netlist<br>compiler|Golden reference netlist is created<br>and first compiler output is compared<br>against it|The golden reference itself is<br>electrically correct — by hand, before<br>it's trusted as ground truth for every<br>future comparison|Blocking|
|Stage 2 — First<br>simulation|First transient waveform returned<br>from libngspice for the inverter|Waveform shape and values are sane<br>for a hand-built inverter, before this run<br>becomes the template other<br>testbenches copy|Blocking|
|Stage 3 —<br>Metric contracts & formulas|First implementation of each MetricContract and its metric function|Definition, required analysis/testbench, sign convention, units, raw data, and result match the metric-specific golden hand calculation; generic current-mirror/diff-pair reuse is not accepted|Blocking|



|**Stage / Component**|**Trigger**|**What you must verify**|**Type**|
|---|---|---|---|
|Stage 4 — Optimizer<br>results|A trial result sits at a search-space<br>boundary, or converges suspiciously<br>fast|The spec/constraint wasn't mis-scoped<br>in a way that let the optimizer find a<br>degenerate “solution”|Advisory|
|Stage 4.5 —<br>Robustness claims|Any headline statement like “X% of<br>Monte Carlo samples pass”|Underlying sample count and corner<br>distribution — small N can produce a<br>misleadingly clean percentage|Blocking|
|Stage 5 — AI<br>explanations|An explainer narrates a failure or<br>optimizer result|The explanation cites an actual<br>ErrorRecord/Measurement it can point<br>to; if it can't, it says so instead of<br>narrating a plausible story|Advisory|
|Stage 6 — AI design<br>proposals|Any AI-proposed topology<br>instantiation or sizing, every time|Accept / reject / compare — this gate<br>already exists in §2; this row just<br>makes it non-negotiable, never<br>auto-committed even when all checks<br>pass|Blocking|
|Stage 8 —<br>DRC/LVS/PCells|First clean DRC+LVS pass on a<br>benchmark circuit|Visual review in the KLayout viewer<br>before the PCell generator is trusted<br>for reuse on other cells|Blocking|
|Cross-cutting —<br>PDK/model syntax|Agent is about to write Sky130<br>model-binding or device syntax not<br>already validated once against the<br>actual PDK docs|Confirm syntax against PDK reference<br>rather than model memory — PDK<br>conventions are niche enough to be a<br>real hallucination risk|Blocking|



_This table is the canonical definition of the [_ I _HUMAN CHECKPOINT] tags placed inline in §4 above. It's an operating rule for the build phase, not new scope — it doesn't reopen §0–§11._ 



---

# **13. AI Feature Expansion Addendum — September 2026 [ADDITIVE; DOES NOT REMOVE OR REORDER §§0–12]**

This addendum expands the AI product roadmap without changing the architectural law, stage ordering, or V1 correctness gates already defined above. The existing plan remains intact. The new rule is:

> **AI may compress engineering work, propose choices, organize evidence, and predict where to look next. Deterministic software still validates; ngspice/DRC/LVS/PEX still decide physical truth; a human still promotes trusted design changes.**

The point is not to bolt a chatbot onto EDA. The point is to make the Experiment Ledger + validated Design Engine progressively smarter while preserving a hard boundary between **prediction/proposal** and **ground truth**.

## **13.1 What the proposed Gemini roadmap got right — and what is corrected here**

The ten proposed features are directionally strong, but three need stricter implementation than a generic AI roadmap implies:

1. **Surrogate models never become signoff.** They may rank or prune candidates, but selected candidates must still be verified by real SPICE, and out-of-distribution predictions must automatically fall back to simulation.
2. **PDK porting is not "scale by Lmin ratio."** A useful porting assistant maps device intent and operating points — gm/Id, inversion region, Vov/headroom, current density, intrinsic gain, capacitances, matching area, voltage limits — into a target-PDK starting point, then re-optimizes and verifies in the target PDK.
3. **A screenshot is not DRC/LVS truth.** The multimodal debugger consumes structured DRC markers, rule IDs, LVS mismatch records, layer/net metadata, and extracted geometry first. Images are supplementary context. It must never invent a rule such as "poly.5" from pixels alone.

The original proposal's "99% fail / 1% pass" autonomous-topology wording is also treated as an illustration, not a target. The system records measured pass rates instead of hard-coding an assumed success percentage.

## **13.2 AI product roadmap — mapped onto the existing stages**

| ID | Capability | Existing/new | Earliest integration | Product release | Trust boundary |
|---|---|---|---|---|---|
| AI-01 | Grounded Error Explainer | Existing, strengthened | Stage 5 | V0.3 | Every factual claim cites ErrorRecord / Measurement / Artifact IDs or refuses |
| AI-02 | Optimizer-Result Narration | Existing, strengthened | Stage 5 | V0.3 | Pareto/trade-off math is deterministic; LLM only explains |
| AI-03 | Template-Based Topology Proposer + KB RAG | Existing, strengthened | Stage 6 | V0.4 | Known topology_id only; schema validation + simulation + human approval |
| AI-04 | Conversational Spec-to-Constraint Generator | New | Stage 5 after Stage 3 schema is stable | V0.3/V0.4 | Produces a draft, surfaces assumptions/ambiguities, human confirms before activation |
| AI-05 | Multi-Objective Pareto Analyst | New | Stage 4/5 | V0.3 enhancement | Pareto front computed by code; AI narrates only verified points |
| AI-06 | Surrogate Modeling for Fast Sizing | Expanded Stage 10 | Post-V1 | V2.0 | Prediction cannot satisfy a spec; SPICE verifies every promoted design |
| AI-07 | PDK Porting Assistant | Expanded Stage 10 | After second PDK adapter works | V2.0 | Intent-aware mapping; target-PDK validation + optimization mandatory |
| AI-08 | Multimodal DRC/LVS Debugger | New physical-design copilot | After Stage 8 | V2.0 | Structured markers/reports are primary evidence; image is secondary |
| AI-09 | AI-Assisted Placement Clustering | Expanded Stage 10 | After placement constraints exist | V2.0 | AI proposes constraints/groups; deterministic placer/layout engine produces geometry |
| AI-10 | Autonomous Topology Exploration | Existing V3 concept, strengthened | Post-V2 | V3.0 | Candidate IR -> validators -> isolated sandbox -> simulator -> human promotion |

**Scope rule:** AI-04 and AI-05 are intentionally lightweight additions around systems already needed for V1. They must not delay Stages 0–4. AI-06 through AI-10 remain post-V1 unless the core engine is already passing its benchmark ladder.

## **13.3 Detailed feature contracts**

### **AI-01 — Grounded Error Explainer 2.0**

Inputs: classified ErrorRecord, linked Measurement rows, Specification rows, relevant waveforms/artifacts, operating-point values, PVT/MC context when available.

Output is structured before prose:

```json
{
  "failure_class": "operating_point",
  "summary": "...",
  "evidence_ids": ["ERR-91", "MEAS-440", "ART-221"],
  "supported_findings": ["..."],
  "unknowns": ["..."],
  "next_diagnostic_tests": ["..."],
  "confidence": "high|medium|low"
}
```

A "next diagnostic test" is a proposal, not a diagnosis. It must name exactly what Design Engine call or measurement would resolve the uncertainty. The LLM may not fabricate a root cause merely because one is typical.

### **AI-02 — Optimizer-Result Narration + Design Trade-off Explainer**

The optimizer, measurement engine, and Pareto code produce the numbers. The AI explains:

- which objectives improved or regressed;
- which constraints are active/binding;
- which parameters moved most;
- which points are Pareto-dominated vs non-dominated;
- where results sit relative to PVT/MC yield;
- whether the apparent win is suspiciously at a search-space boundary.

Never let the model calculate the authoritative Pareto set itself.

### **AI-03 — Template-Based Topology Proposer + Evidence Retrieval**

Extend the existing Stage 6 proposal with retrieval over:

- validated topology templates;
- successful and failed Experiment rows;
- matching Specification shapes;
- PVT/MC results;
- later, post-layout outcomes.

The retrieval layer should prefer **experiment similarity + validated outcome** over semantic text similarity alone. The proposal must cite the historical experiments that support its initial parameters and also retrieve relevant failures so the system does not repeatedly rediscover known dead ends.

### **AI-04 — Conversational Spec-to-Constraint Generator**

Natural-language requirements become a **draft Specification**, never an immediately active one.

Required output fields:

```json
{
  "requested_function": "...",
  "constraints": [],
  "soft_objectives": [],
  "weighted_objectives": [],
  "assumptions": [],
  "ambiguities": [],
  "missing_inputs": [],
  "source_text_hash": "...",
  "needs_human_confirmation": true
}
```

Rules:

- no silent default for supply voltage, load, input common-mode range, process corner, temperature, output swing, stability condition, or measurement definition;
- detect contradictory requirements and impossible unit combinations before creating a Specification;
- show the exact normalized SI values the Design Engine will store;
- human confirmation is mandatory before the draft becomes an active Specification.

### **AI-05 — Multi-Objective Pareto Analyst**

Build a deterministic Pareto service on top of Experiment/OptimizationRun data. The AI may narrate the front and answer questions like "what do I give up to get another 20 MHz?" but the underlying front, yield values, and interpolation points are produced by code.

Add a saved `ParetoSnapshot` artifact containing objective definitions, trial IDs, dominance relation, PVT/MC filter, and environment hashes so a later explanation is reproducible.

### **AI-06 — Surrogate Modeling for Fast Sizing**

Surrogates are **accelerators**, not alternate simulators. Support Gaussian-process/Bayesian models first for small data; lightweight neural/regression models only when the dataset justifies them.

Every prediction records:

```text
model_id, training_data_hash, feature_schema_version,
predicted_mean, uncertainty, applicability_domain,
in_domain, calibration_metrics, created_at
```

Mandatory gates:

- held-out error and calibration benchmark before use;
- OOD detector / applicability-domain check;
- uncertainty threshold above which the system runs SPICE instead;
- every candidate that is promoted to a real design is verified by SPICE;
- surrogate-assisted optimization reports simulated-vs-predicted error so the model can improve from its own misses.

### **AI-07 — PDK Porting Assistant**

Porting workflow:

```text
source validated design
-> extract device intent + operating points
-> map device classes and legal voltage domains
-> propose target-PDK starting sizing
-> target-PDK schema/model validation
-> target-PDK SPICE
-> re-optimize
-> PVT/MC verify
-> human compare/approve
```

Never treat geometry scaling alone as a port. Preserve or intentionally trade off circuit behavior using target-PDK model data.

### **AI-08 — Multimodal DRC/LVS Debugger**

Evidence priority:

1. DRC rule ID + marker geometry + layer names;
2. LVS mismatch graph / device-net correspondence;
3. Design intent and matching constraints;
4. extracted geometry/net metadata;
5. rendered KLayout image as visual context.

Output: evidence-linked diagnosis, highlighted regions, and one or more **candidate ECOs**. Candidate ECOs are proposals only and must re-run DRC/LVS before they can be accepted.

### **AI-09 — AI-Assisted Placement Clustering**

The AI interprets schematic intent and proposes `LayoutConstraint` objects such as:

- symmetry pairs;
- common-centroid groups;
- matched-device groups;
- proximity groups;
- keep-apart / noise-isolation groups;
- orientation constraints;
- guard-ring / well / substrate-contact requirements when supported by verified PDK rules;
- high-impedance / high-swing / sensitive-net annotations.

The AI does **not** directly draw final geometry. Placement/routing remains deterministic and DRC/LVS-verified.

### **AI-10 — Autonomous Topology Exploration (sandboxed research mode)**

This is not a bypass around Stage 6. It is a separate experimental pipeline:

```text
LLM / search policy proposes CandidateCircuitIR
-> graph/schema/connectivity/unit/model checks
-> static analog sanity checks
-> isolated netlist compilation
-> sandboxed SPICE with hard resource limits
-> measurements + constraints
-> novelty/dedup check against Knowledge Base
-> log as experimental candidate
-> human review
-> only then promote to a trusted topology template
```

There is still no direct `LLM -> trusted SPICE/netlist` path. Raw generation terminates in a restricted circuit IR that the same Design Engine validators compile.

## **13.4 Additional AI features worth adding beyond the original ten**

### **AI-11 — Spec Completeness & Contradiction Auditor [V0.3+]**

Before optimization, detect missing test conditions, conflicting hard constraints, unit mistakes, underspecified stability/loading conditions, and specs that cannot be measured by the currently registered Measurement implementations. Output a checklist, not guessed defaults.

### **AI-12 — Active-Learning Experiment Planner [V0.4/V2]**

Given the current uncertainty, optimization history, and simulation budget, propose the next most informative simulations. This can reduce wasted sweeps and becomes especially powerful with surrogate models. The planner proposes jobs; the deterministic scheduler enforces budget and executes them.

### **AI-13 — Sensitivity & Bottleneck Explainer [V0.3+]**

Use actual perturbation/sensitivity runs to explain which device parameters most affect gain, bandwidth, PM, power, offset, and yield. The AI narrates measured sensitivities; it does not infer derivatives from prose.

### **AI-14 — Yield / Corner Risk Scout [V2]**

Predict where robustness is likely to fail and prioritize corners/Monte Carlo regions for real simulation. It may triage simulation effort, but a predicted yield is never reported as a signoff yield.

### **AI-15 — Regression & Design-Revision Reviewer [V0.4+]**

When a commit or DesignRevision changes a circuit, explain which measurements moved, which constraints changed state, what new failures appeared, and which parameter/net/layout change is correlated with the regression. This turns provenance into a daily engineering tool.

### **AI-16 — Testbench & Measurement Coverage Assistant [V0.3+]**

Given a confirmed Specification, propose missing analyses/testbenches and map each hard constraint to the Measurement implementation that proves it. Any generated testbench still passes the same schema/unit/model-binding gate and its first new measurement pattern triggers the existing human checkpoint.

### **AI-17 — PEX / Parasitic Root-Cause + ECO Assistant [V2]**

Compare pre-layout vs post-layout results, associate degradation with extracted parasitics/nets, rank likely contributors, and propose ECOs such as shortening a sensitive route or moving a device cluster. Re-extraction + simulation decides whether the ECO helped.

### **AI-18 — Knowledge-Base Curator / Failure-Pattern Miner [V0.4+]**

Mine repeated validated successes/failures into candidate design heuristics: "these sizing regimes repeatedly violate PM under SS/high-temp". Candidate heuristics remain tagged as learned observations until enough evidence exists and a human promotes them to reusable rules.

### **AI-19 — Read-Only Natural-Language Query over the Experiment Ledger [V0.4+]**

Let a user ask: "show every folded-cascode run that met 70 dB gain under SS and used under 1 mW." The LLM produces a constrained query plan; a deterministic query layer executes it. It is read-only and returns trial IDs, measurements, and provenance.

### **AI-20 — AI Trust & Regression Benchmark Harness [cross-cutting]**

Every shipped AI capability gets a sealed evaluation set and a release gate. Track at minimum:

- structured-output validity;
- unsupported-claim rate;
- citation precision/recall;
- refusal quality when evidence is missing;
- schema/Design Engine acceptance rate;
- simulator pass rate of proposals;
- human accept/edit/reject rate;
- time saved vs the non-AI workflow;
- model/prompt version regression.

No model or prompt is promoted because a demo looks good.

## **13.5 Cross-cutting AI safety and uncertainty contract**

These rules apply to AI-01 through AI-20:

1. **No authoritative number without provenance.** A performance number shown as fact must point to a Measurement/SimulationRun/DRC/LVS/PEX artifact. Surrogate predictions are visibly labeled predictions.
2. **Structured before prose.** Any proposal that changes a design is a typed object. Prose may explain it but never becomes the machine command.
3. **Explicit uncertainty.** Predictive features carry confidence/uncertainty and an applicability-domain result; low-confidence/OOD means "run the real tool."
4. **Evidence must be addressable.** RAG citations are stable Experiment/Artifact/PDK-document IDs, not vague "according to prior runs" language.
5. **No hidden assumptions.** Spec generation and PDK porting surface assumptions as fields requiring confirmation.
6. **No AI signoff.** Signoff remains DRC/LVS/PEX/SPICE + constraint evaluation. AI can explain signoff, not substitute for it.
7. **No silent promotion.** Experimental discoveries can be auto-logged, never auto-promoted to trusted templates or committed revisions.
8. **Fail closed on malformed structured output.** Invalid JSON/schema does not get repaired invisibly and executed; it is rejected or explicitly re-requested from the model.
9. **Record the cost.** AIAction records token/call cost and latency when available so product value can be measured against inference cost.
10. **Model-agnostic architecture.** Every feature uses LLMProvider or a dedicated non-LLM model interface, with mocks in CI.
11. **Design-data residency is explicit and fail-closed.** Every Project has `ai_execution_mode = DISABLED | LOCAL_ONLY | HOSTED_ALLOWED`, defaulting to `LOCAL_ONLY` for design-bearing contexts. A hosted provider receives schematic/netlist/layout/parameter/history content only after the user explicitly enables hosted AI for that Project/workspace. Secrets, API keys, PDK credentials, license tokens, environment variables, and unrelated filesystem content are never written to AIAction provenance and are filtered before provider calls.
12. **Hosted-provider disclosure is visible.** Before the first hosted call for a Project, the UI states which provider/model receives what classes of design data and records the user's opt-in decision. Switching back to LOCAL_ONLY must immediately block all hosted calls without requiring a restart.

## **13.6 Deferred data-model additions**

Do not add these tables in Stage 0. Add them only when their owning feature lands:

| Entity | Earliest owner | Purpose |
|---|---|---|
| SpecDraft | AI-04 | Unconfirmed NL-to-Spec proposal + assumptions/ambiguities |
| ParetoSnapshot | AI-05 | Reproducible objective front linked to trial IDs |
| SurrogateModelRecord / SurrogatePrediction | AI-06 | Training domain, calibration, uncertainty, prediction provenance |
| LayoutConstraint | AI-09 | Matching/symmetry/proximity/keepout intent passed to deterministic layout |
| CandidateCircuitIR | AI-10 | Sandboxed, untrusted novel topology proposal |
| AIExperimentPlan | AI-12 | Proposed simulation batch, budget, expected information gain |
| LearnedHeuristic | AI-18 | Evidence-backed candidate design rule with promotion state |
| AIEvaluationRun | AI-20 | Sealed benchmark results by model/prompt/version |

## **13.7 API additions — additive only**

Preserve every existing Design Engine API method. When needed, add optional/additive methods rather than bypassing the engine:

```text
propose_spec_draft()
compute_pareto()
plan_experiments()
run_sensitivity()
predict_surrogate()
port_design()
propose_layout_constraints()
diagnose_drc_lvs()
compare_post_layout()
explore_candidate_topology()
query_experiments()
evaluate_ai_feature()
```

Each method returns typed data. Any method that can lead to design change returns a proposal/revision candidate, never silently mutating the committed design.

## **13.8 Commercial/startup prioritization — build the moat, not AI theater**

No roadmap can make a startup "foolproof" or guarantee financial success. The best commercial path in this plan is to prioritize AI where it produces a measurable engineering advantage and compounds the Knowledge Base.

**Priority A — ship earliest because they improve trust + workflow immediately:** AI-01, AI-02, AI-04, AI-05, AI-11, AI-13, AI-15, AI-16, AI-19, AI-20.

**Priority B — moat builders once enough experiments exist:** AI-03, AI-12, AI-18.

**Priority C — high-leverage accelerators after the engine has real data:** AI-06, AI-07, AI-14, AI-17.

**Priority D — impressive but dangerous/expensive; keep post-V1:** AI-08, AI-09, AI-10.

The compounding loop becomes:

```text
engine correctness
-> more validated experiments
-> better retrieval / diagnostics / sensitivity knowledge
-> smarter proposals and experiment planning
-> fewer wasted simulations and faster convergence
-> more validated experiments
-> better surrogate + porting + physical-design intelligence
-> stronger product moat
```

The durable asset is still the same one defined in §5: **validated design history tied to reproducible experiments**. These AI features make that asset more useful; they do not replace it.

## **13.9 AI acceptance gates by release**

### **V0.3 AI Copilot gate**

- explainer has zero unsupported factual claims on the sealed grounding suite;
- ungrounded cases refuse rather than improvise;
- SpecDraft is schema-valid and exposes all assumptions;
- Pareto narration matches deterministic ParetoSnapshot data;
- model/prompt regressions are visible in AIEvaluationRun.

### **V0.4 Topology Intelligence gate**

- every topology proposal cites valid experiment IDs;
- every proposal is schema-valid before simulation;
- human accept/reject/edited decision is logged;
- retrieval includes failures, not successes only;
- read-only ledger query cannot mutate state.

### **V2.0 Intelligence acceleration gate**

- surrogate calibration and OOD thresholds pass a held-out benchmark;
- target-PDK porting is re-optimized and verified in the target PDK;
- layout AI uses structured DRC/LVS/geometry evidence;
- any AI-proposed ECO re-runs the deterministic physical-verification loop.

### **V3.0 Autonomy gate**

- novel topology execution is isolated with CPU/memory/wall-clock/network limits;
- candidate generation uses restricted circuit IR and the normal validators;
- experimental candidates never auto-promote to trusted templates;
- all autonomy can be disabled without breaking the core product.

---

**September 2026 expansion rule:** do not reopen or rewrite the proven Stage 0–4 build sequence. Add AI capabilities as clients of the same engine, in the order above, and promote them only when their own sealed benchmarks prove they help.


---

# **14. Implementation Readiness & Product UX Patch — September 2026 [SUPERSEDES CONFLICTING SHORTHAND, DOES NOT REOPEN THE ARCHITECTURE]**

This section is the final pre-Stage-0 patch. Where older wording in §§0–13 conflicts with this section on measurement semantics, reproducibility, Monte Carlo acceptance, libngspice concurrency, characterization authority, AI data residency, physical-backend responsibility, or product claims, **§14 controls**. No subsystem or capability is removed.

## **14.1 Canonical reproducibility model**

```text
design_identity_hash = SHA256(canonical_encode({
  normalized_netlist,
  logical_simulation_config
}))

execution_environment_hash = SHA256(canonical_encode({
  simulator_build,
  pdk_version,
  model_file_hashes,
  container_digest,
  backend_versions,
  measurement_implementation_version
}))

reproducibility_id = SHA256(canonical_encode({
  design_identity_hash,
  execution_environment_hash,
  random_seed,
  analysis_settings
}))

comparison_policy_id = versioned numerical-equivalence policy
```

A tolerance is a **comparison rule**, not circuit identity. Raw outputs remain attached to the SimulationRun; regression equality is decided by the selected comparison policy.

## **14.2 Statistical robustness report contract**

Every PVT/Monte Carlo headline includes or links to:

`N`, seeds, process corners, supply set, temperature set, device/model variation mechanisms, sampling method, metric thresholds, pass/fail counts, yield estimate, confidence interval/uncertainty method, PDK/model hashes, and the exact experiment IDs.

No hard-coded percentage such as 95% is a universal completion rule.

## **14.3 Product UX is a first-class acceptance surface**

Stage 7 is not merely a schematic canvas. By V0.4/V1.0, a first-time designer must be able to complete this **without understanding the database, Job runner, LLMProvider, or internal API names**:

```text
New Project
-> choose PDK / supply / project AI privacy mode
-> describe circuit intent or choose a template
-> enter specs
-> system identifies missing assumptions and unmeasurable/contradictory constraints
-> user confirms the Specification
-> AI/KB proposes one or more known topologies with evidence
-> user sees schematic + assumptions + evidence
-> run sizing/optimization
-> compare candidates and Pareto trade-offs
-> inspect failures and sensitivity bottlenecks
-> accept a DesignRevision
-> create/inspect layout
-> DRC/LVS/PEX
-> compare pre-layout vs post-layout measurements
-> export reproducible report/artifacts
```

Minimum UX views by V0.4/V1.0:

- **Project Home:** current revision, PDK, spec status, verification status, AI mode, last successful run.
- **Spec Builder:** hard/soft/weighted objectives, assumptions, MetricContract coverage, contradiction/missing-test warnings.
- **Design Workspace:** schematic, selected topology/template, parameter editor, revision diff.
- **Run Center:** live Jobs, logs, waveforms, measurements, failures, reproducibility IDs.
- **Explore/Optimize:** candidate table, Pareto front, parameter sensitivity, PVT/MC robustness.
- **Evidence Inspector:** every AI claim/proposal linked to Experiment/ErrorRecord/Measurement/Artifact IDs.
- **Physical Verification:** layout, DRC markers, LVS mismatch graph, PEX summary, pre/post deltas.
- **Decision Gate:** compare revisions and explicitly accept/reject/branch; no silent commit.

**UX done-when:** a new user can complete the two-stage amplifier journey on a clean install using only product concepts, not internal architecture concepts, and can always answer: *what did the tool try, why, what measured truth supports it, what failed, and what should I do next?*

## **14.4 Physical-backend decision gate**

KLayout remains the preferred viewer/geometry candidate, but no tool is granted monopoly by assumption. The Stage 8 single-device technology spike decides the actual split between KLayout, Magic, and Netgen behind `LayoutBackend`. Backend choice is evidence-driven and replaceable without changing canonical design data.

## **14.5 CACE boundary**

CACE may execute/import/export characterization workflows, but the platform owns the definitions of Specification, MetricContract, Measurement, pass/fail, provenance, and revision history. There is one canonical answer to “what does gain mean for this project?”

## **14.6 AI data residency/privacy modes**

```text
DISABLED       -> no model calls
LOCAL_ONLY     -> only approved local providers/models; no design-bearing payload leaves the machine
HOSTED_ALLOWED -> hosted calls allowed only for this project/workspace after explicit opt-in
```

Hosted calls are logged with provider/model/prompt version and classes of source artifacts sent. Credentials/secrets are filtered and never persisted as AI provenance.

## **14.7 Product claim discipline**

For Sky130 V1 marketing/documentation, prefer **“spec-to-physical-verification”** or **“spec-to-verified-design”** over “production signoff” or an unqualified “Virtuoso/Spectre replacement.” The technical ambition remains large; the claim remains evidence-bound. “Stage 9 physical verification” means the platform completed its declared DRC/LVS/PEX/post-layout checks under the open-PDK/toolchain - not that a foundry has certified a commercial tapeout flow.

## **14.8 Final frozen next action**

Do **not** perform another architecture rewrite. Apply these contracts in the implementation prompts, then execute Stage 0 → Stage 1 → Stage 2 and get the real inverter through schema → validation → netlist → libngspice → waveform → reproducibility/concurrency tests. Implementation evidence now outranks more planning.
