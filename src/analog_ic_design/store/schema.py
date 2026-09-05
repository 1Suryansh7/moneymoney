"""SQLite schema + versioned migrations (Stage 1 Commit 1B).

Scope (deliberate): the migration framework plus the structural circuit
tables (Project → Library → Cell → Symbol/Instance/Port/Net) and two
existence-only tables (DesignRevision, Artifact). Behavior-owned tables land
with the commits that implement their semantics and tests:

- 1E (compiler): Parameter, Technology, ModelBinding
- 1F (validator): Specification, Constraint, ErrorRecord
- Stage 2: Job, Testbench, Analysis
- Stages 3/4: Measurement, Experiment (plan-explicit exclusion)

Rules: migrations are append-only and additive (never edit a landed
migration — add a new version). Every connection enforces
`PRAGMA foreign_keys = ON`. Ids are opaque hex strings (`new_id`); timestamps
are caller-supplied ISO-8601 text (deterministic tests, no hidden clocks).
Name-uniqueness is a 1F *validation* semantic (reported with taxonomy), not
a schema constraint — the schema stays permissive here on purpose.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

SCHEMA_VERSION: Final = 2

_MIGRATION_1 = """
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
CREATE TABLE project (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE library (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES project(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE cell (
    id TEXT PRIMARY KEY,
    library_id TEXT NOT NULL REFERENCES library(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE symbol (
    id TEXT PRIMARY KEY,
    cell_id TEXT NOT NULL UNIQUE REFERENCES cell(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE instance (
    id TEXT PRIMARY KEY,
    cell_id TEXT NOT NULL REFERENCES cell(id) ON DELETE CASCADE,
    symbol_id TEXT NOT NULL REFERENCES symbol(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE net (
    id TEXT PRIMARY KEY,
    cell_id TEXT NOT NULL REFERENCES cell(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE port (
    id TEXT PRIMARY KEY,
    cell_id TEXT REFERENCES cell(id) ON DELETE CASCADE,
    instance_id TEXT REFERENCES instance(id) ON DELETE CASCADE,
    net_id TEXT REFERENCES net(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    CHECK ((cell_id IS NULL) != (instance_id IS NULL))
);
CREATE TABLE design_revision (
    id TEXT PRIMARY KEY,
    parent_id TEXT REFERENCES design_revision(id) ON DELETE RESTRICT,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE artifact (
    id TEXT PRIMARY KEY,
    design_revision_id TEXT REFERENCES design_revision(id) ON DELETE SET NULL,
    path TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

_MIGRATION_2 = """
CREATE TABLE technology (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE REFERENCES project(id) ON DELETE CASCADE,
    pdk_id TEXT NOT NULL,
    pdk_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE model_binding (
    id TEXT PRIMARY KEY,
    technology_id TEXT NOT NULL REFERENCES technology(id) ON DELETE CASCADE,
    device_symbol TEXT NOT NULL,
    model_name TEXT NOT NULL,
    pin_order TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE parameter (
    id TEXT PRIMARY KEY,
    instance_id TEXT NOT NULL REFERENCES instance(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    value REAL NOT NULL,
    created_at TEXT NOT NULL
);
"""

MIGRATIONS: Final = ((1, _MIGRATION_1), (2, _MIGRATION_2))


def new_id() -> str:
    """Return an opaque 32-hex-char id (uuid4; randomness lives here, nowhere else)."""
    return uuid.uuid4().hex


def utcnow_iso() -> str:
    """Current UTC time as ISO-8601 text (migration bookkeeping only)."""
    return datetime.now(UTC).isoformat()


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    """Open a database with foreign-key enforcement ON (never the off default)."""
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Return the highest applied migration version (0 = nothing applied)."""
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'schema_version'"
    ).fetchone()
    if tables is None:
        return 0
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return int(row[0]) if row[0] is not None else 0


def migrate(conn: sqlite3.Connection) -> int:
    """Apply pending migrations in order; idempotent; returns landed version."""
    current = get_schema_version(conn)
    for version, sql in MIGRATIONS:
        if version > current:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                (version, utcnow_iso()),
            )
            current = version
    conn.commit()
    return current
