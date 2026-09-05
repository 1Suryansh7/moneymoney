# Stage 0 Layered-Build Debt Record (human-requested, comprehensive)

Decision: ADR-015. `base` image verified in Commit 1; `eda` toolchain declared
but unbuilt until the Stage-0 EDA follow-up. This file lists every disadvantage
of that layering, its blast radius, how it will be detected, and the exact
remediation. It CLOSES (deleted or marked closed) when the EDA follow-up is
green; until then it is required reading before Stage 1G / Stage 2 planning.

## D-1. Reproducibility identity is incomplete (SEVERE)

- What: `final_build.md` section 14.1 requires `execution_environment_hash`
  over simulator build + PDK version + model-file hashes + container digest.
  With no EDA layer built, that hash cannot be computed for anything real.
- Blast radius: any Stage 1/2 artifact claiming reproducibility before the
  follow-up would be unfounded. No such claim is made in Commit 1 (nothing
  simulates), so exposure is currently zero — it becomes blocking the moment
  Stage 2 starts.
- Detection: Stage 2 tests assert the four-part identity; they cannot pass
  on `base`.
- Remediation (R-1): EDA follow-up builds `--target eda` with a frozen
  `OPEN_PDKS_GIT_REF=<sha>`, captures `sky130A/.config/nodeinfo.json`,
  records `docker inspect --format='{{.RepoDigests}}'`, and stores all three
  in the Stage-0 summary update.

## D-2. CI proves Python packaging only (HIGH)

- What: `make setup` / `make test` / CI exercise the `base` target. A green
  badge says nothing about ngspice build flags, KLayout availability, or PDK
  presence.
- Blast radius: false confidence if anyone reads CI green as "toolchain ready".
- Detection: this file + the `UNBUILT` markers in `Dockerfile` + the pin table
  in `docs/stages/stage-0.md` (State column).
- Remediation (R-2): EDA follow-up adds a second CI job building `--target eda`
  and running `docker compose --profile eda run --rm app-eda ngspice --version`
  (plus KLayout/Magic/Netgen version probes) as its gate.

## D-3. libngspice integration risk is deferred, not retired (HIGH)

- What: the load-bearing Stage 2 unknown — source-building ngspice-46 with
  `--with-ngshared`, shared-library ABI, callback behavior, and the 1/2/4-job
  isolation suite — is unverified. A build-flag surprise (missing XSPICE,
  OpenMP, readline, FFTW linkage) surfaces later than it could have.
- Blast radius: confined to schedule (Stage 2 start), not to correctness of
  anything built now — Commit 1/2 contain no simulator path by construction.
- Detection: EDA follow-up must compile a hello-netlist through `libngspice`
  (not the CLI) as its acceptance probe, before Stage 2 begins.
- Remediation (R-3): EDA recipe builds ngspice-46 from source tarball with
  `--with-ngshared --enable-xspice --enable-openmp`, runs `make check` if
  provided upstream, and stores the configure flags in the image labels.

## D-4. PDK blindness: Law 2 exposure starts at Stage 1G (HIGH)

- What: no Sky130 file has been read (nothing downloaded). Per AGENTS.md Law 2
  and the PDK anti-hallucination gate, the Stage 1G golden NMOS/inverter
  reference CANNOT be authored until PDK model cards are on disk and quoted.
- Blast radius: Stage 1A–1F (units, schema, connectivity, canonicalization,
  compiler skeleton, validator) are PDK-independent and may proceed on `base`;
  Stage 1G is hard-blocked on the EDA follow-up.
- Detection: 1G task prompt requires quoting PDK file + lines; no file exists yet.
- Remediation (R-4): EDA follow-up downloads primitive-only sky130A
  (`--with-sky130-variants=A`, extra libs disabled), and records the exact
  model-card paths (e.g. `sky130.lib.spice` primitive sections) for 1G.

## D-5. Tag-not-digest drift on the base image (MEDIUM)

- What: `python:3.11-slim-bookworm` is an exact tag but still a moving pointer:
  rebuilds months apart can pull different OS/security layers.
- Blast radius: slow, silent environment drift; contradicts ADR-005 if ignored.
- Detection: compare `RepoDigests` across rebuilds.
- Remediation (R-5): every `make setup` run prints
  `docker inspect --format='{{.RepoDigests}}'` output; the digest is pasted
  into the commit/summary that performed the build. Commit 1 body carries the
  first digest. A future commit may promote the digest into the Dockerfile
  `FROM ...@sha256:...` form once churn settles.

## D-6. Pinned-dependency duplication (MEDIUM) — CLOSED by Commit 2

- What: the Dockerfile `pip install` list duplicated pyproject `dev` floors,
  because `pip install -e .[dev]` needs a `src/` layout that Commit 1 must not
  create (Commit 2 scope). Two lists can drift.
- Closure: Commit 2 created `src/analog_ic_design` and replaced the Dockerfile
  pip line with `pip install -e ".[dev]"`. Single source of truth restored.
- Blast radius: a version bump in one file but not the other.
- Detection: `tests/test_smoke.py` does not cover this (static files differ
  legitimately); human review at Commit 2.
- Remediation (R-6): Commit 2 REPLACES the Dockerfile pip line with
  `pip install -e ".[dev]"` and deletes this entry.

## D-7. Magic / Netgen pins carried over unverified (MEDIUM)

- What: `8.3.456` / `1.5.270` are PREREQUISITES.md values re-stated, NOT
  live-verified on 2026-09-05 (unlike ngspice/KLayout). Stating them as
  defaults risks enshrining stale numbers.
- Blast radius: EDA build may fail to fetch exact tags; low blast radius
  because the EDA build resolves them against upstream before installing.
- Detection: EDA follow-up `git ls-remote --tags` for both repos first.
- Remediation (R-7): EDA follow-up amends the ARG defaults to the verified
  tags and records the ls-remote output.

## D-8. Windows host cannot run the gate natively (LOW, documented)

- What: stock Windows PowerShell has no `make` (verified 2026-09-05) and no
  host Python toolchain (no pytest/mypy/ruff/pre-commit/act). The
  fresh-clone story REQUIREs WSL2 Ubuntu (`wsl make setup`), where GNU Make
  4.3 + Docker 29.6.2 were verified present.
- Blast radius: a Windows-only stranger without WSL cannot run the gate.
  This matches PREREQUISITES.md (WSL2 mandatory) so it is a documented
  prerequisite, not a surprise — but it must stay in the stage brief.
- Remediation (R-8): none in code; `docs/stages/stage-0.md` section 4 carries
  the WSL-first sequence permanently.

## D-9. Big-bang integration risk if the follow-up slips (PROCESS, HIGH)

- What: every item above compounds if EDA work drifts into Stage 2. The
  layering saves 30–90 minutes and 3–10 GB today; the interest on that loan
  is a compressed debug surface later (ngspice build + PDK install + isolation
  proof failing simultaneously at Stage 2 kickoff).
- Rule: the EDA follow-up MUST land and go green BEFORE Stage 1G starts, and
  no Stage 2 task prompt is sent until R-1–R-4 are checked off. To-Do.md
  encodes this as a hard predecessor edge, not a suggestion.

## Expiry

This file closes when: (a) `--target eda` builds clean, (b) the libngspice
hello-netlist probe passes, (c) `nodeinfo.json` + image digest are recorded,
(d) CI has an eda job. Close = replace this file's body with a pointer to the
green run, keep the history in git.
