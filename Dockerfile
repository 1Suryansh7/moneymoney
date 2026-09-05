# syntax=docker/dockerfile:1

# Stage 0 — layered build (human-approved; see docs/stage-0-layered-debt.md).
#
#   target `base` : pinned Python + test toolchain. BUILT and CI-verified now.
#   target `eda`  : full EDA toolchain pins DECLARED below; the recipe build is
#                   PROVEN in the Stage-0 EDA follow-up, BEFORE Stage 1G/Stage 2
#                   need libngspice or PDK model cards. Nothing in `base` runs a
#                   simulation, so nothing can silently depend on EDA yet.
#
# Pin policy: exact tags, never `:latest`. Image digests are recorded at build
# time (`docker inspect --format='{{.RepoDigests}}'`) into the build log and the
# Stage-0 summary — tags are the contract, digests are the proof.

ARG PYTHON_IMAGE=python:3.11-slim-bookworm

# ---------------------------------------------------------------- base ------
FROM ${PYTHON_IMAGE} AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

# Single source of truth: pyproject.toml [project.optional-dependencies] dev.
# (Commit 1 used an explicit duplicate list because src/ did not exist yet;
# debt doc D-6 closed here.)
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --upgrade pip \
    && pip install -e ".[dev]" \
    && pip freeze > /image-requirements-frozen.txt

COPY . .

CMD ["python", "-m", "pytest", "-q"]

# ---------------------------------------------------------------- eda -------
# DECLARED pin contract for the EDA follow-up. NOT built or verified yet.
# Human-approved refresh (2026-09-05): ngspice-46 (stable, Mar 2026) and
# KLayout 0.30.12 (hotfix, Aug 2026) supersede the stale PREREQUISITES.md
# values (ngspice-42/43, KLayout 0.28.x). Magic/Netgen keep their
# PREREQUISITES.md values as UNVERIFIED defaults until the EDA build proves
# them; open_pdks is fail-closed UNPINNED until a human freezes a commit hash.
# NOTE: `base` above is Debian bookworm (python slim) by design — it runs the
# Python gate only. The EDA follow-up roots its stage at Ubuntu 22.04 below
# (upstream build docs for ngspice/open_pdks target Ubuntu, not Debian), so
# the two stages intentionally have different OS roots.
ARG UBUNTU_IMAGE=ubuntu:22.04
ARG NGSPICE_VERSION=46
ARG KLAYOUT_VERSION=0.30.12
ARG MAGIC_VERSION=8.3.456
ARG NETGEN_VERSION=1.5.270
ARG OPEN_PDKS_GIT_REF=UNPINNED
# PDK scope discipline (AGENTS.md section 12): primitive devices only for
# Stage 1 — never the full multi-GB standard-cell library.
ARG SKY130_VARIANTS=A
ARG SKY130_EXTRA_LIBS=none

FROM base AS eda

RUN if [ "$OPEN_PDKS_GIT_REF" = "UNPINNED" ]; then \
        echo "ERROR: OPEN_PDKS_GIT_REF is UNPINNED." \
             "Freeze a verified open_pdks commit hash (see docs/stage-0-layered-debt.md R-1)" \
             "and rebuild with --build-arg OPEN_PDKS_GIT_REF=<sha>." >&2; \
        exit 1; \
    fi

# Full recipe (ngspice --with-ngshared source build, KLayout/Magic/Netgen
# installs, open_pdks sky130A primitive-only build, PDK nodeinfo.json capture)
# lands in the EDA follow-up commit. This stub exists only so the pin contract
# above is reviewable in one place before that build runs.
RUN echo "eda recipe pending (pins declared, build unverified)" \
    && echo "ngspice=${NGSPICE_VERSION} klayout=${KLAYOUT_VERSION}" \
       "magic=${MAGIC_VERSION} netgen=${NETGEN_VERSION}" \
       "open_pdks=${OPEN_PDKS_GIT_REF} sky130=${SKY130_VARIANTS}"
