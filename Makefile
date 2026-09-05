# Stage 0 — the ONLY three targets the plan allows: setup, test, run-example.
# Lint (ruff) and typecheck (mypy) run INSIDE `test` so the gate stays one
# command with zero extra surface. Container is the authority: every recipe
# line executes inside the pinned base image, never on host Python.
# Windows host: `make` lives in WSL2 Ubuntu (`wsl make setup && wsl make test`).

IMAGE := analog-ic-platform:stage0-base

setup:
	docker compose build app
	docker compose run --rm app python -m pytest -q
	docker compose run --rm app python examples/smoke.py

test:
	docker compose run --rm app python -m ruff check .
	docker compose run --rm app python -m mypy .
	docker compose run --rm app python -m pytest -q

run-example:
	docker compose run --rm app python examples/smoke.py
