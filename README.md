# Ecom Research System

Internal ecommerce product research and decision system. One user, one machine,
no cloud. The architecture and roadmap live in [`docs/FOUNDATION.md`](docs/FOUNDATION.md)
— read that first.

**Current state: Milestone M0** — the skeleton boots. There is a database, a
health endpoint, migrations, logging, and tests. No external providers, no
scoring, no AI yet (that's by design — see the phased plan in the foundation doc).

---

## What you need installed

- **Docker Desktop** (Mac/Windows) or Docker Engine + Compose (Linux)
- **uv** — the Python tool manager: <https://docs.astral.sh/uv/getting-started/installation/>
- **Git**

That's it. uv downloads the right Python version for you automatically.

## First-time setup (do this once)

Open a terminal in this folder and run:

```bash
# 1. Create your private config file from the template
cp .env.example .env

# 2. Open .env in any text editor and change POSTGRES_PASSWORD
#    to something of your own. Save the file. Never commit .env.

# 3. Install the Python dependencies
uv sync
```

## Starting the system

```bash
docker compose up --build
```

Wait until the logs settle (first run takes a few minutes — it downloads
PostgreSQL and builds the app). Then open:

- **<http://localhost:8000/health>** — should show `{"status":"ok","db":"connected"}`
- **<http://localhost:8000/docs>** — the interactive API documentation

To stop everything: press `Ctrl+C` in that terminal, or run `docker compose down`.
Your data survives restarts (it lives in a Docker volume). To wipe the database
completely: `docker compose down -v`.

## Running the tests

The tests need a running database. Easiest path — start only the database:

```bash
docker compose up -d db
uv run pytest
```

Everything should be green. Add `-v` for a detailed list: `uv run pytest -v`.

## Checking code style

```bash
uv run ruff check .
```

## Database migrations (for later reference)

Migrations are how the database schema changes safely over time. They are
applied automatically every time the API container starts. To run them by hand:

```bash
uv run alembic upgrade head      # apply all pending migrations
uv run alembic downgrade -1     # undo the most recent one
```

## Project layout

```
app/
  core/            settings, logging, errors, database session
  api/             HTTP endpoints (just /health for now)
  ingestion/       owns: sources, collection_runs, raw_observations (append-only)
  catalog/         owns: candidates (products come in a later phase)
  providers/       stub — external source adapters (gated by access spikes)
  scoring/         stub — deterministic scores
  analysis/        stub — LLM conclusions
  recommendation/  stub — final reports
migrations/        database schema history (Alembic)
tests/             automated tests
docs/FOUNDATION.md the architecture document
docs/providers/    provider access spike records (none yet)
```

## Troubleshooting

- **"port is already allocated"** — something else on your machine uses port
  5432 or 8000. Stop it, or ask your assistant to change the port mapping in
  `docker-compose.yml`.
- **`/health` says `degraded`** — the database isn't up yet or the
  `DATABASE_URL` in your `.env` is wrong. Run `docker compose up -d db` and
  retry.
- **Tests complain about DATABASE_URL** — make sure `.env` exists; then run
  tests as `uv run --env-file .env pytest`.
