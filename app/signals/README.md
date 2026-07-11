# Signals Layer

The signals layer (OPERATING_SYSTEM.md §4) bridges provider observations and reasoning:

**observations** → **facts** → **signals** → **opportunities**

## Architecture

### Facts (append-only)
Raw observations are turned into facts — the current truth values for observable properties at a point in time. Multiple facts of the same type supersede prior versions; the newest is the current truth.

Example: Keepa observation with sales_rank=50000 becomes a fact `{type: "sales_rank", value: {rank: 50000}}`.

### Signals (append-only, deterministic)
Signals are fired by detectors when facts change meaningfully. Each signal:
- Has a versioned detector (for auditability)
- Outputs a confidence score from a versioned formula (never agent judgment)
- References the facts it derived from
- Is provider-agnostic (e.g., `rank_improved` not `keepa_rank_improved`)

Example: When sales_rank < prior_rank, the `rank_improved` signal fires with confidence=1.0.

### Events (append-only)
An audit log of what happened: when collections succeeded/failed, when facts changed, when signals fired. Downstream logic (agents, dashboards, diagnostics) subscribes to events.

## Implementing a New Provider

The goal: make the second provider take 10% of the effort of the first (Keepa). Follow this pattern:

### 1. Provider Adapter (`app/providers/<name>.py`)
- Fetches data from the external API
- Returns observations (provider-specific DTO)
- No database writes (returns DTOs only)
- Example: `app/providers/keepa.py` fetches bestsellers from Keepa

### 2. Fact Extractors
In your provider adapter, define extractors that turn observations into facts:

```python
def keepa_bestseller_to_facts(payload: dict) -> list[tuple[str, dict, datetime]]:
    """Extract facts from a Keepa bestseller observation."""
    asin = payload["asin"]
    rank = payload["sales_rank"]
    return [
        ("sales_rank", {"rank": rank, "asin": asin}, datetime.fromisoformat(payload["observed_at"])),
    ]
```

Register in `fact_extractors` dict: `{"keepa_bestseller_product": keepa_bestseller_to_facts}`

### 3. Signal Detectors (`app/signals/detectors.py`)
Define detectors that examine facts and emit provider-agnostic signals:

```python
def rank_improved(session, candidate_id, fact_type, new_fact_value, now):
    """Detect rank improvement: sales_rank < prior_fact.sales_rank."""
    if fact_type != "sales_rank":
        return []
    new_rank = new_fact_value.get("rank")
    prior_fact = get_latest_fact_of_type(session, candidate_id, "sales_rank")
    if prior_fact and new_rank < prior_fact.value.get("rank"):
        return [create_signal(...)]
    return []
```

Register in `signal_detectors` dict: `{"sales_rank": [rank_improved, ...]}`

### 4. Collection Job
Wire together the adapter, extractors, and detectors in your collection job:

```python
from app.signals.service import SignalOrchestrator

orchestrator = SignalOrchestrator(session)
facts, signals, events = orchestrator.process_observation(
    observation,
    fact_extractors={
        "keepa_bestseller_product": keepa_bestseller_to_facts,
    },
    signal_detectors={
        "sales_rank": [
            keepa_new_bestseller_detected,
            keepa_rank_improved,
        ],
    },
)
session.commit()
```

## Key Design Points

1. **No provider-specific signal types.** Signals are provider-agnostic. Keepa's `rank_improved` signal has the same type as an AliExpress ranking signal. The detector version disambiguates the source logic.

2. **Append-only everywhere.** Facts, Signals, Events cannot be updated or deleted. New versions are added, never replace old ones. This preserves auditability and makes rollback tractable.

3. **Deterministic signals.** Signals are computed from facts via versioned formulas, never agent judgment. Confidence is a number, not "maybe". This makes signals reproducible and auditable.

4. **Provider isolation.** The provider adapter is a black box. New providers don't modify Keepa's code, they just add their own adapter alongside it.

5. **Event subscribers.** Downstream logic (Opportunity agents, dashboards, alert systems) subscribes to events, not to facts/signals directly. This decouples collection from reasoning.

## Testing

Run signal tests:
```bash
pytest tests/test_signals.py -v
```

Run migration tests (including 0003):
```bash
pytest tests/test_migrations.py::test_migration_0003_round_trip -v
```

Test append-only enforcement:
```bash
# Facts, Signals, Events all reject updates and deletes
pytest tests/test_signals.py::TestFactAppendOnly -v
```

Test detector logic:
```bash
pytest tests/test_signals.py::TestKeepaRankImproved -v
```
