"""Signal orchestration: observation -> facts -> signals, with the fact-supersession
and signal events that the operating system requires (OPERATING_SYSTEM.md §2, §4).

The orchestrator is provider-agnostic. It is handed:
- `fact_extractors`: observation_type -> function(observation) -> [(fact_type, value, observed_at)]
- `signal_detectors`: fact_type -> [detector(session, new_fact, prior_fact, *, now)]

For each extracted fact it fetches the prior fact of that type BEFORE inserting
the new one (so a change detector never sees the new fact as its own "prior"),
inserts the new fact, emits EvidenceChanged when it supersedes a prior fact, runs
the detectors with (new_fact, prior_fact), and emits SignalDetected per signal.

NewProductDiscovered and EvidenceCollected are emitted by the collection job that
stores the observation, not here — this layer starts from an already-stored one.
"""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.ingestion.models import RawObservation
from app.signals.models import Event, Fact, Signal
from app.signals.repository import create_event, create_fact, get_latest_fact_of_type

FactExtractor = Callable[[RawObservation], list[tuple[str, dict, datetime]]]
SignalDetector = Callable[..., list[Signal]]


class SignalOrchestrator:
    def __init__(self, session: Session):
        self.session = session

    def process_observation(
        self,
        observation: RawObservation,
        fact_extractors: dict[str, FactExtractor],
        signal_detectors: dict[str, list[SignalDetector]],
        now: datetime | None = None,
        run_id: uuid.UUID | None = None,
    ) -> tuple[list[Fact], list[Signal], list[Event]]:
        """Turn one stored observation into facts, signals, and events. run_id, when
        given, is stamped on the EvidenceChanged/SignalDetected events so they are
        attributable to the collection run that produced them."""
        if now is None:
            now = datetime.now(UTC)

        candidate_id: uuid.UUID | None = observation.candidate_id
        if candidate_id is None:
            return [], [], []

        extractor = fact_extractors.get(observation.observation_type)
        if extractor is None:
            return [], [], []

        facts: list[Fact] = []
        signals: list[Signal] = []
        events: list[Event] = []

        for fact_type, fact_value, observed_at in extractor(observation):
            # Prior = current truth BEFORE this fact is inserted.
            prior_fact = get_latest_fact_of_type(self.session, candidate_id, fact_type)

            new_fact = create_fact(
                self.session,
                candidate_id=candidate_id,
                fact_type=fact_type,
                value=fact_value,
                observed_at=observed_at,
                source_observation_id=observation.id,
            )
            facts.append(new_fact)

            if prior_fact is not None:
                events.append(
                    create_event(
                        self.session,
                        event_type="EvidenceChanged",
                        occurred_at=now,
                        run_id=run_id,
                        candidate_id=candidate_id,
                        fact_id=new_fact.id,
                        payload={
                            "fact_type": fact_type,
                            "superseded_fact_id": str(prior_fact.id),
                            "new_fact_id": str(new_fact.id),
                        },
                    )
                )

            for detector in signal_detectors.get(fact_type, []):
                for signal in detector(self.session, new_fact, prior_fact, now=now):
                    signals.append(signal)
                    events.append(
                        create_event(
                            self.session,
                            event_type="SignalDetected",
                            occurred_at=now,
                            run_id=run_id,
                            candidate_id=candidate_id,
                            signal_id=signal.id,
                            payload={
                                "signal_type": signal.signal_type,
                                "detector_version": signal.detector_version,
                                "confidence": float(signal.confidence),
                            },
                        )
                    )

        return facts, signals, events
