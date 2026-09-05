# PREREQUISITES.md — Stage 0 Prerequisite Specifications & Verification Guide

> **DISCLAIMER**: This document specifies every single prerequisite, environment dependency, tool requirement, and configuration setting required **BEFORE** Stage 0 implementation begins. In strict adherence to user instructions, **ZERO IMPLEMENTATION CODE, DOCKERFILES, OR STUBS ARE BUILT IN THIS STEP**.

---

## 1. System & Virtualization Prerequisites

### 1.1 Host Hardware Verification
- **Host OS**: Windows 11 (64-bit).
- **RAM Allocation**: 16 GB Physical RAM.
- **GPU**: NVIDIA GeForce RTX 4060 Laptop GPU (8 GB VRAM) — drivers installed and CUDA enabled (relevant for later stages).
- **Storage**: Minimum 30 GB unallocated disk space dedicated for containers, WSL2 virtual disk, and build artifacts (out of ~100 GB available).

### 1.2 WSL2 Configuration (`.wslconfig`)
To prevent WSL2 from exhausting host RAM on a 16 GB machine, create or verify `C:\Users\<username>\.wslconfig` with the following memory-capping limits:

```ini
[wsl2]
memory=10GB          # Caps WSL2 memory to 10GB, leaving 6GB for Windows and IDE
processors=6         # Allocates 6 CPU cores
swap=4GB             # Caps swap allocation to 4GB
localhostForwarding=true
```
*After editing, restart WSL via PowerShell: `wsl --shutdown`.*

### 1.3 WSL2 Virtual Disk Compaction Procedure
WSL2 virtual hard disks (`ext4.vhdx`) grow dynamically upon container builds and do not automatically contract when files or images are deleted. To maintain disk health under the 100 GB budget:
1. Shut down WSL:
   ```powershell
   wsl --shutdown
   ```
2. Compact the virtual disk (Run in Administrator PowerShell):
   ```powershell
   wsl --manage Ubuntu --compact
   ```
   *Alternatively via diskpart: select vdisk file=`<path-to-vhdx>` $\to$ `compact vdisk`.*

### 1.4 WSL2 Filesystem Location & Performance Policy
Per official Microsoft guidance, cross-filesystem access from Linux containers to Windows NTFS mounts (`/mnt/c/...`) incurs noticeable 9P bridge translation and I/O latency.
- **Stage 0–3 Development**: Running from the current Windows directory (`C:\MONEY\Cad\codeeahhhhhhh` / `/mnt/c/MONEY/Cad/codeeahhhhhhh`) is suitable for packaging and initial kernel development.
- **Stage 4+ Optimization & High-Frequency Sweeps**: For batch simulations (e.g. 500+ Optuna trials), clone or move the active simulation runtime to the WSL2 native Linux filesystem (`/home/<user>/...` or `~`), which is directly accessible from Windows via network path `\\wsl$\Ubuntu\home\<user>\`.
- **In-Memory Scratch Acceleration**: Configure container simulation artifacts and temporary SPICE decks to write to `/tmp` (in-memory ext4 tmpfs) rather than disk to minimize cross-boundary I/O overhead.

---

## 2. Container Runtime Prerequisites

### 2.1 Docker Engine / Podman Setup
- **Engine**: Docker Desktop (version 25.0+ or 26.0+) configured with the **WSL2-based engine backend** (Settings $\to$ General $\to$ "Use the WSL 2 based engine" checked).
- **WSL Integration**: Enabled for the default Ubuntu distribution (Settings $\to$ Resources $\to$ WSL Integration $\to$ Ubuntu enabled).
- **Docker Compose**: Docker Compose v2.24+ enabled.

### 2.2 Container Hygiene Policy
- Execute `docker system prune` following container rebuilds to purge dangling build layers.
- Avoid multi-stage image hoarding; maintain only the single tagged project build.

---

## 3. Pinned Toolchain & Image Bill of Materials (For Stage 0 Dockerfile)

When Stage 0 is authorized, the Dockerfile will build against exact, immutable version tags and commit hashes (never `:latest`):

| Component | Target Version / Pin | Purpose in Stack |
|---|---|---|
| **Base Image** | `ubuntu:22.04` (pinned digest) | Host container environment |
| **Python** | `python:3.11-slim` (3.11.8+) | Core runtime for Design Engine and test harness |
| **ngspice** | `ngspice-42` (or `ngspice-43`) built with `--with-ngshared` | Electrical simulation engine producing `libngspice.so` |
| **SkyWater 130nm PDK** | `sky130A` primitive models (pinned `open_pdks` commit) | Transistor and passive model cards (excluding standard cell libraries) |
| **KLayout** | `0.28.16` or `0.29.1` Debian package | GDS/OASIS layout viewer, DRC, and geometry engine |
| **Magic** | `8.3.456` (pinned commit) | Secondary physical DRC / PEX extraction adapter |
| **Netgen** | `1.5.270` (pinned commit) | LVS (Layout-vs-Schematic) comparison engine |

---

## 4. Host Development Environment & Quality Tooling

The local host and container Python environment require the following pinned tooling:

### 4.1 Strict Type Checking (`mypy`)
- **Version**: `mypy >= 1.9.0`
- **Configuration**: Strict mode mandatory (`--strict`, `disallow_untyped_defs = true`, `disallow_any_generics = true`, `no_implicit_optional = true`).

### 4.2 Fast Linting & Code Formatting (`ruff`)
- **Version**: `ruff >= 0.3.0`
- **Configuration**: Line length 100, rules enabled: `E` (Pycodestyle), `F` (Pyflakes), `I` (isort), `B` (flake8-bugbear), `UP` (pyupgrade).

### 4.3 Automated Test Framework (`pytest`)
- **Version**: `pytest >= 8.0.0`, `pytest-cov >= 5.0.0`
- **Execution Target**: Stage 0 requires 100% pass on all interface signature tests with zero warnings.

### 4.4 Git & Pre-Commit Hooks
- **Tool**: `pre-commit >= 3.6.0`
- **Enforcement**: Blocks commits if unformatted, untyped, or failing linter checks.

---

## 5. IDE & MCP Server Roster

### 5.1 Recommended IDE Extensions
- **Python** (`ms-python.python`) & **Mypy** (`matangover.mypy`)
- **Docker** (`ms-azuretools.vscode-docker`)
- **Error Lens** (`usernamehw.errorlens`) — Instant visual feedback on type mismatches
- **SQLite Viewer** (`qwtel.sqlite-viewer`) — Inspection of Stage 1+ schemas

### 5.2 Mandatory MCP Servers
- **Filesystem MCP**: Authorized for `c:\MONEY\Cad\codeeahhhhhhh`
- **Git MCP**: For inspecting diffs and commit histories
- **Sequential Thinking MCP**: For multi-file architectural planning

---

## 6. AI API Configuration & Capability Aliases

### 6.1 Google AI Studio API Key Setup
- Obtain Gemini API Key from Google AI Studio.
- Export as environment variable in `.env` or user environment:
  ```bash
  export GEMINI_API_KEY="AIzaSy..."
  ```

### 6.2 Model Capability Alias Resolution Configuration
Define the alias mapping in the environment or project configuration file (`config/models.json`):
```json
{
  "GEMINI_STRONG_MODEL": "gemini-1.5-pro-latest",
  "GEMINI_FAST_MODEL": "gemini-1.5-flash-latest"
}
```
*Note: A startup health check must verify that these aliases successfully query the provider before sessions begin.*

### 6.3 External Web Review Environment
- **ChatGPT Plus**: Browser session ready for adversarial netlist testing and second-opinion architecture reviews.

---

## 7. Prerequisite Pre-Flight Diagnostic Checklist

A developer or incoming agent can run these checks in PowerShell / bash to verify host readiness before executing Stage 0:

```bash
# 1. Verify Docker Engine is running and responsive
docker version

# 2. Verify Docker Compose is available
docker compose version

# 3. Verify WSL2 status
wsl --status

# 4. Verify Python 3.11 is available
python --version

# 5. Verify Git status
git status

# 6. Verify Google Gemini API key is present in environment
echo $GEMINI_API_KEY
```

Once all 6 checks return clean status, the repository is 100% prepared for **Stage 0 Commit 1 (Packaging & Bootstrap)**.
