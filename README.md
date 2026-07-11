# Ecom Research System

Internal ecommerce product research and decision system. One user, one machine,
no cloud. The architecture and roadmap live in [`docs/FOUNDATION.md`](docs/FOUNDATION.md)
— read that first.

**Current state: Milestone M1** — a working research notebook. You can register
product candidates, attach evidence (notes + URLs) to them, and read it all
back. No external providers, no scoring, no AI yet (that's by design — see the
phased plan in the foundation doc).

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

## Using it as a research notebook

Everything happens in your browser at **<http://localhost:8000/docs>**. Each
endpoint has a "Try it out" button that turns it into a form.

1. **Register a product candidate.** Open `POST /candidates`, click *Try it
   out*, and fill in the JSON — only `name` is required:
   ```json
   {"name": "LED Dog Collar", "niche": "pets", "notes": "seen twice this week"}
   ```
   Press *Execute*. The response includes an `id` — that's your candidate.
2. **Attach evidence whenever you spot something.** Open
   `POST /candidates/{candidate_id}/observations`, paste the candidate's `id`,
   and record what you saw, with the URL:
   ```json
   {
     "payload": {"note": "8 advertisers running near-identical creatives"},
     "source_url": "https://www.facebook.com/ads/library/?q=led%20dog%20collar"
   }
   ```
   `payload` is free-form JSON — write whatever you observed. Evidence is
   **permanent**: there is deliberately no way to edit or delete it through
   the app, so your research trail stays honest.
3. **Read your evidence back.** `GET /candidates/{candidate_id}/observations`
   lists everything you collected, newest first.
4. **Track where each idea stands.** `PATCH /candidates/{candidate_id}` with
   `{"status": "collecting"}` (allowed: `new`, `collecting`, `analyzed`,
   `decided`), and `GET /candidates?status=collecting` to see what's in flight.

## Running the tests

The tests need a **dedicated test database** (`TEST_DATABASE_URL` in your
`.env` — it's in the template). This is a safety feature: the migration tests
wipe whatever database they run against, so they refuse to run unless the
database name contains `test`, and they never touch your real `DATABASE_URL`
data. When it finishes, the suite leaves the test database migrated to the
latest schema.

```bash
docker compose up -d db
uv run pytest
```

On a fresh setup, docker compose creates the `ecom_test` database
automatically. If your database volume predates this feature, create it once:

```bash
docker compose exec db createdb -U ecom ecom_test
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
  ingestion/       owns: sources, collection_runs, raw_observations
                   (append-only, enforced at the application layer via the
                   repository + ORM guards; direct SQL or database-owner
                   access can still bypass this — a DB trigger is deferred)
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
- **Tests complain about TEST_DATABASE_URL** — make sure `.env` exists and
  contains the `TEST_DATABASE_URL` line from `.env.example`, and that the
  test database exists (`docker compose exec db createdb -U ecom ecom_test`
  if needed). The error message itself walks you through the fix.
