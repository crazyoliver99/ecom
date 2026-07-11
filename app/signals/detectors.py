"""Signal detectors: deterministic algorithms that emit signals from facts.

Each detector:
- Takes facts and prior signals as input
- Outputs zero or more signals with versioned logic
- Is provider-agnostic (emits standardized signal types)
- Records its version in signal.detector_version for auditability

Provider-specific detectors (e.g., Keepa's rank-improvement detector) live in
the provider adapter and call these to emit standardized signals.
"""

import uuid
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.signals.models import Signal
from app.signals.repository import create_signal, get_latest_fact_of_type


class SignalDetector(Protocol):
    """Protocol for a signal detector function.

    A detector examines facts for a candidate and decides whether to emit signals.
    Outputs are appended: detectors never modify prior signals, only add new ones.
    """

    def __call__(
        self,
        session: Session,
        candidate_id: uuid.UUID,
        fact_type: str,
        new_fact_value: dict,
        now: datetime = datetime.now(UTC),
    ) -> list[Signal]:
        """Detect signals from a new fact.

        Args:
            session: Database session for reading prior facts and emitting signals
            candidate_id: The candidate this fact belongs to
            fact_type: The type of fact that changed
            new_fact_value: The new fact's value (dict, structure varies by fact_type)
            now: Current time for signal.computed_at

        Returns:
            List of signals emitted (may be empty)
        """


# Keepa-specific detectors


def keepa_new_bestseller_detected(
    session: Session,
    candidate_id: uuid.UUID,
    fact_type: str,
    new_fact_value: dict,
    now: datetime = datetime.now(UTC),
) -> list[Signal]:
    """Detect new bestseller: sales_rank < 100k and no prior sales_rank fact.

    Fires once per candidate when Keepa first detects a product in the bestseller
    ranking. Does not fire on every rank update, only on initial entry.

    Detector version: 1.0 (formula: sales_rank < 100000 and no prior fact)
    """
    if fact_type != "sales_rank":
        return []

    sales_rank = new_fact_value.get("rank")
    if sales_rank is None or sales_rank >= 100000:
        return []

    prior_fact = get_latest_fact_of_type(session, candidate_id, "sales_rank")
    if prior_fact is not None:
        return []

    signal = create_signal(
        session=session,
        candidate_id=candidate_id,
        signal_type="new_bestseller_detected",
        detector_version="1.0",
        confidence=1.0,
        computed_at=now,
        fact_ids=[],
    )
    return [signal]


def keepa_rank_improved(
    session: Session,
    candidate_id: uuid.UUID,
    fact_type: str,
    new_fact_value: dict,
    now: datetime = datetime.now(UTC),
) -> list[Signal]:
    """Detect rank improvement: sales_rank < prior_fact.sales_rank.

    Fires whenever the rank improves (numerically decreases). Does not fire on
    unchanged or worsened rank.

    Detector version: 1.0 (formula: new_rank < old_rank)
    """
    if fact_type != "sales_rank":
        return []

    new_rank = new_fact_value.get("rank")
    if new_rank is None:
        return []

    prior_fact = get_latest_fact_of_type(session, candidate_id, "sales_rank")
    if prior_fact is None:
        return []

    prior_rank = prior_fact.value.get("rank")
    if prior_rank is None or new_rank >= prior_rank:
        return []

    signal = create_signal(
        session=session,
        candidate_id=candidate_id,
        signal_type="rank_improved",
        detector_version="1.0",
        confidence=1.0,
        computed_at=now,
        fact_ids=[],
    )
    return [signal]
