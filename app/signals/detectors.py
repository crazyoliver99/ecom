"""Signal detectors: deterministic algorithms that emit signals from facts.

A detector is a versioned, mechanical rule (OPERATING_SYSTEM.md §4). It receives
the newly created Fact and the immediately prior Fact of the same type (fetched
BEFORE the new one was inserted, so it can never be the new fact itself), and
returns zero or more Signals. Detectors never query for the "latest" fact
themselves — the orchestrator passes prior explicitly.

Confidence is a versioned, deterministic formula output, never a constant and
never a judgment. Each detector documents its exact formula and carries a
version string so a stored signal can be reproduced or rolled back.

Signal types are provider-agnostic. These detectors are Keepa's, but the
`new_bestseller_detected` / `rank_improved` signals they emit look identical to
any other marketplace provider's equivalent detections.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.signals.models import Fact, Signal
from app.signals.repository import create_signal

# Detector versions. Bump when a formula changes; stored signals keep the version
# that produced them so old values remain reproducible (OPERATING_SYSTEM.md §6).
NEW_BESTSELLER_DETECTOR_VERSION = "1.0"
RANK_IMPROVED_DETECTOR_VERSION = "1.0"

SALES_RANK_FACT_TYPE = "sales_rank"


def _clamp_unit(x: float) -> float:
    """Clamp to [0, 1] — the valid confidence range."""
    return max(0.0, min(1.0, x))


def new_bestseller_confidence(position: int, list_size: int) -> float:
    """Confidence for new_bestseller_detected, formula v1.0.

        confidence = 1 - (position - 1) / list_size

    `position` is the product's 1-indexed slot in the bestseller list we fetched
    and `list_size` is the number of entries in that list. A debut at position 1
    yields 1.0; a debut near the bottom of an N-item list yields ~1/N. Confidence
    therefore scales with how strong the bestseller-list position is. Result is
    clamped to [0, 1].
    """
    if list_size <= 0:
        raise ValueError("list_size must be positive")
    return _clamp_unit(1.0 - (position - 1) / list_size)


def rank_improved_confidence(prior_rank: int, new_rank: int) -> float:
    """Confidence for rank_improved, formula v1.0.

        confidence = (prior_rank - new_rank) / prior_rank

    This is the fractional (percentage) magnitude of the improvement in Amazon
    sales rank: a rank moving 50000 -> 40000 scores 0.20, while 50000 -> 500
    scores ~0.99. Confidence scales with how large the improvement is relative to
    where it started. Result is clamped to [0, 1].
    """
    if prior_rank <= 0:
        raise ValueError("prior_rank must be positive")
    return _clamp_unit((prior_rank - new_rank) / prior_rank)


def keepa_new_bestseller_detected(
    session: Session,
    new_fact: Fact,
    prior_fact: Fact | None,
    *,
    now: datetime | None = None,
) -> list[Signal]:
    """Emit `new_bestseller_detected` when a product first appears with a
    sales-rank fact (prior_fact is None). Cites the new fact.

    Detector version: 1.0. Confidence: new_bestseller_confidence().
    """
    if now is None:
        now = datetime.now(UTC)
    if new_fact.fact_type != SALES_RANK_FACT_TYPE:
        return []
    if prior_fact is not None:
        return []

    position = new_fact.value.get("bestseller_position")
    list_size = new_fact.value.get("bestseller_list_size")
    if position is None or list_size is None:
        return []

    confidence = new_bestseller_confidence(int(position), int(list_size))
    signal = create_signal(
        session,
        candidate_id=new_fact.candidate_id,
        signal_type="new_bestseller_detected",
        detector_version=NEW_BESTSELLER_DETECTOR_VERSION,
        confidence=confidence,
        computed_at=now,
        fact_ids=[new_fact.id],
    )
    return [signal]


def keepa_rank_improved(
    session: Session,
    new_fact: Fact,
    prior_fact: Fact | None,
    *,
    now: datetime | None = None,
) -> list[Signal]:
    """Emit `rank_improved` when the Amazon sales rank improves (new rank is
    numerically smaller than the prior rank). Cites both the prior and new facts.
    Does not fire on unchanged or worsened rank, or without a prior fact.

    Detector version: 1.0. Confidence: rank_improved_confidence().
    """
    if now is None:
        now = datetime.now(UTC)
    if new_fact.fact_type != SALES_RANK_FACT_TYPE:
        return []
    if prior_fact is None:
        return []

    new_rank = new_fact.value.get("rank")
    prior_rank = prior_fact.value.get("rank")
    if new_rank is None or prior_rank is None:
        return []
    if new_rank >= prior_rank:
        return []

    confidence = rank_improved_confidence(int(prior_rank), int(new_rank))
    signal = create_signal(
        session,
        candidate_id=new_fact.candidate_id,
        signal_type="rank_improved",
        detector_version=RANK_IMPROVED_DETECTOR_VERSION,
        confidence=confidence,
        computed_at=now,
        fact_ids=[prior_fact.id, new_fact.id],
    )
    return [signal]
