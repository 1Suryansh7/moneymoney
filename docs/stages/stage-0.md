# Stage 0 — Architecture & Packaging (Stage Brief, Layer 2)

Source of truth: `final_build.md` Stage 0 + `final_prompt.md` Stage 0 prompt.
Global rules: `AGENTS.md`. This brief scopes Stage 0 only; anything tagged
`[defer]` stays out.

## 1. Scope (in)

1. Pinned container contract (`Dockerfile`, `docker-compose.yml`) — layered build
   per ADR-015: `base` target verified now, `eda` target pins declared, recipe
   proven in the Stage-0 EDA follow-up. See `docs/stage-0-layered-debt.md`.
2. `Makefile` with exactly three targets: `setup`, `test`, `run-example`.
3. Commit 2 (separate commit): abstract `Simulator` / `LayoutBackend` /
   `PDKAdapter` stubs + `DesignEngine v0.1` skeleton (11 signatures) + stub tests.
4. CI smoke (`/.github/workflows/ci.yml`) building the image and running `make test`.
5. Packaging-only tooling: `pyproject.toml` floors, `config/models.json` capability
   aliases, `scripts/check_models.py` (no-network health check), `examples/smoke.py`.

## 2. Non-goals (out — [defer] violations if built)

No business logic, no unit-system domain logic (empty stub module only in
Commit 2), no database schema (Stage 1), no ngspice calls, no PDK downloads,
no GUI, no LLM wiring (`LLMProvider` arrives Stage 5; aliases config only).

## 3. Done-when

Fresh clone + `setup && test` passes with ZERO manual steps, executed from the
sanctioned shell for the platform (below). `test` = ruff + mypy(strict) +
pytest with zero warnings. `run-example` prints the packaging baseline.

## 4. Stranger-runs-this sequence

Windows 11 + WSL2 + Docker Desktop (WSL2 backend, Ubuntu integration on):

```powershell
git clone <repo> ; Set-Location <repo>
wsl make setup        # builds pinned base image, runs pytest + smoke inside it
wsl make test         # ruff + mypy(strict) + pytest, all inside the image
wsl make run-example  # packaging baseline report
```

Native Linux (Ubuntu 22.04+, Docker Engine 25+/Compose v2.24+): same without `wsl`.
`make` does NOT exist on stock Windows PowerShell — WSL is the sanctioned path,
not a workaround (PREREQUISITES.md sections 1–2, ADR-014).

## 5. Pinned toolchain contract (Commit 1)

| Component | Pin | State |
|---|---|---|
| Python (container authority) | `python:3.11-slim-bookworm` | BUILT + tested |
| Ubuntu reference | `UBUNTU_IMAGE=ubuntu:22.04` | declared (EDA stage root, follow-up) |
| ngspice | `NGSPICE_VERSION=46` (stable, Mar 2026) | DECLARED, build in EDA follow-up |
| KLayout | `KLAYOUT_VERSION=0.30.12` (hotfix, Aug 2026) | DECLARED, build in EDA follow-up |
| Magic | `MAGIC_VERSION=8.3.456` | DECLARED, UNVERIFIED (PREREQUISITES.md carry-over) |
| Netgen | `NETGEN_VERSION=1.5.270` | DECLARED, UNVERIFIED (PREREQUISITES.md carry-over) |
| open_pdks / sky130A | `OPEN_PDKS_GIT_REF=UNPINNED` (fail-closed) | MUST freeze to a commit SHA at EDA build |
| PDK scope | primitive devices only, `sky130A` | policy (no stdcell libs) |
| Host Python | 3.13.x stays (editing only) | container is the test authority |

Supersession note: ngspice-46 / KLayout 0.30.12 replace the stale
PREREQUISITES.md values (ngspice-42/43, KLayout 0.28.x) per live verification
2026-09-05 (ADR-016). PREREQUISITES.md itself is updated in the EDA follow-up,
not silently here.

## 6. Contracts frozen in Stage 0

- `DesignEngine v0.1`: 11 method names + version constant (Commit 2). Additive
  changes only; signature/behavior change bumps to v0.2 with a migration note.
- `Makefile`: exactly `[setup, test, run-example]` (asserted by test_smoke.py).
- LF line endings for all netlist/golden artifacts (`.gitattributes`).
- SI-units law and validation-gate law: no code yet, but no Stage 0 artifact
  may invent a unit-carrying value or a simulator path (nothing to bypass with).

## 7. Verification log

OBSERVED 2026-09-05 in WSL2 Ubuntu (GNU Make 4.3, Docker 29.6.2), from repo root:

- `wsl make setup` — PASS: image built, `6 passed in 0.26s`, `SMOKE OK`.
- `wsl make test` — PASS: `ruff: All checks passed!`,
  `mypy: Success: no issues found in 3 source files`, `6 passed in 0.39s`.
- `wsl make run-example` — PASS: `python=3.11.16`, both aliases reported
  `UNCONFIGURED (expected pre-Stage-5)`, all 4 pins present, `SMOKE OK`.
- Upstream base resolved at build time:
  `python:3.11-slim-bookworm@sha256:528257d48c1da0dcecc2e725d1ae34498d60c965f1241e39cd6a85a8859bdf84`
  (see build log step `[base 1/4] FROM`).
- Resolved toolchain inside image (build log + `/image-requirements-frozen.txt`):
  pip 26.2.1, pytest 9.1.1, pytest-cov 7.1.0, mypy 2.3.1, ruff 0.16.6,
  pre-commit 4.6.2, interpreter 3.11.16.
- Two test failures occurred and were fixed before commit (both honest
  self-authored bugs, neither a framework issue): (1) `:latest` pin check
  false-positived on Dockerfile comment prose — fixed by checking image
  references only; (2) `NameError` from a variable rename in test + smoke —
  fixed, and `make test` (ruff F821) would have caught the same class.
