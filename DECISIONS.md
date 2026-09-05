# DECISIONS.md — Architecture Decision Records (ADRs)

> **Purpose**: This ledger records every foundational architectural decision, design choice, and technical direction taken in this platform, including the context, rationale, alternatives considered, and consequences. Every active agent MUST document any new architectural decision made during development as an ADR in this file.

---

## Index of Architectural Decisions

- [ADR-001: Headless-First Design Loop Prior to GUI](#adr-001-headless-first-design-loop-prior-to-gui)
- [ADR-002: Canonical SI Base Units for All Internal Representations](#adr-002-canonical-si-base-units-for-all-internal-representations)
- [ADR-003: Unified Design Engine API Surface (`DesignEngine v0.1`)](#adr-003-unified-design-engine-api-surface-designengine-v01)
- [ADR-004: Pre-Simulation Validation Gate with Zero Bypass](#adr-004-pre-simulation-validation-gate-with-zero-bypass)
- [ADR-005: Fully Pinned Container Toolchain Environment](#adr-005-fully-pinned-container-toolchain-environment)
- [ADR-006: `libngspice` Shared Library with Process-Isolation Concurrency Proof](#adr-006-libngspice-shared-library-with-process-isolation-concurrency-proof)
- [ADR-007: Four-Part Canonical Reproducibility Identity](#adr-007-four-part-canonical-reproducibility-identity)
- [ADR-008: Model Capability Aliases Instead of Frozen Model IDs](#adr-008-model-capability-aliases-instead-of-frozen-model-ids)
- [ADR-009: Three-Tier AI Data Residency & Secret Protection Layer](#adr-009-three-tier-ai-data-residency--secret-protection-layer)
- [ADR-010: CACE as an Execution Adapter, Not Canonical Specification Authority](#adr-010-cace-as-an-execution-adapter-not-canonical-specification-authority)
- [ADR-011: Strict Human-in-the-Loop Checkpoint Protocol (§12)](#adr-011-strict-human-in-the-loop-checkpoint-protocol-12)
- [ADR-012: Multi-Agent Continuity & Governance File Architecture](#adr-012-multi-agent-continuity--governance-file-architecture)
- [ADR-013: Granular Atomic Decomposition of Stage 1 (1A through 1G)](#adr-013-granular-atomic-decomposition-of-stage-1-1a-through-1g)
- [ADR-014: WSL2 Native Linux Filesystem Architecture Policy](#adr-014-wsl2-native-linux-filesystem-architecture-policy)
- [ADR-015: Layered Stage 0 Container Build (Base Verified Now, EDA Follow-Up Before Stage 1G)](#adr-015-layered-stage-0-container-build-base-verified-now-eda-follow-up-before-stage-1g)
- [ADR-016: Toolchain Pin Refresh — ngspice-46 and KLayout 0.30.12](#adr-016-toolchain-pin-refresh--ngspice-46-and-klayout-03012)
- [ADR-017: ngspice 46 → 47 Correction (Top-Level Folder Does Not Exist)](#adr-017-ngspice-46--47-correction-top-level-folder-does-not-exist)
- [ADR-018: Unit Kernel Ships Types + Display Formatting Only, No Parser](#adr-018-unit-kernel-ships-types--display-formatting-only-no-parser)
- [ADR-019: Platform Language Stability & Native Compiled Extension Gate](#adr-019-platform-language-stability--native-compiled-extension-gate)

---

### ADR-001: Headless-First Design Loop Prior to GUI
- **Date**: 2026-09-04
- **Status**: Accepted
- **Context**: EDA platforms frequently couple business logic and circuit representation tightly into GUI event loops (e.g. Qt/React), making headless optimization, regression testing, and AI-agent automation brittle and difficult.
- **Decision**: Build and verify the complete analog design loop (spec $\to$ topology $\to$ sizing $\to$ simulation $\to$ measurement $\to$ optimization $\to$ verification) headlessly via pure code and API contracts. The GUI (Stage 7) is constructed strictly as a thin client of the existing API.
- **Rationale**: Enables rapid CI automated testing, batch Monte Carlo / optimization runs, and reliable agent interaction without UI overhead.
- **Alternatives Considered**: Building a full schematic GUI first (rejected: delays core engine validation and creates hidden coupling).
- **Consequences**: No visual canvas until Stage 7; early feedback depends on waveforms, metrics, and terminal reports.

---

### ADR-002: Canonical SI Base Units for All Internal Representations
- **Date**: 2026-09-04
- **Status**: Accepted
- **Context**: Analog design tools frequently suffer from unit confusion (e.g. mixing MHz, kHz, pF, fF, mV), leading to silent arithmetic bugs, inconsistent optimization parameters, and parser ambiguities.
- **Decision**: All values stored in SQLite, passed across APIs, held in dataclasses, or processed in algorithms MUST be floating-point numbers in SI base units (Farads, Ohms, Hertz, Volts, Amperes, Seconds, Meters, Kelvin). Metric prefix strings (e.g. `"10MHz"`, `"2.5pF"`) are banned from all storage, schemas, and logic. Prefix parsing and formatting is strictly confined to the display/presentation layer.
- **Rationale**: Eliminates an entire category of unit scaling bugs at compile and runtime.
- **Alternatives Considered**: Storing values with unit strings or allowing arbitrary scale factors (rejected: brittle, slow, prone to parsing errors).
- **Consequences**: Explicit converter functions must be invoked at boundary layers (UI input/output, SPICE netlist export).

---

### ADR-003: Unified Design Engine API Surface (`DesignEngine v0.1`)
- **Date**: 2026-09-04
- **Status**: Accepted
- **Context**: When multiple frontends (CLI, GUI, scripts, AI copilot) interact with EDA engines, they often create private backdoor access to databases or simulator processes, degrading architectural integrity.
- **Decision**: Establish a single, canonical API contract (`DesignEngine v0.1`) exposing 11 core methods (`create_project`, `create_cell`, `instantiate`, `validate`, `netlist`, `simulate`, `check_constraints`, `optimize`, `run_drc`, `extract`, `compare`). All clients must call this surface; private paths to SQLite, ngspice, or KLayout are strictly prohibited.
- **Rationale**: Ensures uniform validation, consistent provenance logging, and seamless backend replacement without breaking client applications.
- **Alternatives Considered**: Allowing direct database queries for GUI performance (rejected: violates Law 4 and destroys provenance integrity).
- **Consequences**: Any capability needed by the UI or AI must be formally added to the Design Engine API contract.

---

### ADR-004: Pre-Simulation Validation Gate with Zero Bypass
- **Date**: 2026-09-04
- **Status**: Accepted
- **Context**: Passing malformed, disconnected, or out-of-spec netlists to SPICE causes silent convergence hangs, nonsensical bias points, and wasted simulation compute.
- **Decision**: Implement a mandatory pre-simulation validation gate that verifies: (1) schema validity, (2) electrical graph connectivity (floating nets, short circuits), (3) SI physical units, and (4) PDK model bindings. Nothing—whether authored by a human or proposed by an AI—reaches ngspice without passing this gate.
- **Rationale**: Guarantees electrical sanity and protects the simulation engine from invalid configurations.
- **Alternatives Considered**: Letting SPICE parse the netlist and report errors (rejected: SPICE syntax errors are notoriously obscure and non-deterministic).
- **Consequences**: Netlist compiler must maintain complete connectivity graphs and device binding records.

---

### ADR-005: Fully Pinned Container Toolchain Environment
- **Date**: 2026-09-04
- **Status**: Accepted
- **Context**: Open-source EDA tools (ngspice, Magic, Netgen, KLayout, open_pdks) undergo frequent updates with breaking syntax, changed model cards, or numerical drift across platforms.
- **Decision**: Package all execution tools in a Docker/Podman container with exact pinned version tags and SHA-256 digests. Never use `:latest`. Pinned tools include: Ubuntu 22.04 LTS, Python 3.11-slim, ngspice with `libngspice`, SkyWater 130nm PDK primitive devices, KLayout, Magic, and Netgen.
- **Rationale**: Guarantees bit-for-bit reproducible toolchain builds across developer machines, CI, and agent sessions.
- **Alternatives Considered**: Host-level installation via package managers (rejected: causes environment drift and platform incompatibilities on Windows/WSL2/macOS).
- **Consequences**: All simulator and layout executions run inside the container; container storage must be actively pruned.

---

### ADR-006: `libngspice` Shared Library with Worker-Process Isolation from Day One
- **Date**: 2026-09-04
- **Status**: Accepted (Amended)
- **Context**: Invoking the `ngspice` CLI binary via subprocess incurs process startup overhead, whereas `libngspice` C API allows fast in-memory execution. However, native C libraries with global/static state (like ngspice) present substantial thread-safety, callback contamination, and reentrancy risks when run in multi-threaded Python environments.
- **Decision**: Adopt **worker-process isolation as the default architecture from Day One** for concurrent simulation trials: `Job Scheduler -> Worker Process -> single libngspice instance -> results/artifacts -> parent`. Keep the public `Job` and `Simulator` contracts unchanged. In-process multi-threading is not required for correctness and will not be pursued as a prerequisite. Concurrency tests in Stage 2 validate the public `Simulator` contract under concurrent Jobs across worker processes.
- **Rationale**: Clean OS-level process boundary guarantees complete isolation of native memory, simulator lifecycle, callbacks, crashes, and cancellations without fighting C global state.
- **Alternatives Considered**: In-process multi-threading (rejected: high risk of silent cross-run state pollution); Python sub-interpreters (rejected: still reside within the same OS process and do not isolate C-level static globals); CLI subprocess shelling (retained as external fallback, but slower than in-process libngspice workers).
- **Consequences**: Job runner uses Python `multiprocessing` or process worker pools from Stage 2 onward. Multi-worker isolation tests assert clean separation across worker processes.

---

### ADR-007: Four-Part Canonical Reproducibility Identity
- **Date**: 2026-09-04
- **Status**: Accepted
- **Context**: Comparing simulation runs requires distinguishing between "is this the same circuit intent?" and "did it run in the same tool environment?", while acknowledging that floating-point simulator outputs are never byte-identical across platforms.
- **Decision**: Define four mathematically distinct concepts:
  1. `design_identity_hash`: SHA-256 of normalized netlist + logical simulation config.
  2. `execution_environment_hash`: SHA-256 of tool builds, PDK hash, container digest, and analysis code version.
  3. `reproducibility_id`: Combined SHA-256 of design hash, env hash, seed, and analysis settings.
  4. `comparison_policy_id`: Versioned numerical tolerance policy.
  Numerical tolerance is strictly a comparison policy, NOT part of circuit identity. Netlists must be byte-identical; simulation outputs are compared under tolerance policies.
- **Rationale**: Provides airtight auditability and reproducible scientific provenance without false comparison failures.
- **Alternatives Considered**: Byte-level hashing of raw simulation waveforms (rejected: numerical noise causes false negatives).
- **Consequences**: The data model and simulation runners must compute and store these hashes for every `SimulationRun`.

---

### ADR-008: Model Capability Aliases Instead of Frozen Model IDs
- **Date**: 2026-09-04
- **Status**: Accepted
- **Context**: Hardcoding concrete LLM model strings (e.g. "gemini-1.5-pro", "gemini-3-flash") in prompts and code leads to brittle configurations as model versions deprecate or update.
- **Decision**: Reference all AI capabilities by functional capability aliases (`GEMINI_STRONG_MODEL`, `GEMINI_FAST_MODEL`) managed in a central configuration. A pre-flight health check verifies resolution of aliases before agent sessions begin.
- **Rationale**: Decouples playbook prompts and application logic from transient provider version naming.
- **Alternatives Considered**: Hardcoding model names across stage prompts (rejected: requires global find-and-replace upon every model deprecation).
- **Consequences**: Configuration file or environment variables must map aliases to concrete model IDs.

---

### ADR-009: Three-Tier AI Data Residency & Secret Protection Layer
- **Date**: 2026-09-04
- **Status**: Accepted
- **Context**: Proprietary circuit designs, API tokens, and local configuration secrets must never be leaked to third-party hosted AI providers without explicit authorization.
- **Decision**: Enforce three project-level AI modes: `DISABLED`, `LOCAL_ONLY` (default), and `HOSTED_ALLOWED`. Design-bearing contexts default to `LOCAL_ONLY`. Outbound hosted calls require explicit user opt-in following artifact disclosure. API keys, PDK credentials, environment variables, and secrets are filtered before provider dispatch and never persisted in `AIAction` records.
- **Rationale**: Protects intellectual property and guarantees zero credential leakage.
- **Alternatives Considered**: Blanket opt-in for all external LLMs (rejected: unacceptable for proprietary IC IP).
- **Consequences**: A redaction filter and residency guard must be integrated into the `LLMProvider` abstraction.

---

### ADR-010: CACE as an Execution Adapter, Not Canonical Specification Authority
- **Date**: 2026-09-04
- **Status**: Accepted
- **Context**: CACE (Circuit Automatic Characterization Engine) provides automated datasheet and verification capabilities for Sky130, but defining specs in both CACE format and platform format risks split-brain definition conflicts.
- **Decision**: The Design Engine remains the sole canonical authority for `Specification`, `MetricContract`, `Measurement`, pass/fail verdicts, and revision provenance. CACE is supported strictly as an adapter/execution bridge (import/export), never as a secondary specification authority.
- **Rationale**: Prevents conflicting definitions of core metrics (e.g. gain, bandwidth, phase margin).
- **Alternatives Considered**: Using CACE YAML files as the primary project specification format (rejected: limits the platform to CACE capabilities and creates external dependency).
- **Consequences**: Bidirectional round-trip tests must be implemented to ensure zero semantic translation loss when bridging to CACE.

---

### ADR-011: Strict Human-in-the-Loop Checkpoint Protocol (§12)
- **Date**: 2026-09-04
- **Status**: Accepted
- **Context**: AI agents building complex analog circuits frequently produce code that compiles and runs cleanly while being quietly wrong (e.g. swapped transistor terminals, sign errors in measurement math, non-physical PCells).
- **Decision**: Mandate the §12 Human Checkpoint protocol. For any first-time occurrence of defined triggers (first golden reference, first simulation waveform, each new metric contract, statistical claims, AI topology proposals, clean DRC/LVS), the agent must halt execution, emit an exact standardized alert block, and wait for explicit human verification before proceeding.
- **Rationale**: Enforces human engineering signoff at critical trust boundaries, preventing compounded silent failures.
- **Alternatives Considered**: Automated test-only gating (rejected: tests cannot detect bugs when the golden reference itself is wrong).
- **Consequences**: Development workflow requires human presence and verification at marked milestones.

---

### ADR-012: Multi-Agent Continuity & Governance File Architecture
- **Date**: 2026-09-04
- **Status**: Accepted
- **Context**: High-horizon development across autonomous coding agents frequently experiences context truncation, lost session state, unrecorded decisions, and fragmented to-do tracking.
- **Decision**: Establish a permanent five-file root governance structure:
  1. `AGENTS.md`: Non-negotiable operating rules, laws, and prompt libraries.
  2. `context.md`: Comprehensive system state and session resume handbook.
  3. `To-Do.md`: Granular task and subtask execution tracker.
  4. `DECISIONS.md`: Architectural Decision Records log.
  5. `PREREQUISITES.md`: Explicit environment specifications and pre-stage verification checklists.
  All agents are bound to maintain and update these files across turns.
- **Rationale**: Guarantees seamless handoffs across agent sessions, prevents duplicate work, and maintains architectural coherence.
- **Alternatives Considered**: Relying on conversation chat history or memory summaries (rejected: chat history truncates and does not persist across different tools/agents).
- **Consequences**: Minor documentation maintenance overhead on each task execution.

---

### ADR-013: Granular Atomic Decomposition of Stage 1 (Commits 1A through 1G)
- **Date**: 2026-09-04
- **Status**: Accepted
- **Context**: Stage 1 (Circuit Kernel) bundles the unit system, SQLite schema, connectivity graph, netlist compiler, validation gate, and golden fixture. If authored as a single monolithic commit or large chunks, failure localization becomes ambiguous—an AI agent debugging a failed golden netlist might erroneously "fix" the compiler to compensate for a bug in unit scaling or device binding.
- **Decision**: Formally decompose Stage 1 into 7 atomic, independently tested commits (100–250 lines target, 400 lines hard cap):
  - **Commit 1A**: Typed SI unit system + boundary converters $\to$ unit tests.
  - **Commit 1B**: Minimal SQLite schema/entities $\to$ migration & schema tests.
  - **Commit 1C**: Design connectivity representation $\to$ graph & net connectivity tests.
  - **Commit 1D**: Deterministic canonicalization $\to$ canonical-hash tests.
  - **Commit 1E**: SPICE netlist compiler $\to$ expected netlist tests.
  - **Commit 1F**: Pre-simulation validator $\to$ invalid-design rejection suite.
  - **Commit 1G**: Hand-built inverter/NMOS golden fixture $\to$ blocking Human Checkpoint.
- **Rationale**: Provides pinpoint failure localization, prevents cross-layer compensating bugs, and strictly enforces the "one task = one commit = one testable claim" rule.
- **Alternatives Considered**: Monolithic Stage 1 implementation (rejected: dangerous error coupling across layers).
- **Consequences**: Increases the number of small commits in Stage 1, but guarantees each layer is independently proven before the next depends on it.

---

### ADR-014: WSL2 Native Linux Filesystem Architecture Policy
- **Date**: 2026-09-04
- **Status**: Accepted
- **Context**: On Windows 11 with WSL2, accessing Windows NTFS files via the 9P filesystem bridge (`/mnt/c/...`) introduces noticeable I/O latency and CPU overhead compared to native Linux ext4 filesystem access (`/home/...` or `~`). While Stage 0 and early single-simulation stages tolerate this overhead, high-frequency simulation loops (e.g. Stage 4 Optuna sweeps with 500+ trials generating database records, logs, and waveforms) can experience substantial I/O degradation.
- **Decision**: Adopt the Microsoft-recommended filesystem policy:
  1. The project repository can be cloned and built directly inside the WSL2 native filesystem (`~/workspace/...` or accessible from Windows via `\\wsl$\Ubuntu\home\...`) for maximum container I/O throughput during simulation and optimization sweeps.
  2. If developed from the Windows host mount (`/mnt/c/...`), treat cross-filesystem I/O as a known performance risk, monitor trial latency, and migrate high-frequency artifact/simulation scratch directories to `/tmp` (in-memory ext4) inside the container.
- **Rationale**: Eliminates filesystem bridge bottlenecks during compute-heavy optimization sweeps while preserving Windows-side IDE convenience.
- **Alternatives Considered**: Mandating that developers never use Windows mounts (rejected: overly rigid for initial setup); ignoring WSL2 filesystem characteristics (rejected: leads to unexplained slowdowns during large optimization runs).
- **Consequences**: Documentation and Docker volume mount configurations must support both native WSL paths and Windows paths gracefully.

---

### ADR-015: Layered Stage 0 Container Build (Base Verified Now, EDA Follow-Up Before Stage 1G)
- **Date**: 2026-09-05
- **Status**: Accepted (human-approved: layered with comprehensive debt record)
- **Context**: The Stage 0 prompt demands one Dockerfile pinning Python, ngspice/libngspice, sky130A PDK, KLayout, Magic, and Netgen. Building all of that at once costs 3–10 GB and a 30–90 minute failure-prone build on the Windows/WSL2 host, delaying the verified packaging gate everything else stands on. But deferring EDA silently would create false confidence.
- **Decision**: Layer the build. Commit 1 verifies the `base` target (pinned `python:3.11-slim-bookworm` + test toolchain) in CI; the `eda` target declares every pin but its recipe build is proven in a Stage-0 EDA follow-up that MUST go green before Stage 1G (golden reference needs PDK model cards per Law 2) and before any Stage 2 prompt. All disadvantages, blast radii, and remediations are recorded in `docs/stage-0-layered-debt.md` (D-1 through D-9, R-1 through R-8), which closes only on a green EDA run.
- **Rationale**: A fast, truthful, verified packaging gate now beats a slow, half-verified monolith; the debt file keeps the deferral honest and scheduled instead of silent.
- **Alternatives Considered**: Full monolithic EDA image in Commit 1 (rejected: big-bang debug surface, blocks all Stage 0 verification on the slowest step); silent deferral with no debt record (rejected: violates honesty rules).
- **Consequences**: `docker-compose.yml` carries an `app-eda` (`eda` profile) service; CI gains an eda job in the follow-up; To-Do.md encodes the predecessor edge.

---

### ADR-016: Toolchain Pin Refresh — ngspice-46 and KLayout 0.30.12
- **Date**: 2026-09-05
- **Status**: Accepted (human-approved: pin new stable)
- **Context**: PREREQUISITES.md pins ngspice-42/43 and KLayout 0.28.x/0.29.x. Live verification on 2026-09-05 showed ngspice-46 (stable, 29-Mar-2026) and KLayout 0.30.12 (hotfix, 26-Aug-2026) as current stable releases. Building on two-year-old EDA versions would start the platform with known-fixed bugs.
- **Decision**: Pin `NGSPICE_VERSION=46` and `KLAYOUT_VERSION=0.30.12` in the Dockerfile contract. Magic 8.3.456 / Netgen 1.5.270 stay as explicitly UNVERIFIED carry-over defaults until the EDA follow-up runs `ls-remote` against upstream (ADR-015 D-7). PREREQUISITES.md itself is amended in the EDA follow-up, not rewritten from memory here.
- **Rationale**: Pin what is current and verified; label what is carried over on trust.
- **Alternatives Considered**: Keeping stale pins for doc compliance (rejected: knowingly building on outdated tools).
- **Consequences**: Stage 2 libngspice work targets the ngspice-46 API; the EDA follow-up confirms Magic/Netgen tags.

---

### ADR-017: ngspice 46 → 47 Correction (Top-Level Folder Does Not Exist)
- **Date**: 2026-09-05
- **Status**: Accepted (supersedes ADR-016's ngspice-46 pin; ADR-016's KLayout/Magic/Netgen reasoning stands)
- **Context**: ADR-016 pinned ngspice-46 from March-2026 release notes seen via web search. During the EDA build, both candidate tarball URLs 404'd; a live listing of `ng-spice-rework/` showed only `47/` and `old-releases/` (46 lives under `old-releases/46/`), and the project's own download page names ngspice-47 "the latest stable release". The search snippets had mixed stale folder contents.
- **Decision**: Pin `NGSPICE_VERSION=47` (`ng-spice-rework/47/ngspice-47.tar.gz`, listing observed live). Lesson recorded: release existence (NEWS file) is not release availability (file path) — verify the artifact URL, not just the version number.
- **Rationale**: User directive "latest everything" + project-declared latest stable + verified artifact path.
- **Alternatives Considered**: ngspice-46 from old-releases (rejected: older by one release against the explicit latest-everything directive).
- **Consequences**: EDA recipe, smoke pins, and contract tests target 47; Stage 2 libngspice work targets the ngspice-47 API.

---

### ADR-018: Unit Kernel Ships Types + Display Formatting Only, No Parser
- **Date**: 2026-09-05
- **Status**: Accepted
- **Context**: The playbook asks for "explicit converters at the boundary" in Commit 1A, but AGENTS.md Law warns that parsing SI prefixes outside the UI layer is a fundamental architectural mistake — and no UI/input boundary exists until Stage 7.
- **Decision**: Commit 1A ships validated quantity types (`Quantity` + 8 SI units, finite-only validation) and one display formatter (`format_quantity`, display-layer-only, documented non-import for engine code). NO string→quantity parser ships; strings are rejected at construction with `UnitError`, proven by test. Parsing arrives with the Stage 7 UI input boundary that actually needs it.
- **Rationale**: A kernel parser would legitimize unit strings inside the system — the exact failure mode the law forbids. Converters shipped are exactly the ones with a live boundary today (float→Quantity at APIs, Quantity→string at reports).
- **Alternatives Considered**: Shipping `parse_quantity` now (rejected: no legitimate caller exists yet; invites misuse).
- **Consequences**: Stage 7 must build the input parser; until then any `"10MHz"`-shaped input fails closed at the typed boundary.

---

### ADR-019: Platform Language Stability & Native Compiled Extension Gate
- **Date**: 2026-09-05
- **Status**: Accepted
- **Context**: Exploration was raised whether rewriting the platform from Python to C++ or Rust would improve system efficiency, given the intense computational demands of analog IC design.
- **Decision**: Python 3.11+ remains the permanent orchestration language for the entire platform. Full rewrites into C++, Rust, or other languages are strictly prohibited. Native compiled extensions (e.g. Rust via PyO3 or C++ via nanobind) are permitted ONLY when backed by an empirical profiling trace proving that a specific inner loop spends >80% of job execution time in Python bytecode. Proposing language stack alterations or introducing compiled extensions triggers a mandatory BLOCKING HUMAN CHECKPOINT (§8) before any code is added.
- **Rationale**: 95–99% of CPU runtime in analog IC design is already spent in native C/C++ engines (ngspice, KLayout, Magic, Netgen, SQLite). Rewriting the orchestration layer yields negligible (<0.2%) runtime benefit under Amdahl's Law, while forfeiting the entire Python EDA/AI/scientific ecosystem (Optuna, NumPy, SciPy, KLayout Python API, AI SDKs) and destroying developer velocity. In addition, ngspice's global C state mandates multi-process isolation regardless of host language.
- **Alternatives Considered**: 
  - Complete rewrite in Rust/C++ (rejected: premature optimization, massive velocity penalty, loss of EDA/AI Python ecosystem, zero impact on ngspice solver bottlenecks).
  - Unrestricted use of native extensions (rejected: increases Docker container build complexity, cross-platform compilation friction, and maintenance burden without proven performance need).
- **Consequences**: Platform remains maintainable and Python-centric; performance hot-paths can be accelerated surgically via PyO3/nanobind if empirically justified later under human signoff.
