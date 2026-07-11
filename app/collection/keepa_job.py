"""Keepa collection job: one scheduled pass over a fixed US bestseller category.

This is the seam where a provider adapter (returns DTOs only) meets persistence
(observations, facts, signals, events). It is deliberately the only place that
knows both Keepa's payload shape and the database.

Flow for one run:
1. Create a collection_run (candidate_id NULL — a run discovers many candidates).
2. Call Keepa: bestsellers -> product details. Provider I/O happens BEFORE any
   data is written, so a provider failure leaves no candidates/facts/signals; the
   run is marked failed and a ProviderFailed event is persisted.
3. On success (including zero results): store the full raw bestsellers response,
   then per product: dedup the candidate by ASIN (NewProductDiscovered on first
   sight), store a per-candidate observation (EvidenceCollected), and run the
   signal orchestrator (facts, EvidenceChanged, signals, SignalDetected).
4. Finalize the run succeeded.

Extending to a second provider means writing an analogous job plus its fact
extractor; the orchestrator, detectors, events, and dedup mechanism are reused
unchanged.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.repository import CandidateRepository
from app.core.errors import ConfigurationError
from app.ingestion.models import CollectionRun, RawObservation, Source
from app.ingestion.repository import RawObservationRepository
from app.providers.keepa import KeepaClient, KeepaError, extract_sales_rank
from app.signals.detectors import keepa_new_bestseller_detected, keepa_rank_improved
from app.signals.repository import create_event
from app.signals.service import SignalOrchestrator

KEEPA_SOURCE_KEY = "keepa"
# One fixed narrow US category for the reference milestone. Overridable via CLI.
# Node 3760901 is a real amazon.com (domain 1) "Home & Kitchen > Home Office
# Furniture" node; the exact node is not load-bearing — it is passed straight to
# Keepa and can be changed without touching any code below.
DEFAULT_US_CATEGORY_ID = 3760901
DEFAULT_MAX_PRODUCTS = 20

BESTSELLERS_OBSERVATION_TYPE = "keepa_bestsellers"
PRODUCT_OBSERVATION_TYPE = "keepa_product"
SALES_RANK_FACT_TYPE = "sales_rank"


@dataclass
class KeepaCollectionResult:
    run_id: uuid.UUID
    status: str
    new_candidates: int = 0
    observations: int = 0
    facts: int = 0
    signals: int = 0
    error: str | None = None
    signal_types: list[str] = field(default_factory=list)
    # Non-fatal issues on an otherwise successful run (e.g. an ASIN the
    # bestseller list named but the product endpoint did not return).
    provider_warnings: list[str] = field(default_factory=list)


def keepa_sales_rank_extractor(
    observation: RawObservation,
) -> list[tuple[str, dict, datetime]]:
    """Extract a sales_rank fact from a keepa_product observation. No rank -> no
    fact (a missing rank is never coerced to 0)."""
    payload = observation.payload
    rank = payload.get("rank")
    if rank is None:
        return []
    value = {
        "asin": payload.get("asin"),
        "rank": rank,
        "bestseller_position": payload.get("bestseller_position"),
        "bestseller_list_size": payload.get("bestseller_list_size"),
        "category_id": payload.get("category_id"),
    }
    return [(SALES_RANK_FACT_TYPE, value, observation.fetched_at)]


FACT_EXTRACTORS = {PRODUCT_OBSERVATION_TYPE: keepa_sales_rank_extractor}
SIGNAL_DETECTORS = {
    SALES_RANK_FACT_TYPE: [keepa_new_bestseller_detected, keepa_rank_improved]
}


def _get_keepa_source(session: Session) -> Source:
    source = session.scalar(select(Source).where(Source.key == KEEPA_SOURCE_KEY))
    if source is None:
        raise ConfigurationError(
            "The 'keepa' source is missing — run migrations (`alembic upgrade head`)."
        )
    return source


def run_keepa_collection(
    session: Session,
    client: KeepaClient,
    *,
    category_id: int = DEFAULT_US_CATEGORY_ID,
    max_products: int = DEFAULT_MAX_PRODUCTS,
    now: datetime | None = None,
) -> KeepaCollectionResult:
    """Execute one Keepa collection run and commit its results."""
    if now is None:
        now = datetime.now(UTC)

    source = _get_keepa_source(session)

    run = CollectionRun(
        source_id=source.id,
        candidate_id=None,
        status="running",
        started_at=now,
    )
    session.add(run)
    session.flush()

    # --- Provider I/O first: a failure here writes no evidence. ---
    try:
        bestsellers = client.get_bestsellers(category_id)
        asin_list = (bestsellers.get("bestSellersList") or {}).get("asinList") or []
        selected = [a for a in asin_list[:max_products] if a]
        products_by_asin: dict[str, dict] = {}
        if selected:
            products_response = client.get_products(selected)
            for product in products_response.get("products") or []:
                asin = product.get("asin")
                if asin:
                    products_by_asin[asin] = product
    except KeepaError as exc:
        finished = datetime.now(UTC)
        run.status = "failed"
        run.error = f"{type(exc).__name__}: {exc}"
        run.finished_at = finished
        create_event(
            session,
            event_type="ProviderFailed",
            occurred_at=finished,
            run_id=run.id,
            payload={
                "provider": KEEPA_SOURCE_KEY,
                "error_type": type(exc).__name__,
                "message": str(exc),
            },
        )
        session.commit()
        return KeepaCollectionResult(
            run_id=run.id, status="failed", error=run.error
        )

    # --- Success path (zero results is a valid success). ---
    obs_repo = RawObservationRepository(session)
    cand_repo = CandidateRepository(session)
    orchestrator = SignalOrchestrator(session)

    list_size = len(selected)
    result = KeepaCollectionResult(run_id=run.id, status="succeeded")

    # Store the full raw bestsellers response for auditability (run-scoped).
    obs_repo.create(
        source_id=source.id,
        observation_type=BESTSELLERS_OBSERVATION_TYPE,
        payload=bestsellers,
        fetched_at=now,
        run_id=run.id,
        source_url=f"https://api.keepa.com/bestsellers?domain=1&category={category_id}",
    )

    for position, asin in enumerate(selected, start=1):
        product = products_by_asin.get(asin)
        if product is None:
            # Requested but not returned by Keepa — a warning, not a failure.
            result.provider_warnings.append(
                f"ASIN {asin} was in the bestseller list but not returned by the product endpoint"
            )
            continue
        rank = extract_sales_rank(product)
        title = product.get("title") or asin

        candidate, created = cand_repo.get_or_create_by_external_id(
            source_id=source.id,
            external_id=asin,
            name=title,
            niche=None,
        )
        if created:
            result.new_candidates += 1
            create_event(
                session,
                event_type="NewProductDiscovered",
                occurred_at=now,
                candidate_id=candidate.id,
                run_id=run.id,
                payload={
                    "asin": asin,
                    "discovery_source": KEEPA_SOURCE_KEY,
                    "bestseller_position": position,
                },
            )

        observation = obs_repo.create(
            source_id=source.id,
            observation_type=PRODUCT_OBSERVATION_TYPE,
            payload={
                "asin": asin,
                "title": title,
                "rank": rank,
                "bestseller_position": position,
                "bestseller_list_size": list_size,
                "category_id": category_id,
                "raw_product": product,
            },
            fetched_at=now,
            run_id=run.id,
            candidate_id=candidate.id,
            source_url=f"https://api.keepa.com/product?domain=1&asin={asin}",
        )
        result.observations += 1
        create_event(
            session,
            event_type="EvidenceCollected",
            occurred_at=now,
            candidate_id=candidate.id,
            run_id=run.id,
            payload={
                "observation_id": str(observation.id),
                "observation_type": PRODUCT_OBSERVATION_TYPE,
                "source": KEEPA_SOURCE_KEY,
                "compliance": source.compliance,
            },
        )

        facts, signals, _events = orchestrator.process_observation(
            observation, FACT_EXTRACTORS, SIGNAL_DETECTORS, now=now, run_id=run.id
        )
        result.facts += len(facts)
        result.signals += len(signals)
        result.signal_types.extend(s.signal_type for s in signals)

    run.status = "succeeded"
    run.finished_at = datetime.now(UTC)
    session.commit()
    return result
