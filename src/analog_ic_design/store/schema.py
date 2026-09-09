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

SCHEMA_VERSION: Final = 9

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

_MIGRATION_3 = """
CREATE TABLE specification (
    id TEXT PRIMARY KEY,
    cell_id TEXT NOT NULL REFERENCES cell(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE constraint_rule (
    id TEXT PRIMARY KEY,
    specification_id TEXT NOT NULL REFERENCES specification(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('hard', 'soft', 'weighted')),
    metric TEXT NOT NULL,
    operator TEXT NOT NULL CHECK (operator IN ('>=', '<=', '=')),
    threshold REAL NOT NULL,
    tolerance REAL NOT NULL,
    priority INTEGER NOT NULL,
    weight REAL,
    created_at TEXT NOT NULL
);
CREATE TABLE error_record (
    id TEXT PRIMARY KEY,
    cell_id TEXT REFERENCES cell(id) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK (category IN (
        'syntax', 'schema', 'netlist', 'spice_convergence', 'operating_point',
        'constraint', 'pvt', 'monte_carlo', 'drc', 'lvs', 'pex', 'post_layout'
    )),
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

_MIGRATION_4 = """
ALTER TABLE model_binding ADD COLUMN kind TEXT CHECK (kind IN ('mosfet', 'subckt'));
"""

_MIGRATION_5 = """
CREATE TABLE testbench (
    id TEXT PRIMARY KEY,
    cell_id TEXT NOT NULL REFERENCES cell(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE analysis (
    id TEXT PRIMARY KEY,
    testbench_id TEXT NOT NULL REFERENCES testbench(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('tran', 'dc', 'ac', 'op')),
    parameters TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE job (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN (
        'pending', 'running', 'succeeded', 'failed', 'cancelled'
    )),
    payload TEXT NOT NULL,
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_MIGRATION_6 = """
CREATE TABLE measurement (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES job(id) ON DELETE CASCADE,
    metric_id TEXT NOT NULL,
    value REAL NOT NULL,
    units TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

_MIGRATION_7 = """
CREATE TABLE experiment (
    id TEXT PRIMARY KEY,
    study TEXT NOT NULL,
    trial INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('trial', 'baseline')),
    status TEXT NOT NULL CHECK (status IN ('succeeded', 'failed')),
    corner TEXT NOT NULL DEFAULT 'nominal',
    parameters TEXT NOT NULL,
    metrics TEXT NOT NULL,
    verdict TEXT NOT NULL,
    reproducibility_id TEXT NOT NULL,
    seed INTEGER NOT NULL,
    job_id TEXT REFERENCES job(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
);
"""

_MIGRATION_8 = """
CREATE TABLE ai_action (
    id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL CHECK (
        action_type IN (
            'explain_failure', 'narrate_optimization',
            'propose_topology', 'propose_sizing'
        )
    ),
    model_provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT,
    prompt_version TEXT NOT NULL,
    input_context_hash TEXT NOT NULL,
    output_hash TEXT NOT NULL,
    source_artifacts TEXT NOT NULL,
    resulting_design_revision TEXT,
    human_decision TEXT NOT NULL CHECK (
        human_decision IN ('accept', 'reject', 'edited', 'n/a')
    ) DEFAULT 'n/a',
    token_cost REAL,
    latency_s REAL,
    created_at TEXT NOT NULL
);
"""

_MIGRATION_9 = """
CREATE TABLE checkpoint_registry (
    id TEXT PRIMARY KEY,
    checkpoint_key TEXT NOT NULL,
    trigger TEXT NOT NULL,
    required_evidence TEXT NOT NULL,
    verification_action TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('blocking', 'advisory')),
    reviewer TEXT,
    decision TEXT NOT NULL CHECK (
        decision IN ('confirmed', 'confirmed_with_note', 'rejected', 'insufficient', 'pending')
    ) DEFAULT 'pending',
    decided_at TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE design_state (
    id TEXT PRIMARY KEY,
    cell_id TEXT NOT NULL UNIQUE REFERENCES cell(id) ON DELETE CASCADE,
    state TEXT NOT NULL CHECK (state IN (
        'DRAFT', 'SIMULATION_READY', 'NOMINAL', 'PVT', 'MC', 'LAYOUT_READY',
        'PHYSICAL_VERIFIED', 'POST_LAYOUT_VALIDATED', 'REVIEW_READY', 'RELEASED'
    )),
    design_revision TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

MIGRATIONS: Final = (
    (1, _MIGRATION_1),
    (2, _MIGRATION_2),
    (3, _MIGRATION_3),
    (4, _MIGRATION_4),
    (5, _MIGRATION_5),
    (6, _MIGRATION_6),
    (7, _MIGRATION_7),
    (8, _MIGRATION_8),
    (9, _MIGRATION_9),
)


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
