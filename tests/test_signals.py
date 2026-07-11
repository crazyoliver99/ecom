"""Tests for the signals layer: facts, signals, events."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.catalog.models import Candidate
from app.catalog.repository import CandidateRepository
from app.ingestion.models import RawObservation, Source
from app.signals.detectors import keepa_new_bestseller_detected, keepa_rank_improved
from app.signals.models import Event, Fact, Signal
from app.signals.repository import (
    create_event,
    create_fact,
    create_signal,
    get_latest_fact_of_type,
)
from app.signals.service import SignalOrchestrator


@pytest.fixture
def candidate(db_session: Session) -> Candidate:
    """A test candidate."""
    repo = CandidateRepository(db_session)
    return repo.create(name="Test Product")


@pytest.fixture
def keepa_source(db_session: Session) -> Source:
    """The Keepa source (seeded by migration 0003)."""
    from sqlalchemy import select

    source = db_session.execute(
        select(Source).where(Source.key == "keepa")
    ).scalar_one_or_none()
    assert source is not None
    return source


class TestFactAppendOnly:
    """Facts are append-only: updates and deletes are rejected."""

    def test_fact_update_rejected(self, db_session: Session, candidate: Candidate):
        fact = create_fact(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 50000},
            datetime.now(UTC),
        )
        db_session.commit()

        fact.value = {"rank": 60000}
        with pytest.raises(Exception, match="append-only"):
            db_session.commit()

    def test_fact_delete_rejected(self, db_session: Session, candidate: Candidate):
        fact = create_fact(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 50000},
            datetime.now(UTC),
        )
        db_session.commit()

        db_session.delete(fact)
        with pytest.raises(Exception, match="append-only"):
            db_session.commit()


class TestFactVersion:
    """Latest fact of a type is the current truth."""

    def test_get_latest_fact_of_type(self, db_session: Session, candidate: Candidate):
        now = datetime.now(UTC)
        old_fact = create_fact(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 50000},
            now,
        )
        db_session.commit()

        new_fact = create_fact(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 40000},
            now,
        )
        db_session.commit()

        latest = get_latest_fact_of_type(db_session, candidate.id, "sales_rank")
        assert latest.id == new_fact.id
        assert latest.value["rank"] == 40000

    def test_get_latest_fact_nonexistent(self, db_session: Session, candidate: Candidate):
        latest = get_latest_fact_of_type(db_session, candidate.id, "nonexistent_type")
        assert latest is None


class TestSignalAppendOnly:
    """Signals are append-only: updates and deletes are rejected."""

    def test_signal_update_rejected(self, db_session: Session, candidate: Candidate):
        signal = create_signal(
            db_session,
            candidate.id,
            "new_bestseller_detected",
            "1.0",
            1.0,
            datetime.now(UTC),
        )
        db_session.commit()

        signal.confidence = 0.8
        with pytest.raises(Exception, match="append-only"):
            db_session.commit()

    def test_signal_delete_rejected(self, db_session: Session, candidate: Candidate):
        signal = create_signal(
            db_session,
            candidate.id,
            "new_bestseller_detected",
            "1.0",
            1.0,
            datetime.now(UTC),
        )
        db_session.commit()

        db_session.delete(signal)
        with pytest.raises(Exception, match="append-only"):
            db_session.commit()


class TestEventAppendOnly:
    """Events are append-only: updates and deletes are rejected."""

    def test_event_update_rejected(self, db_session: Session):
        event = create_event(
            db_session,
            "EvidenceCollected",
            datetime.now(UTC),
            payload={"test": "data"},
        )
        db_session.commit()

        event.payload = {"updated": "data"}
        with pytest.raises(Exception, match="append-only"):
            db_session.commit()

    def test_event_delete_rejected(self, db_session: Session):
        event = create_event(
            db_session,
            "EvidenceCollected",
            datetime.now(UTC),
        )
        db_session.commit()

        db_session.delete(event)
        with pytest.raises(Exception, match="append-only"):
            db_session.commit()


class TestKeepaNewBestsellerDetected:
    """Signal: new bestseller detected (rank < 100k, no prior fact)."""

    def test_fires_on_first_bestseller_rank(self, db_session: Session, candidate: Candidate):
        now = datetime.now(UTC)
        signals = keepa_new_bestseller_detected(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 50000},
            now=now,
        )
        assert len(signals) == 1
        assert signals[0].signal_type == "new_bestseller_detected"
        assert signals[0].confidence == 1.0

    def test_fires_only_on_first_fact(self, db_session: Session, candidate: Candidate):
        now = datetime.now(UTC)

        create_fact(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 50000},
            now,
        )
        db_session.commit()

        signals = keepa_new_bestseller_detected(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 40000},
            now=now,
        )
        assert len(signals) == 0

    def test_does_not_fire_on_non_bestseller_rank(self, db_session: Session, candidate: Candidate):
        now = datetime.now(UTC)
        signals = keepa_new_bestseller_detected(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 150000},
            now=now,
        )
        assert len(signals) == 0

    def test_ignores_other_fact_types(self, db_session: Session, candidate: Candidate):
        now = datetime.now(UTC)
        signals = keepa_new_bestseller_detected(
            db_session,
            candidate.id,
            "review_count",
            {"count": 100},
            now=now,
        )
        assert len(signals) == 0


class TestKeepaRankImproved:
    """Signal: rank improved (new_rank < old_rank)."""

    def test_fires_on_rank_improvement(self, db_session: Session, candidate: Candidate):
        now = datetime.now(UTC)

        create_fact(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 50000},
            now,
        )
        db_session.commit()

        signals = keepa_rank_improved(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 40000},
            now=now,
        )
        assert len(signals) == 1
        assert signals[0].signal_type == "rank_improved"

    def test_does_not_fire_on_rank_decline(self, db_session: Session, candidate: Candidate):
        now = datetime.now(UTC)

        create_fact(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 50000},
            now,
        )
        db_session.commit()

        signals = keepa_rank_improved(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 60000},
            now=now,
        )
        assert len(signals) == 0

    def test_does_not_fire_on_unchanged_rank(self, db_session: Session, candidate: Candidate):
        now = datetime.now(UTC)

        create_fact(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 50000},
            now,
        )
        db_session.commit()

        signals = keepa_rank_improved(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 50000},
            now=now,
        )
        assert len(signals) == 0

    def test_requires_prior_fact(self, db_session: Session, candidate: Candidate):
        now = datetime.now(UTC)
        signals = keepa_rank_improved(
            db_session,
            candidate.id,
            "sales_rank",
            {"rank": 40000},
            now=now,
        )
        assert len(signals) == 0
