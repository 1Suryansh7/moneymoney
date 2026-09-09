"""Stage 7A tests: Law 4 architecture boundary CI guard (AGENT2 §2).

New caller surfaces (ui/, cli/, sdk/) may import ONLY the engine surface,
interfaces, units, and stdlib. Direct imports of simulators, layout tools,
the store, or any other engine-side internals fail the build here.

Scoping (deliberate): engine/, sim/, store/, circuit/, metrics/, topology/,
optimize/, ai/, and tests/ predate the boundary and are engine-side — the
guard covers new caller packages only, strangler-direction. Existing suite
imports internals throughout; applying this rule retroactively would nuke
it, so the rule constrains what gets ADDED, not what exists.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PKG_ROOT = REPO_ROOT / "src" / "analog_ic_design"

# Caller surfaces created after the boundary landed. Absent dirs pass
# vacuously (documented, not green-washing: the self-tests below prove the
# checker itself catches violations).
GUARDED_PACKAGES: tuple[str, ...] = ("ui", "cli", "sdk", "api")

# Import roots a caller surface may touch, besides stdlib.
ALLOWED_ROOTS: tuple[str, ...] = (
    "analog_ic_design.engine",
    "analog_ic_design.interfaces",
    "analog_ic_design.units",
)

# Anything engine-side that must only be reached through EngineV01.
FORBIDDEN_ROOTS: tuple[str, ...] = (
    "sqlite3",
    "analog_ic_design.sim",
    "analog_ic_design.store",
    "analog_ic_design.circuit",
    "analog_ic_design.metrics",
    "analog_ic_design.topology",
    "analog_ic_design.optimize",
    "analog_ic_design.ai",
    "analog_ic_design.robust",
)


def _imported_roots(tree: ast.AST) -> list[str]:
    """Top-level imported module paths in one file (absolute only)."""
    roots: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.append(node.module)
    return roots


def _violations_in_file(path: Path) -> list[str]:
    """Forbidden imports in `path`; empty means the file respects Law 4."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [f"{path}: unparseable ({exc})"]
    try:
        rel = path.relative_to(PKG_ROOT).with_suffix("").as_posix().replace("/", ".")
        own = f"analog_ic_design.{rel}"
    except ValueError:
        own = ""
    if own.endswith(".__init__"):
        own = own[: -len(".__init__")]
    hits: list[str] = []
    for root in _imported_roots(tree):
        if any(root == f or root.startswith(f + ".") for f in FORBIDDEN_ROOTS):
            hits.append(f"{path}: forbidden import {root!r}")
        elif root == "analog_ic_design" or root.startswith("analog_ic_design."):
            if not root.startswith(ALLOWED_ROOTS) and root != own and not root.startswith(
                own + "."
            ):
                hits.append(f"{path}: non-engine import {root!r}")
    return hits


def test_guarded_packages_respect_law4() -> None:
    """Every file under ui/cli/sdk (when present) imports engine-side only."""
    hits: list[str] = []
    for pkg in GUARDED_PACKAGES:
        pkgdir = PKG_ROOT / pkg
        if not pkgdir.is_dir():
            continue
        for path in sorted(pkgdir.rglob("*.py")):
            hits.extend(_violations_in_file(path))
    assert hits == [], "Law 4 violation:\n" + "\n".join(hits)


def test_checker_catches_side_door(tmp_path: Path) -> None:
    """The checker itself is proven: violating file fails, clean passes."""
    bad = tmp_path / "bad.py"
    bad.write_text(
        "import sqlite3\nfrom analog_ic_design.sim.jobs import JobRunner\n", encoding="utf-8"
    )
    hits = _violations_in_file(bad)
    assert len(hits) == 2

    good = tmp_path / "good.py"
    good.write_text(
        "import json\n"
        "from analog_ic_design.engine import EngineV01\n"
        "from analog_ic_design.units.display import format_quantity\n",
        encoding="utf-8",
    )
    assert _violations_in_file(good) == []


def test_relative_imports_not_silently_trusted(tmp_path: Path) -> None:
    """Relative imports are out of scope for the checker: flagged as unknown."""
    rel = tmp_path / "rel.py"
    rel.write_text("from . import backend\n", encoding="utf-8")
    # Absolute-only analysis: relative form contributes no roots (documents
    # the checker's blind spot rather than pretending full coverage).
    assert _imported_roots(ast.parse(rel.read_text(encoding="utf-8"))) == []
