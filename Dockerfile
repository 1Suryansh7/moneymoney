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
ARG UBUNTU_IMAGE=ubuntu:22.04
ARG NGSPICE_VERSION=47
ARG KLAYOUT_VERSION=0.30.12
ARG KLAYOUT_DEB_MD5=6dfffa50f385881768dee30bdc759608
ARG MAGIC_VERSION=8.3.683
ARG NETGEN_VERSION=1.5.323
ARG OPEN_PDKS_GIT_REF=1689ac3f2dc763876eaf967227c7dfe831b031ae
ARG OPEN_PDKS_GIT_URL=https://github.com/RTimothyEdwards/open_pdks.git

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
# EDA recipe (human-approved 2026-09-05, "latest everything"). Pin sources:
# ngspice-47 (latest stable — verified live at ng-spice-rework/47/; 46 exists
# only under old-releases/), KLayout 0.30.12 (Ubuntu-22 .deb MD5 verified
# on klayout.de), Magic 8.3.683 + Netgen 1.5.323 (live latest tags, observed
# via ls-remote), open_pdks frozen at the verified HEAD hash above.
# open_pdks flag vocabulary was verified against `scripts/configure` AT that
# commit (not just --help, which omits the `--enable-sky130-pdk` master
# switch even though the code honors it via `enable_sky130_pdk` — confirmed
# by reading the generated script; the install docs agree). Without that
# switch, ENABLED_TECHS stays empty and `make` stages nothing (observed).
# Libraries toggle individually; gf180 drops via one master switch.
# PDK scope discipline (AGENTS.md section 12): sky130A primitive devices +
# KLayout tech overlay only — never standard-cell libraries.
# NOTE: `base` above is Debian bookworm (python slim) by design — it runs the
# Python gate only. This stage roots at Ubuntu 22.04 (upstream build docs for
# ngspice/open_pdks target Ubuntu, not Debian), so the two stages
# intentionally have different OS roots.

FROM ${UBUNTU_IMAGE} AS eda

ARG NGSPICE_VERSION
ARG KLAYOUT_VERSION
ARG KLAYOUT_DEB_MD5
ARG MAGIC_VERSION
ARG NETGEN_VERSION
ARG OPEN_PDKS_GIT_REF
ARG OPEN_PDKS_GIT_URL

LABEL eda.ngspice="${NGSPICE_VERSION}" \
      eda.klayout="${KLAYOUT_VERSION}" \
      eda.magic="${MAGIC_VERSION}" \
      eda.netgen="${NETGEN_VERSION}" \
      eda.open_pdks="${OPEN_PDKS_GIT_REF}" \
      eda.sky130="A-primitive-only"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PDK_ROOT=/usr/local/share/pdk

WORKDIR /workspace

# 1. OS toolchain. Python note: jammy archives carry only a 3.11.0~rc1
#    pre-release (rejected for a pinned toolchain), hence deadsnakes.
RUN apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common gnupg curl ca-certificates git \
        build-essential autoconf automake libtool bison flex gperf m4 \
        libx11-dev libxaw7-dev libreadline-dev \
        tcl-dev tk-dev python3-minimal \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3.11-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. ngspice source build with the shared library (Stage 2 libngspice target).
RUN curl -sL --retry 5 --retry-all-errors -o /tmp/ngspice.tar.gz \
        "https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/${NGSPICE_VERSION}/ngspice-${NGSPICE_VERSION}.tar.gz" \
    && mkdir -p /tmp/ngspice && tar xzf /tmp/ngspice.tar.gz -C /tmp/ngspice --strip-components=1 \
    && cd /tmp/ngspice \
    && ./configure --with-ngshared --enable-xspice --enable-openmp --without-x --prefix=/usr/local \
    && make -j"$(nproc)" && make install && ldconfig \
    && rm -rf /tmp/ngspice /tmp/ngspice.tar.gz

# 2b. ngspice CLI from the same source (the ngshared build yields lib-only;
# observed: no `ngspice` binary linked). CLI is the human debugging tool and
# the deck-level cross-check for Stage 2 libngspice results.
RUN curl -sL --retry 5 --retry-all-errors -o /tmp/ngspice-cli.tar.gz \
        "https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/${NGSPICE_VERSION}/ngspice-${NGSPICE_VERSION}.tar.gz" \
    && mkdir -p /tmp/ngspice-cli && tar xzf /tmp/ngspice-cli.tar.gz -C /tmp/ngspice-cli --strip-components=1 \
    && cd /tmp/ngspice-cli \
    && ./configure --enable-xspice --enable-openmp --without-x --prefix=/usr/local \
    && make -j"$(nproc)" && make install \
    && rm -rf /tmp/ngspice-cli /tmp/ngspice-cli.tar.gz

# 3. Magic from the verified tag.
RUN curl -sL --retry 5 --retry-all-errors -o /tmp/magic.tar.gz \
        "https://github.com/RTimothyEdwards/magic/archive/refs/tags/${MAGIC_VERSION}.tar.gz" \
    && mkdir -p /tmp/magic && tar xzf /tmp/magic.tar.gz -C /tmp/magic --strip-components=1 \
    && cd /tmp/magic && ./configure --prefix=/usr/local \
    && make -j"$(nproc)" && make install \
    && rm -rf /tmp/magic /tmp/magic.tar.gz

# 4. Netgen from the verified tag.
RUN curl -sL --retry 5 --retry-all-errors -o /tmp/netgen.tar.gz \
        "https://github.com/RTimothyEdwards/netgen/archive/refs/tags/${NETGEN_VERSION}.tar.gz" \
    && mkdir -p /tmp/netgen && tar xzf /tmp/netgen.tar.gz -C /tmp/netgen --strip-components=1 \
    && cd /tmp/netgen && ./configure --prefix=/usr/local \
    && make -j"$(nproc)" && make install \
    && rm -rf /tmp/netgen /tmp/netgen.tar.gz

# 5. KLayout exact-version .deb, MD5-verified. NOTE: klayout.org serves at
#    ~65 KB/s from here (observed 2026-09-05) — expect ~17 min for this step.
RUN curl -sL --retry 8 --retry-all-errors --retry-delay 15 -o /tmp/klayout.deb \
        "https://www.klayout.org/downloads/Ubuntu-22/klayout_${KLAYOUT_VERSION}-1_amd64.deb" \
    && echo "${KLAYOUT_DEB_MD5}  /tmp/klayout.deb" | md5sum -c - \
    && apt-get update && apt-get install -y /tmp/klayout.deb && rm -f /tmp/klayout.deb \
    && rm -rf /var/lib/apt/lists/*

# 6. sky130A primitive-only PDK at the frozen open_pdks commit. io dropped per
#    primitive-only policy — the ngspice model probe in step 8 proves fd_pr
#    suffices; re-enable io with a recorded reason if that probe ever fails.
RUN if [ "${OPEN_PDKS_GIT_REF}" = "UNPINNED" ] || [ -z "${OPEN_PDKS_GIT_REF}" ]; then \
        echo "ERROR: OPEN_PDKS_GIT_REF must be a frozen commit hash." >&2; exit 1; \
    fi \
    && git init /tmp/open_pdks && cd /tmp/open_pdks \
    && git remote add origin "${OPEN_PDKS_GIT_URL}" \
    && git fetch --depth 1 origin "${OPEN_PDKS_GIT_REF}" && git checkout FETCH_HEAD \
    && ./configure --prefix=/usr/local \
        --enable-sky130-pdk --disable-gf180mcu-pdk \
        --disable-io-sky130 --disable-sc-hs-sky130 --disable-sc-ms-sky130 \
        --disable-sc-ls-sky130 --disable-sc-lp-sky130 --disable-sc-hd-sky130 \
        --disable-sc-hdll-sky130 --disable-sc-hvl-sky130 --disable-alpha-sky130 \
        --disable-xschem-sky130 --disable-precheck-sky130 \
    && make -j"$(nproc)" && make install \
    && mkdir -p /pdk-record && cp /usr/local/share/pdk/sky130A/.config/nodeinfo.json /pdk-record/ \
    && rm -rf /tmp/open_pdks

# 7. Python package (same install as `base`, so Stage 2 workers find the API
#    next to libngspice).
COPY pyproject.toml ./
COPY src/ ./src/
RUN python3.11 -m ensurepip --upgrade && python3.11 -m pip install --upgrade pip \
    && python3.11 -m pip install -e ".[dev]" \
    && python3.11 -m pip freeze > /image-requirements-frozen.txt

COPY . .

# 8. EDA acceptance probes — fail-closed: any breach fails the image build.
#    (Magic/netgen assert presence + clean startup; their functional proof is
#    owned by Stage 8, which exercises real DRC/LVS decks.)
RUN ngspice --version | grep -q "ngspice-${NGSPICE_VERSION}" \
    && test -f /usr/local/lib/libngspice.so \
    && python3.11 -c "import ctypes; ctypes.CDLL('/usr/local/lib/libngspice.so'); print('libngspice loads OK')" \
    && klayout -b -v 2>&1 | grep -q "${KLAYOUT_VERSION}" \
    && printf 'quit\n' | timeout 120 magic -dnull -noconsole > /tmp/magic-banner.txt 2>&1 \
    && command -v netgen \
    && test -f /usr/local/share/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice \
    && printf '* rc hello\nV1 in 0 DC 0 PULSE(0 1.8 1n 1n 1n 10n 20n)\nR1 in out 1k\nC1 out 0 1p\n.tran 0.1n 30n\n.control\nrun\nprint v(out) > /tmp/hello.out\n.endc\n.end\n' > /tmp/hello.cir \
    && ngspice -b /tmp/hello.cir > /dev/null 2>&1 \
    && test -s /tmp/hello.out && grep -q "out" /tmp/hello.out \
    && { echo "=== EDA versions ==="; echo "python3.11: $(python3.11 --version 2>&1)"; \
         ngspice --version | head -1; klayout -b -v 2>&1 | head -2; \
         echo "--- magic banner ---"; head -3 /tmp/magic-banner.txt; \
         echo "open_pdks_ref=${OPEN_PDKS_GIT_REF}"; \
       } | tee /image-eda-versions.txt \
    && rm -f /tmp/hello.cir /tmp/hello.out /tmp/magic-banner.txt

CMD ["python3.11", "-m", "pytest", "-q"]
