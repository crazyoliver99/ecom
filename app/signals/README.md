# Signals Layer

The signals layer (OPERATING_SYSTEM.md §4) sits between provider observations and reasoning:

**observations → facts → signals → (later) opportunities**

Everything here is deterministic and append-only. Nothing in this layer uses an LLM or a judgment call.

## The three tables

### Facts (append-only)
A fact is the current truth value of one observable property at a point in time. A new fact of the same type for the same candidate *supersedes* the prior one — the newest non-stale fact is the current truth. Older facts are never updated or deleted.

- `source_observation_id` is **NOT NULL**: every fact cites exactly one stored raw observation. A fact with no observation behind it is not traceable evidence and cannot exist.
- Example: a Keepa product observation becomes a `sales_rank` fact whose value is `{asin, rank, bestseller_position, bestseller_list_size, category_id}`.

### Signals (append-only, deterministic)
A signal is a versioned, mechanical detection that something meaningful changed. Each signal:
- carries a `detector_version` (so a stored signal can be reproduced or rolled back);
- carries a `confidence` in **[0, 1]** produced by a **versioned formula**, never a constant and never a judgment (enforced by a DB check constraint and by the repository);
- cites the facts it was computed from in `fact_ids`, which must be a **non-empty** array (enforced by a DB check constraint and by the repository);
- is **provider-agnostic**: the type is `rank_improved`, not `keepa_rank_improved`. A second marketplace's detector emits the identical signal type.

### Events (append-only)
The audit trail of what happened, and the trigger surface for downstream logic. Types emitted by this milestone:
`NewProductDiscovered`, `EvidenceCollected`, `EvidenceChanged`, `SignalDetected`, `ProviderFailed`.

## Detectors and the prior fact

A detector receives the **newly created fact** and the **immediately prior fact** explicitly:

```python
def keepa_rank_improved(session, new_fact, prior_fact, *, now=None) -> list[Signal]:
    ...
```

The orchestrator fetches the prior fact (`get_latest_fact_of_type`) **before** inserting the new one, so a detector can never mistake the new fact for its own "prior". Detectors never query for the latest fact themselves.

### Confidence formulas (versioned)

**`new_bestseller_detected` — detector v1.0.** Fires on initial discovery (no prior sales_rank fact). Cites the new fact.

```
confidence = 1 - (bestseller_position - 1) / bestseller_list_size     # clamped to [0, 1]
```

Position 1 of an N-item list scores 1.0; a debut near the bottom scores ~1/N. Confidence scales with how strong the bestseller-list position is.

**`rank_improved` — detector v1.0.** Fires when the Amazon sales rank improves (new rank numerically smaller than prior). Does not fire on unchanged or worse rank, or without a prior fact. Cites **both** the prior and the new fact.

```
confidence = (prior_rank - new_rank) / prior_rank                     # clamped to [0, 1]
```

A move of 50000→40000 scores 0.20; 50000→500 scores ~0.99. Confidence scales with the fractional magnitude of the improvement.

## Adding a second provider (the 10% goal)

The reference provider is Keepa (`app/providers/keepa.py` + `app/collection/keepa_job.py`). A second provider reuses the orchestrator, the events, the append-only tables, and the ASIN-style dedup mechanism unchanged. You write only:

1. **A provider adapter** in `app/providers/<name>.py` — returns raw payloads, never writes the DB (see `providers/README.md`).
2. **A fact extractor** — `function(observation) -> [(fact_type, value, observed_at)]`.
3. **A collection job** in `app/collection/<name>_job.py` — mirror `keepa_job.py`: create the run, call the adapter (provider I/O before any write), dedup candidates by external id (`CandidateRepository.get_or_create_by_external_id`), store observations, and hand each to `SignalOrchestrator.process_observation`.
4. **(Optional) new detectors** in `app/signals/detectors.py` if the provider surfaces a new pattern — but reuse existing provider-agnostic signal types wherever the meaning matches.

You do **not** modify the Keepa adapter, the orchestrator, the models, or the migration.

## Running the Keepa collection

```bash
# Requires KEEPA_API_KEY in the environment (never hard-coded).
python -m app.cli collect-keepa --category 3760901 --max-products 20
```

See the repository README for cron setup and the SQL inspection queries in `docs/SQL_QUERIES.md`.

## Testing

```bash
uv run pytest tests/test_signals.py          # facts, signals, events, detectors, formulas
uv run pytest tests/test_keepa_client.py     # HTTP client: parsing, error classes, retries (offline)
uv run pytest tests/test_keepa_collection.py # end-to-end pipeline over fixture-driven runs
uv run pytest tests/test_migrations.py       # migration round-trip incl. constraints
```
