"""Signal service: orchestrates fact detection, signal detection, and event emission."""

import uuid
from datetime import UTC, datetime
from typing import Callable

from sqlalchemy.orm import Session

from app.ingestion.models import RawObservation
from app.signals.models import Event, Fact, Signal
from app.signals.repository import create_event, create_fact, create_signal


SignalDetector = Callable[
    [Session, uuid.UUID, str, dict, datetime],
    list[Signal],
]


class SignalOrchestrator:
    """Orchestrates the observation → fact → signal → event pipeline.

    For a given raw observation:
    1. Extract facts (observation_type-specific extraction logic)
    2. Run signal detectors on each new fact
    3. Emit events for facts and signals
    """

    def __init__(self, session: Session):
        self.session = session

    def process_observation(
        self,
        observation: RawObservation,
        fact_extractors: dict[str, Callable[[dict], list[tuple[str, dict, datetime]]]],
        signal_detectors: dict[str, list[SignalDetector]],
        now: datetime = datetime.now(UTC),
    ) -> tuple[list[Fact], list[Signal], list[Event]]:
        """Process a raw observation into facts, signals, and events.

        Args:
            observation: The raw observation to process
            fact_extractors: Map of observation_type → extractor function.
                Each extractor takes payload dict and returns list of (fact_type, fact_value, observed_at)
            signal_detectors: Map of fact_type → list of detector functions.
                Each detector runs after a fact is created.
            now: Current time for timestamps

        Returns:
            Tuple of (facts_created, signals_fired, events_logged)
        """
        candidate_id = observation.candidate_id
        if candidate_id is None:
            return [], [], []

        facts = []
        signals = []
        events = []

        extractor = fact_extractors.get(observation.observation_type)
        if not extractor:
            return [], [], []

        extracted_facts = extractor(observation.payload)
        for fact_type, fact_value, observed_at in extracted_facts:
            fact = create_fact(
                self.session,
                candidate_id=candidate_id,
                fact_type=fact_type,
                value=fact_value,
                observed_at=observed_at,
                source_observation_id=observation.id,
            )
            facts.append(fact)

            event = create_event(
                self.session,
                event_type="EvidenceCollected",
                occurred_at=now,
                candidate_id=candidate_id,
                fact_id=fact.id,
                payload={"fact_type": fact_type, "source_observation_id": str(observation.id)},
            )
            events.append(event)

            detectors = signal_detectors.get(fact_type, [])
            for detector in detectors:
                new_signals = detector(
                    self.session,
                    candidate_id,
                    fact_type,
                    fact_value,
                    now=now,
                )
                signals.extend(new_signals)
                for signal in new_signals:
                    event = create_event(
                        self.session,
                        event_type="SignalDetected",
                        occurred_at=now,
                        candidate_id=candidate_id,
                        signal_id=signal.id,
                        payload={"signal_type": signal.signal_type},
                    )
                    events.append(event)

        return facts, signals, events
