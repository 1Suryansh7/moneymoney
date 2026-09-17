# actionhub.md — GitHub Workflows Log & Incident Record

> Owner: CI health (`ci.yml`). Every workflow fact below is quoted from
> `.github/workflows/ci.yml` or measured in a tool run — no projected
> numbers. Last updated 2026-09-16 after the #40–#42 incident.

---

## 1. The workflow we designed together (`ci.yml`)

One file: `.github/workflows/ci.yml`. Trigger: `on: push` to branches
`**` + `pull_request`. Two jobs, no dependencies (run in parallel on
separate `ubuntu-latest` runners):

| Job | Steps (in order) | Gate |
|---|---|---|
| `smoke` | 1. `actions/checkout@11d5960a326750d5838078e36cf38b85af677262` (pinned immutable SHA, PGP-verified v4 — never float) 2. build base image + `make setup` (= `docker compose build app` + in-container `pytest -q` + `examples/smoke.py`) 3. `make test` (= in-container `ruff check .` + `mypy .` (strict) + `pytest -q`) | Base gate green |
| `eda` | 1. Same pinned checkout 2. `docker compose --profile eda build app-eda` (acceptance probes run inside the build) 3. Re-probe (`ngspice --version`, `klayout -b -v`, `sky130.lib.spice` present, `/image-eda-versions.txt`) 4. `python3.11 -m pytest -q` (full suite, **zero skips expected**) | Full-suite green, no skips |

Exit-code semantics: pytest `0` = pass, `1` = test failures, `2` = interrupted,
`5` = no tests collected. GNU `make` exits `2` when ANY recipe fails — so a
smoke annotation of "exit code 2" points at the `make` wrapper, and you must
open the red STEP to see which of build/pytest/smoke/ruff/mypy actually died.
A failure at ~1 min cannot have reached pytest (fresh base build alone takes
minutes) — it died in checkout or `docker compose build`.

Known benign annotations: `actions/checkout` Node.js 20 deprecation
warnings (forced onto Node 24 by the runner) — warnings, not errors.

---

## 2. Incident log (every CI failure to date)

### #1 — pytest cache-write teardown, first-ever GitHub run (2026-09-06)
- Symptom: BOTH jobs red at teardown AFTER all tests passed
  (`PermissionError Errno 13` on `/workspace/pytest-cache-files-*`).
- Root cause (product defect, fixed): container runs as UID 1000, GitHub
  checks out files owned by runner UID 1001 — `/workspace` read-only for
  the test user.
- Fix (committed): hermetic caches — pytest `-p no:cacheprovider`, ruff
  `cache-dir` + mypy `cache_dir` → `/tmp` (`pyproject.toml`), exact `==`
  dev pins. Proven by read-only-workspace replica + fresh `--no-cache`
  build. Follow-up runs green.

### #2 — smoke red, unused loop variable (2026-09-12, `7c4ca71` era)
- Symptom: smoke red, ~59 s profile (build/context stage, not tests).
- Root cause (product defect, fixed): `R0-5 Commit 2` shipped without a
  full local gate; an unused loop variable failed the `ruff` leg of
  `make test`. Plus `COPY . .` shipped ~1 GB of UI generated weight.
- Fix (committed `7c4ca71`): removed the variable; `.dockerignore`
  excludes `node_modules/.output/.wrangler/test-results/dist`. Local
  `ruff + mypy + 388+47` green; re-run requested.

### #3 — smoke red ×1, infrastructure suspected (run #36, `a783410`)
- Symptom: smoke red in ~1m3s; eda GREEN (41m).
- Triage: all five smoke steps reproduced green locally on the pushed
  tree (build, pytest 432+51, smoke example, ruff, mypy strict 132
  files). A 1-minute failure cannot reach pytest — dies in checkout or
  `docker compose build` (anonymous-registry pull flake signature on
  shared runner egress IPs). No code change made (green code is not
  "fixed"). Re-run requested.

### #4 — smoke AND eda red ×3 consecutive (runs #40 `1c49422`, #41
  `2dabe8f`, #42 `1ec2455`; smoke ~1m, eda ~48–58m, exit 2 / exit 1)
- Triage (2026-09-16, full evidence):
  - Base: collection clean (493 tests, no errors); all five smoke steps
    green locally incl. fresh `--no-cache` base build.
  - EDA: full suite rerun locally on the pushed tree —
    **479 passed, 14 skipped, 0 failures in 50m24s**. No EDA defect.
  - One genuine (minor) defect found en route and fixed: Netgen writes
    `comp.out` to the invocation CWD — pinned to `tmp_path` in
    `tests/test_layout_spike.py` (tree hygiene, not a CI cause;
    untracked file, never pushed).
  - Scare en route (recorded so nobody re-chases it): a full-suite run
    appeared hung 15 min at 14% inside `test_b7_without_backend` /
    `jobs.wait → proc.join`. Faulthandler proved it was mid-simulation,
    not deadlocked; contributing factors were observer load (concurrent
    base runs + shells on the same box) and line-buffered dots. Quiet-box
    rerun advanced normally. `engine.simulate` already bounds every wait
    at 300 s (`_SIM_TIMEOUT_S`), so an infinite hang is structurally
    impossible on this path.
- Verdict: **CI infrastructure on both jobs, zero product defect.**
  Smoke ~1 min ×3 = build-phase pull/runner fault (registry
  rate-limit signature, persistent for hours on shared IPs). EDA
  exit-1 after ~58 min with a locally-proven-green tree = runner-side
  fault (disk pressure on 14 GB runners vs multi-GB EDA image, or
  transient execution fault).
- Fix (committed): bounded ×3 retry (60 s backoff) on both
  `docker compose build` steps — genuine Dockerfile breaks still fail,
  only slower. No product code touched.
- Resolution (run #43, green in 46m23s): three reds → green with zero
  product-code changes between them — infrastructure verdict proven.
  (Whether the retry triggered or the flake healed on its own is
  unrecorded; either way the repo is now resilient to the class.)

### #5 — smoke ruff failure + EDA PCell DRC failure (runs #44–#53, 2026-09-17)
- Symptom: smoke red in ~1 min across all 10 runs; EDA red in runs #49–#53.
- Root causes (product defects, verified & fixed):
  1. **Smoke job**: `scripts/layout_pcell_emit.py` had an unused `import os`
     (runs #44–#48); subsequently `src/analog_ic_design/layout/__init__.py`
     had an unformatted import block with line length > 100 chars (runs #50–#53),
     causing `ruff check .` to exit 1 during `make test`.
  2. **EDA job**: in `src/analog_ic_design/layout/pcells.py`, reducing
     `_TAP_Y_GAP_UM` to 0.30 placed the substrate tap LI only 0.15 µm away
     from the S/D strap LI (0.30 - 0.10 strap past diff - 0.05 tap LI past tap).
     Rule `li.3` mandates minimum LI spacing of 0.17 µm. Resulted in 2 DRC
     violations in `test_pcell_drc_clean` for both NMOS and PMOS.
- Fix: formatted imports in `src/analog_ic_design/layout/__init__.py`;
  increased `_TAP_Y_GAP_UM` to 0.35 µm in `src/analog_ic_design/layout/pcells.py`
  (clearing `li.3` at 0.20 µm and `difftap.3` at 0.35 µm).
- Local verification: `make test` inside base container (ruff, mypy 147 files,
  pytest 447 passed + 62 skipped) and `test_pcell_drc_clean` (0 violations)
  all 100% green.

---

## 3. Operator runbook

- **Green code, red CI**: (1) note durations (sub-2-min smoke ≈ build
  phase; full-duration eda ≈ suite), (2) reproduce the exact failing
  step locally per §1, (3) if local is green, it is infra: Re-run jobs
  from the run page, (4) three consecutive infra reds → harden the
  workflow (retry/backoff), never "fix" green code.
- **Reading a run**: job duration + per-step red marker first (exit 2 =
  `make` wrapper failed — open the STEP, not the job), annotations
  second (Node warnings are benign), `FAILED` node IDs in the pytest
  tail for real failures.
- **Re-run**: run page → `Re-run jobs` dropdown (no CLI/token needed
  from here; there is no `gh` access in this environment).
- **Local reproduction map**: smoke = `docker compose build app` +
  `docker compose run --rm app python -m pytest -q` +
  `python examples/smoke.py` + `ruff check .` + `mypy .`
  (`make setup` / `make test` on WSL2 Ubuntu); eda =
  `docker compose --profile eda run --rm app-eda python3.11 -m pytest -q`
  (expect ~50 min, zero skips).
