"""Tests for the signals layer: facts, signals, events, detectors."""

from datetime import UTC, datetime, timedelta

import pytest
from app.catalog.models import Candidate
from app.catalog.repository import CandidateRepository
from app.ingestion.models import RawObservation, Source
from app.signals.detectors import (
    keepa_new_bestseller_detected,
    keepa_rank_improved,
    new_bestseller_confidence,
    rank_improved_confidence,
)
from app.signals.repository import (
    create_event,
    create_fact,
    create_signal,
    get_latest_fact_of_type,
)
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def candidate(db_session: Session) -> Candidate:
    repo = CandidateRepository(db_session)
    cand = repo.create(name="Test Product")
    db_session.flush()
    return cand


@pytest.fixture
def keepa_source(db_session: Session) -> Source:
    source = db_session.scalar(select(Source).where(Source.key == "keepa"))
    assert source is not None, "keepa source should be seeded by migration 0003"
    return source


@pytest.fixture
def observation(db_session: Session, keepa_source: Source, candidate: Candidate) -> RawObservation:
    """A stored observation facts can cite (source_observation_id is NOT NULL)."""
    obs = RawObservation(
        source_id=keepa_source.id,
        candidate_id=candidate.id,
        observation_type="keepa_product",
        payload={"asin": "B000TEST01"},
        fetched_at=datetime.now(UTC),
    )
    db_session.add(obs)
    db_session.flush()
    return obs


def _make_fact(db_session, candidate, observation, rank, position=1, list_size=10, when=None):
    return create_fact(
        db_session,
        candidate_id=candidate.id,
        fact_type="sales_rank",
        value={
            "asin": "B000TEST01",
            "rank": rank,
            "bestseller_position": position,
            "bestseller_list_size": list_size,
        },
        observed_at=when or datetime.now(UTC),
        source_observation_id=observation.id,
    )


class TestFactTraceability:
    def test_fact_requires_source_observation(self, db_session, candidate):
        with pytest.raises(ValueError, match="source_observation_id is required"):
            create_fact(
                db_session,
                candidate_id=candidate.id,
                fact_type="sales_rank",
                value={"rank": 1},
                observed_at=datetime.now(UTC),
                source_observation_id=None,
            )

    def test_fact_cites_exactly_one_observation(self, db_session, candidate, observation):
        fact = _make_fact(db_session, candidate, observation, rank=100)
        db_session.flush()
        assert fact.source_observation_id == observation.id


class TestFactAppendOnly:
    def test_fact_update_rejected(self, db_session, candidate, observation):
        fact = _make_fact(db_session, candidate, observation, rank=50000)
        db_session.flush()
        fact.value = {"rank": 60000}
        with pytest.raises(Exception, match="append-only"):
            db_session.flush()

    def test_fact_delete_rejected(self, db_session, candidate, observation):
        fact = _make_fact(db_session, candidate, observation, rank=50000)
        db_session.flush()
        db_session.delete(fact)
        with pytest.raises(Exception, match="append-only"):
            db_session.flush()


class TestPriorFactSemantics:
    def test_latest_before_insert_is_not_the_new_fact(
        self, db_session, candidate, observation
    ):
        """The prior fact must be fetched before inserting the new fact, so it can
        never be the new fact itself."""
        t0 = datetime.now(UTC)
        first = _make_fact(db_session, candidate, observation, rank=50000, when=t0)
        db_session.flush()

        # Prior fetched BEFORE inserting the second fact.
        prior = get_latest_fact_of_type(db_session, candidate.id, "sales_rank")
        assert prior is not None
        assert prior.id == first.id

        second = _make_fact(
            db_session, candidate, observation, rank=40000, when=t0 + timedelta(hours=1)
        )
        db_session.flush()

        # The prior we captured is emphatically not the newly-inserted fact.
        assert prior.id != second.id

        # And now the "latest" has moved on to the second fact.
        latest_now = get_latest_fact_of_type(db_session, candidate.id, "sales_rank")
        assert latest_now.id == second.id

    def test_latest_none_when_no_facts(self, db_session, candidate):
        assert get_latest_fact_of_type(db_session, candidate.id, "sales_rank") is None


class TestSignalValidation:
    def test_confidence_out_of_range_rejected(self, db_session, candidate, observation):
        fact = _make_fact(db_session, candidate, observation, rank=100)
        db_session.flush()
        with pytest.raises(ValueError, match="confidence must be within"):
            create_signal(
                db_session,
                candidate_id=candidate.id,
                signal_type="rank_improved",
                detector_version="1.0",
                confidence=1.5,
                computed_at=datetime.now(UTC),
                fact_ids=[fact.id],
            )

    def test_empty_fact_ids_rejected_by_repository(self, db_session, candidate):
        with pytest.raises(ValueError, match="at least one fact"):
            create_signal(
                db_session,
                candidate_id=candidate.id,
                signal_type="rank_improved",
                detector_version="1.0",
                confidence=0.5,
                computed_at=datetime.now(UTC),
                fact_ids=[],
            )

    def test_empty_fact_ids_rejected_by_database(self, db_session, candidate):
        """Even bypassing the repository, the DB check constraint forbids an empty
        fact_ids array."""
        from app.signals.models import Signal

        signal = Signal(
            candidate_id=candidate.id,
            signal_type="rank_improved",
            detector_version="1.0",
            confidence=0.5,
            fact_ids=[],
            computed_at=datetime.now(UTC),
        )
        db_session.add(signal)
        with pytest.raises(Exception, match="ck_signals_fact_ids_nonempty"):
            db_session.flush()
        db_session.rollback()

    def test_confidence_out_of_range_rejected_by_database(self, db_session, candidate, observation):
        from app.signals.models import Signal

        fact = _make_fact(db_session, candidate, observation, rank=1)
        db_session.flush()
        signal = Signal(
            candidate_id=candidate.id,
            signal_type="rank_improved",
            detector_version="1.0",
            confidence=2,
            fact_ids=[str(fact.id)],
            computed_at=datetime.now(UTC),
        )
        db_session.add(signal)
        with pytest.raises(Exception, match="ck_signals_confidence_range"):
            db_session.flush()
        db_session.rollback()


class TestSignalAppendOnly:
    def _signal(self, db_session, candidate, observation):
        fact = _make_fact(db_session, candidate, observation, rank=1)
        db_session.flush()
        sig = create_signal(
            db_session,
            candidate_id=candidate.id,
            signal_type="new_bestseller_detected",
            detector_version="1.0",
            confidence=1.0,
            computed_at=datetime.now(UTC),
            fact_ids=[fact.id],
        )
        db_session.flush()
        return sig

    def test_signal_update_rejected(self, db_session, candidate, observation):
        sig = self._signal(db_session, candidate, observation)
        sig.confidence = 0.8
        with pytest.raises(Exception, match="append-only"):
            db_session.flush()

    def test_signal_delete_rejected(self, db_session, candidate, observation):
        sig = self._signal(db_session, candidate, observation)
        db_session.delete(sig)
        with pytest.raises(Exception, match="append-only"):
            db_session.flush()


class TestEventAppendOnly:
    def test_event_update_rejected(self, db_session):
        ev = create_event(db_session, "EvidenceCollected", datetime.now(UTC), payload={"a": 1})
        db_session.flush()
        ev.payload = {"a": 2}
        with pytest.raises(Exception, match="append-only"):
            db_session.flush()

    def test_event_delete_rejected(self, db_session):
        ev = create_event(db_session, "EvidenceCollected", datetime.now(UTC))
        db_session.flush()
        db_session.delete(ev)
        with pytest.raises(Exception, match="append-only"):
            db_session.flush()


class TestConfidenceFormulas:
    def test_new_bestseller_confidence_scales_with_position(self):
        # Position 1 of 100 is strongest; deeper positions score lower.
        top = new_bestseller_confidence(1, 100)
        mid = new_bestseller_confidence(50, 100)
        bottom = new_bestseller_confidence(100, 100)
        assert top == pytest.approx(1.0)
        assert mid == pytest.approx(1 - 49 / 100)
        assert bottom == pytest.approx(1 - 99 / 100)
        assert top > mid > bottom > 0
        # Non-constant across inputs.
        assert len({top, mid, bottom}) == 3

    def test_rank_improved_confidence_scales_with_magnitude(self):
        small = rank_improved_confidence(50000, 49000)  # 2%
        big = rank_improved_confidence(50000, 500)  # ~99%
        assert small == pytest.approx((50000 - 49000) / 50000)
        assert big == pytest.approx((50000 - 500) / 50000)
        assert 0 < small < big <= 1
        assert small != big

    def test_confidence_within_unit_interval(self):
        assert 0 <= new_bestseller_confidence(100, 100) <= 1
        assert 0 <= rank_improved_confidence(2, 1) <= 1


class TestNewBestsellerDetector:
    def test_fires_on_initial_discovery(self, db_session, candidate, observation):
        new_fact = _make_fact(
            db_session, candidate, observation, rank=1234, position=3, list_size=20
        )
        db_session.flush()
        signals = keepa_new_bestseller_detected(db_session, new_fact, None)
        assert len(signals) == 1
        sig = signals[0]
        assert sig.signal_type == "new_bestseller_detected"
        # Cites the NEW fact id.
        assert sig.fact_ids == [str(new_fact.id)]
        # Confidence from the position formula, not a constant.
        assert float(sig.confidence) == pytest.approx(new_bestseller_confidence(3, 20))
        assert float(sig.confidence) != 1.0

    def test_does_not_fire_when_prior_exists(self, db_session, candidate, observation):
        prior = _make_fact(db_session, candidate, observation, rank=5000)
        db_session.flush()
        new_fact = _make_fact(db_session, candidate, observation, rank=4000)
        db_session.flush()
        assert keepa_new_bestseller_detected(db_session, new_fact, prior) == []


class TestRankImprovedDetector:
    def test_fires_on_improvement_citing_both_facts(self, db_session, candidate, observation):
        prior = _make_fact(db_session, candidate, observation, rank=50000)
        db_session.flush()
        new_fact = _make_fact(db_session, candidate, observation, rank=40000)
        db_session.flush()

        signals = keepa_rank_improved(db_session, new_fact, prior)
        assert len(signals) == 1
        sig = signals[0]
        assert sig.signal_type == "rank_improved"
        # Cites BOTH prior and new fact ids, in that order.
        assert sig.fact_ids == [str(prior.id), str(new_fact.id)]
        assert float(sig.confidence) == pytest.approx(rank_improved_confidence(50000, 40000))

    def test_does_not_fire_on_worse_rank(self, db_session, candidate, observation):
        prior = _make_fact(db_session, candidate, observation, rank=50000)
        db_session.flush()
        new_fact = _make_fact(db_session, candidate, observation, rank=60000)
        db_session.flush()
        assert keepa_rank_improved(db_session, new_fact, prior) == []

    def test_does_not_fire_on_unchanged_rank(self, db_session, candidate, observation):
        prior = _make_fact(db_session, candidate, observation, rank=50000)
        db_session.flush()
        new_fact = _make_fact(db_session, candidate, observation, rank=50000)
        db_session.flush()
        assert keepa_rank_improved(db_session, new_fact, prior) == []

    def test_does_not_fire_without_prior(self, db_session, candidate, observation):
        new_fact = _make_fact(db_session, candidate, observation, rank=40000)
        db_session.flush()
        assert keepa_rank_improved(db_session, new_fact, None) == []
