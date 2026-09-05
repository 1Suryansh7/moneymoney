"""Stage 0 Commit 1 tests: packaging contract only (no design logic exists yet).

Every assertion is a static, deterministic file/content check — no network,
no simulator, no floating point. Failure taxonomy: Schema (packaging
contract breach); each message names the breached file and rule.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from check_models import ALIASES, resolve_aliases

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_models_config_declares_both_capability_aliases() -> None:
    config_path = REPO_ROOT / "config" / "models.json"
    assert config_path.is_file(), "Schema: config/models.json is missing"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    for alias in ALIASES:
        assert alias in data, f"Schema: {alias} missing from config/models.json"


def test_alias_resolver_reports_both_aliases() -> None:
    resolved = resolve_aliases()
    for alias in ALIASES:
        assert alias in resolved, f"Schema: resolver dropped {alias}"
        value, source = resolved[alias]
        assert isinstance(value, str) and value, f"Schema: {alias} resolved empty"
        assert source in ("env", "config", "missing"), f"Schema: bad source for {alias}"


def test_makefile_has_exactly_three_targets() -> None:
    text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    targets = re.findall(r"^(?!#)([A-Za-z0-9_.-]+):", text, flags=re.MULTILINE)
    assert targets == ["setup", "test", "run-example"], (
        f"Schema: Makefile must define exactly [setup, test, run-example], found {targets}"
    )


def test_dockerfile_pin_policy() -> None:
    lines = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
    # Policy governs image references, not prose: strip full-line comments so a
    # comment naming the forbidden pattern cannot false-positive (or mask).
    code = "\n".join(
        line for line in lines if not line.lstrip().startswith("#")
    )
    assert ":latest" not in code, "Schema: Dockerfile pins a ':latest' image tag"
    for pin in ("python:3.11", "NGSPICE_VERSION=46", "KLAYOUT_VERSION=0.30.12"):
        assert pin in code, f"Schema: Dockerfile missing declared pin {pin}"


def test_compose_defines_app_service() -> None:
    text = (REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert re.search(r"^\s+app:", text, flags=re.MULTILINE), (
        "Schema: docker-compose.yml missing the `app` service"
    )


def test_gitattributes_forces_lf_for_netlist_artifacts() -> None:
    text = (REPO_ROOT / ".gitattributes").read_text(encoding="utf-8")
    for pattern in ("*.cir text eol=lf", "*.sp text eol=lf", "*.golden text eol=lf"):
        assert pattern in text, (
            f"Schema: .gitattributes missing LF guard '{pattern}' "
            "(Stage 1 byte-identical netlist comparisons depend on it)"
        )
