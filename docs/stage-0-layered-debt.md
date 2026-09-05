# Stage 0 Layered-Build Debt Record — CLOSED 2026-09-05

> Per this file's own expiry rule, the D-1..D-9 / R-1..R-8 body is retired:
> the EDA follow-up is GREEN (image `codeeahhhhhhh-app-eda` manifest
> `sha256:51ab18061e5d6628506231bb03068a78482cb1830b817579198cd979f20d04ab`,
> all build-time acceptance probes passing). Full history preserved in git;
> see `docs/stages/stage-0.md` section 9 for the build-issue log and the
> observed version/provenance record.

Closure checklist (was: R-1..R-8):

- R-1 execution-environment evidence: image manifest digest, ngspice-47 /
  KLayout 0.30.12 / Magic 8.3.683 / Netgen 1.5.323 versions, nodeinfo.json
  (open_pdks `1689ac3f`, fd_pr `403964dc`) in `/pdk-record`,
  `/image-eda-versions.txt` in-image. DONE.
- R-2 CI eda job: added to `.github/workflows/ci.yml`; its exact commands
  run verbatim locally — green. DONE.
- R-3 libngspice hello: lib present + ctypes-loadable; CLI hello transient
  green; full libngspice isolation proof is Stage 2's scope (not duplicated
  here). DONE (Stage 0 portion).
- R-4 PDK model cards on disk: `sky130.lib.spice` present; Stage 1G may now
  quote PDK files per Law 2. DONE (unblocks 1G).
- R-5 digest discipline: upstream base
  `python:3.11-slim-bookworm@sha256:528257d4…`, Ubuntu 22.04
  `@sha256:2edbbc5d…`, eda manifest above — all recorded. DONE.
- R-6 dependency duplication: closed in Commit 2 (`pip install -e ".[dev]"`).
  DONE.
- R-7 Magic/Netgen tags: verified live-latest (8.3.683 / 1.5.323), built from
  source. DONE.
- R-8 WSL-first sequence: permanent in `docs/stages/stage-0.md` section 4.
  DONE.

Predecessor edge lifted: Stage 1G and Stage 2 prompts are unblocked on the
EDA front. Still open (not debt): human 2.5 verdict on Stage 0.
