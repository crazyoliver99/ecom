"""One autonomous collection cycle: collect, then summarize (Atlas Autonomy M1).

This ties the Keepa collection job to the deterministic summary. It is what the
scheduler invokes each interval and what `atlas morning-report` relies on having
run. A successful run produces exactly one persisted summary; a failed run
produces none (per the milestone: summaries describe successful cycles).
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.collection.keepa_job import (
    DEFAULT_MAX_PRODUCTS,
    DEFAULT_US_CATEGORY_ID,
    KeepaCollectionResult,
    run_keepa_collection,
)
from app.collection.models import CollectionSummary
from app.collection.summary import generate_collection_summary
from app.ingestion.models import CollectionRun
from app.providers.keepa import KeepaClient


@dataclass
class CycleOutcome:
    result: KeepaCollectionResult
    summary: CollectionSummary | None


def run_keepa_collection_cycle(
    session: Session,
    client: KeepaClient,
    *,
    category_id: int = DEFAULT_US_CATEGORY_ID,
    max_products: int = DEFAULT_MAX_PRODUCTS,
    now: datetime | None = None,
) -> CycleOutcome:
    """Run one collection, and on success generate and persist its summary."""
    if now is None:
        now = datetime.now(UTC)

    result = run_keepa_collection(
        session, client, category_id=category_id, max_products=max_products, now=now
    )

    summary = None
    if result.status == "succeeded":
        run = session.get(CollectionRun, result.run_id)
        summary = generate_collection_summary(session, run, result, now=now)
        session.commit()

    return CycleOutcome(result=result, summary=summary)
