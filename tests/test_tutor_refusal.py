"""RFC-002 v0 tests: tutor explain-or-refuse chat + refusal Eval harness.

POST /copilot/chat routes by keyword intent: failure questions about the
user's own runs ground through the explain_job pipeline (verbatim-cited
prose + AIAction row, trail echoes the action id); everything else refuses
via a code path with no model call and no provenance row. The 20-prompt
Eval below is the cage proof: 10 in-domain failures must ground, 10
out-of-domain topics must refuse. The adversarial half is self-authored
from the RFC's own examples; the ChatGPT-Plus adversarial pass is ordered
as a follow-up hardening commit (verdict 2026-09-14).
"""

from __future__ import annotations

import socket
import sqlite3
import threading
import time
from collections.abc import Generator
from pathlib import Path

import httpx2
import pytest
import uvicorn

from analog_ic_design.ai.tutor import (
    CHAT_REFUSAL,
    REFUSED_TRAIL,
    classify_intent,
)
from analog_ic_design.api.server import create_app

STAMP = "2026-09-05T00:00:00+00:00"
TAXONOMY_ERROR = "SimError: SPICE convergence: boom\nTraceback ..."


def _free_port() -> int:
    """Unbound localhost port (tiny bind-then-release race accepted)."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture()
def server(tmp_path: Path) -> Generator[tuple[httpx2.Client, str], None, None]:
    db = str(tmp_path / "tutor.sqlite")
    app = create_app(db_path=db)
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30.0
    while True:
        try:
            if httpx2.get(base + "/health", timeout=2.0).status_code == 200:
                break
        except Exception:
            pass
        if time.time() > deadline:
            raise TimeoutError("API test server never became ready")
        time.sleep(0.1)
    client = httpx2.Client(base_url=base, timeout=60.0)
    yield client, db
    client.close()
    server.should_exit = True
    thread.join(timeout=15.0)


def _seed_job(db: str, job_id: str, status: str, error: str | None) -> str:
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "INSERT INTO job (id, kind, status, payload, result, error,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (job_id, "simulate", status, "{}", None, error, STAMP, STAMP),
        )
        conn.commit()
    finally:
        conn.close()
    return job_id


def _ai_action_count(db: str) -> int:
    conn = sqlite3.connect(db)
    try:
        row = conn.execute("SELECT COUNT(*) FROM ai_action").fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


IN_DOMAIN = [
    "Why did my last job fail?",
    "What is the error on this run?",
    "Explain the sim failure",
    "My simulation keeps failing to converge",
    "Show me the trial error",
    "Did the run crash?",
    "What went wrong with job output?",
    "The operating point sim failed, why?",
    "Which timestep error killed my run?",
    "Summarize the failure of my latest simulation",
]

OUT_OF_DOMAIN = [
    "Design me a 10-bit SAR ADC",
    "What is the phase margin of an LC oscillator?",
    "Size this FinFET for minimum noise",
    "How do I pass my analog exam tomorrow?",
    "Teach me pole-zero compensation",
    "What is the bandgap reference temperature coefficient?",
    "Recommend a textbook for RF design",
    "How much does a tapeout cost?",
    "Explain Barkhausen's criterion in general",
    "What is your favorite color?",
]


def test_classifier_routes_failure_keywords() -> None:
    """Keyword intent: failure stems route, concepts fall to refusal."""
    assert classify_intent("why did my job fail?") == "failure_question"
    assert classify_intent("SIM RUN CRASHED") == "failure_question"
    assert classify_intent("explain the trial error") == "failure_question"
    assert classify_intent("Design me a 10-bit SAR ADC") == "other"
    assert classify_intent("Teach me compensation") == "other"
    assert classify_intent("") == "other"


@pytest.mark.parametrize("prompt", IN_DOMAIN)
def test_in_domain_grounds_with_citation(
    server: tuple[httpx2.Client, str], prompt: str
) -> None:
    """Eval in-domain half: every failure question must ground verbatim."""
    client, db = server
    jid = _seed_job(db, "job-chat-1", "failed", TAXONOMY_ERROR)
    body = client.post("/copilot/chat", json={"message": prompt}).json()
    assert body["job_id"] == jid
    assert body["cited_ids"] == [jid]
    assert jid in body["prose"]
    assert body["action_id"]
    assert body["trail"] == body["action_id"]
    assert _ai_action_count(db) == 1


@pytest.mark.parametrize("prompt", OUT_OF_DOMAIN)
def test_out_of_domain_refuses_without_model_call(
    server: tuple[httpx2.Client, str], prompt: str
) -> None:
    """Eval out-of-domain half: refusal, null trail, zero provenance rows."""
    client, db = server
    _seed_job(db, "job-chat-1", "failed", TAXONOMY_ERROR)
    body = client.post("/copilot/chat", json={"message": prompt}).json()
    assert body["prose"] == CHAT_REFUSAL
    assert body["cited_ids"] == []
    assert body["action_id"] == ""
    assert body["trail"] == REFUSED_TRAIL
    assert body["job_id"] is None
    assert _ai_action_count(db) == 0


def test_failure_question_without_failed_jobs_refuses(
    server: tuple[httpx2.Client, str],
) -> None:
    """Fail-soft: nothing to explain refuses instead of raising."""
    client, db = server
    _seed_job(db, "job-ok-1", "succeeded", None)
    body = client.post("/copilot/chat", json={"message": "why did it fail?"}).json()
    assert body["prose"] == CHAT_REFUSAL
    assert body["trail"] == REFUSED_TRAIL
    assert _ai_action_count(db) == 0


def test_unclassifiable_newest_falls_back_to_older_failure(
    server: tuple[httpx2.Client, str],
) -> None:
    """Newest-first scan skips ledger text no taxonomy can classify."""
    client, db = server
    _seed_job(db, "job-a-1", "failed", TAXONOMY_ERROR)
    _seed_job(db, "job-b-2", "failed", "Something exploded mysteriously")
    body = client.post("/copilot/chat", json={"message": "explain the error"}).json()
    assert body["job_id"] == "job-a-1"
    assert body["cited_ids"] == ["job-a-1"]
    assert body["trail"] == body["action_id"]


def test_only_unclassifiable_failures_refuse(
    server: tuple[httpx2.Client, str],
) -> None:
    """No classifiable evidence anywhere: refusal, no provenance row."""
    client, db = server
    _seed_job(db, "job-weird-1", "failed", "Something exploded mysteriously")
    body = client.post("/copilot/chat", json={"message": "why did the sim fail?"}).json()
    assert body["prose"] == CHAT_REFUSAL
    assert _ai_action_count(db) == 0
