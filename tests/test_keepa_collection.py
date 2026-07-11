"""End-to-end tests for the Keepa collection job, driven by a fake client.

The job commits, so each test runs inside an outer transaction with a restarting
SAVEPOINT: the job's commit() only commits the savepoint, and the outer rollback
undoes everything, keeping the shared test database clean.
"""

import pytest
from app.catalog.models import Candidate, CandidateExternalId
from app.collection.keepa_job import run_keepa_collection
from app.ingestion.models import CollectionRun, RawObservation
from app.providers.keepa import KeepaRateLimitError, KeepaTransientError
from app.signals.models import Event, Fact, Signal
from sqlalchemy import event, func, select, text
from sqlalchemy.orm import Session

# Data tables cleared for a clean slate, in FK-safe order. `sources` is kept
# (the Keepa/manual rows are seed data the job depends on).
_CLEANUP_TABLES = [
    "events",
    "signals",
    "facts",
    "candidate_external_ids",
    "raw_observations",
    "collection_runs",
    "candidates",
]


@pytest.fixture()
def tx_session(engine):
    """A session whose commits are contained in an outer transaction that is
    rolled back at teardown. Because sibling suites (e.g. the candidates API)
    commit real rows into the shared test database, the fixture first clears the
    data tables inside this same rolled-back transaction — every collection test
    gets a clean slate, and no committed data is permanently destroyed."""
    connection = engine.connect()
    outer = connection.begin()
    for table in _CLEANUP_TABLES:
        connection.execute(text(f"DELETE FROM {table}"))

    session = Session(bind=connection, expire_on_commit=False)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            sess.begin_nested()

    yield session

    session.close()
    outer.rollback()
    connection.close()


def _product(asin, title, rank):
    """A Keepa product object shaped like the real API (rank at stats.current[3])."""
    return {"asin": asin, "title": title, "stats": {"current": [0, 0, 0, rank]}}


class FakeKeepaClient:
    def __init__(self, *, asin_list=None, products=None, fail_on=None):
        self._asin_list = asin_list or []
        self._products = products or {}
        self._fail_on = fail_on

    def get_bestsellers(self, category_id, **_kw):
        if self._fail_on == "bestsellers":
            raise KeepaTransientError("bestsellers unavailable")
        return {"bestSellersList": {"asinList": self._asin_list}, "tokensLeft": 100}

    def get_products(self, asins, **_kw):
        if self._fail_on == "products":
            raise KeepaRateLimitError("quota exhausted")
        return {
            "products": [self._products[a] for a in asins if a in self._products],
            "tokensLeft": 90,
        }


def _count(session, model, **filters):
    stmt = select(func.count()).select_from(model)
    for key, value in filters.items():
        stmt = stmt.where(getattr(model, key) == value)
    return session.scalar(stmt)


def _event_types(session, run_id):
    rows = session.scalars(select(Event.event_type).where(Event.run_id == run_id)).all()
    return sorted(rows)


class TestTwoRuns:
    """Two fixture-driven runs: discovery then rank improvement."""

    def test_full_pipeline_across_two_runs(self, tx_session):
        asins = ["B001", "B002", "B003"]
        run1_client = FakeKeepaClient(
            asin_list=asins,
            products={
                "B001": _product("B001", "Alpha", 5000),
                "B002": _product("B002", "Bravo", 8000),
                "B003": _product("B003", "Charlie", 12000),
            },
        )

        r1 = run_keepa_collection(tx_session, run1_client, category_id=999, max_products=10)

        assert r1.status == "succeeded"
        assert r1.new_candidates == 3
        assert r1.observations == 3
        assert r1.facts == 3
        assert r1.signals == 3
        assert set(r1.signal_types) == {"new_bestseller_detected"}

        # Candidates + ASIN mappings created.
        assert _count(tx_session, Candidate) == 3
        assert _count(tx_session, CandidateExternalId) == 3

        # Run 1 events: 3 NewProductDiscovered + 3 EvidenceCollected + 3 SignalDetected.
        # (Plus no EvidenceChanged on first sight.)
        types1 = _event_types(tx_session, r1.run_id)
        assert types1.count("NewProductDiscovered") == 3
        assert types1.count("EvidenceCollected") == 3
        assert types1.count("SignalDetected") == 3
        assert "EvidenceChanged" not in types1

        run1 = tx_session.get(CollectionRun, r1.run_id)
        assert run1.status == "succeeded"
        assert run1.candidate_id is None
        assert run1.finished_at is not None

        # --- Run 2: same ASINs, all ranks improved. ---
        run2_client = FakeKeepaClient(
            asin_list=asins,
            products={
                "B001": _product("B001", "Alpha", 3000),
                "B002": _product("B002", "Bravo", 8000),  # unchanged
                "B003": _product("B003", "Charlie", 1000),
            },
        )
        r2 = run_keepa_collection(tx_session, run2_client, category_id=999, max_products=10)

        assert r2.status == "succeeded"
        assert r2.new_candidates == 0  # dedup: no new candidates
        assert r2.observations == 3
        assert r2.facts == 3
        # Only B001 and B003 improved; B002 unchanged -> 2 rank_improved signals.
        assert r2.signals == 2
        assert set(r2.signal_types) == {"rank_improved"}

        # Still exactly 3 candidates and 3 mappings — dedup held.
        assert _count(tx_session, Candidate) == 3
        assert _count(tx_session, CandidateExternalId) == 3

        # Run 2 events: 3 EvidenceCollected, 3 EvidenceChanged (all 3 superseded a
        # prior fact), 2 SignalDetected, 0 NewProductDiscovered.
        types2 = _event_types(tx_session, r2.run_id)
        assert types2.count("EvidenceCollected") == 3
        assert types2.count("EvidenceChanged") == 3
        assert types2.count("SignalDetected") == 2
        assert "NewProductDiscovered" not in types2

        # Totals across both runs.
        assert _count(tx_session, Fact) == 6
        assert _count(tx_session, Signal) == 5  # 3 new_bestseller + 2 rank_improved


class TestZeroResults:
    def test_empty_bestseller_list_is_success(self, tx_session):
        client = FakeKeepaClient(asin_list=[], products={})
        result = run_keepa_collection(tx_session, client, category_id=1, max_products=10)

        assert result.status == "succeeded"
        assert result.new_candidates == 0
        assert result.observations == 0
        assert result.facts == 0
        assert result.signals == 0

        # No candidates/facts/signals, but the raw bestsellers response is stored.
        assert _count(tx_session, Candidate) == 0
        assert _count(tx_session, Fact) == 0
        assert _count(tx_session, Signal) == 0
        bestsellers_obs = _count(
            tx_session, RawObservation, observation_type="keepa_bestsellers"
        )
        assert bestsellers_obs == 1

        run = tx_session.get(CollectionRun, result.run_id)
        assert run.status == "succeeded"


class TestProviderFailure:
    def test_bestsellers_failure_creates_no_data(self, tx_session):
        client = FakeKeepaClient(fail_on="bestsellers")
        result = run_keepa_collection(tx_session, client, category_id=1)

        assert result.status == "failed"
        assert result.error is not None

        # No candidates, observations, facts, or signals.
        assert _count(tx_session, Candidate) == 0
        assert _count(tx_session, RawObservation) == 0
        assert _count(tx_session, Fact) == 0
        assert _count(tx_session, Signal) == 0

        # Run marked failed and a ProviderFailed event persisted.
        run = tx_session.get(CollectionRun, result.run_id)
        assert run.status == "failed"
        assert run.finished_at is not None
        types = _event_types(tx_session, result.run_id)
        assert types == ["ProviderFailed"]

    def test_products_failure_creates_no_data(self, tx_session):
        client = FakeKeepaClient(asin_list=["B001"], fail_on="products")
        result = run_keepa_collection(tx_session, client, category_id=1)

        assert result.status == "failed"
        # The bestsellers call succeeded, but because the product call failed
        # before any write, nothing was persisted.
        assert _count(tx_session, RawObservation) == 0
        assert _count(tx_session, Candidate) == 0
        assert _count(tx_session, Fact) == 0
        assert _count(tx_session, Signal) == 0

        run = tx_session.get(CollectionRun, result.run_id)
        assert run.status == "failed"
        types = _event_types(tx_session, result.run_id)
        assert types == ["ProviderFailed"]


class TestAsinDedup:
    def test_same_asin_different_title_reuses_candidate(self, tx_session):
        c1 = FakeKeepaClient(
            asin_list=["B001"], products={"B001": _product("B001", "Original Title", 5000)}
        )
        run_keepa_collection(tx_session, c1, category_id=1)

        c2 = FakeKeepaClient(
            asin_list=["B001"],
            products={"B001": _product("B001", "Completely Different Title", 4000)},
        )
        run_keepa_collection(tx_session, c2, category_id=1)

        # Identity is the ASIN, not the name — still one candidate.
        assert _count(tx_session, Candidate) == 1
        assert _count(tx_session, CandidateExternalId) == 1

        mapping = tx_session.scalar(select(CandidateExternalId))
        assert mapping.external_id == "B001"
