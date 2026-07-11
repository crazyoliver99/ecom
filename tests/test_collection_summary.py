"""Tests for the deterministic collection summary and morning report."""

from datetime import UTC, datetime

import pytest
from app.collection.autonomy import run_keepa_collection_cycle
from app.collection.models import CollectionSummary
from app.collection.summary import (
    compute_summary_fields,
    format_summary,
    get_latest_successful_summary,
)
from app.ingestion.models import CollectionRun, Source
from sqlalchemy import select

from tests.conftest import FakeKeepaClient
from tests.conftest import keepa_product as product


def _run_cycle(session, client, **kw):
    return run_keepa_collection_cycle(session, client, category_id=555, **kw)


class TestSummaryContents:
    def test_summary_counts_match_run(self, tx_session):
        client = FakeKeepaClient(
            asin_list=["B1", "B2", "B3"],
            products={
                "B1": product("B1", "One", 4000),
                "B2": product("B2", "Two", 7000),
                "B3": product("B3", "Three", 9000),
            },
        )
        outcome = _run_cycle(tx_session, client, max_products=10)
        s = outcome.summary

        assert s is not None
        assert s.status == "succeeded"
        assert s.candidates_discovered == 3
        assert s.new_candidates == 3
        assert s.existing_candidates_updated == 0
        # 3 product observations + 1 raw bestsellers blob.
        assert s.observations_stored == 4
        assert s.facts_created == 3
        assert s.signals_emitted == 3  # all new_bestseller_detected
        # 3 NewProductDiscovered + 3 EvidenceCollected + 3 SignalDetected.
        assert s.events_emitted == 9
        assert s.provider_warnings == []
        assert s.provider_errors == []
        assert s.duration_seconds is not None and s.duration_seconds >= 0
        assert s.started_at is not None and s.finished_at is not None

        # Persisted exactly once, linked to the run.
        assert get_latest_successful_summary(tx_session).id == s.id

    def test_second_cycle_counts_existing_and_improvements(self, tx_session):
        c1 = FakeKeepaClient(
            asin_list=["B1", "B2"],
            products={"B1": product("B1", "One", 5000), "B2": product("B2", "Two", 8000)},
        )
        _run_cycle(tx_session, c1, max_products=10)

        c2 = FakeKeepaClient(
            asin_list=["B1", "B2"],
            products={"B1": product("B1", "One", 3000), "B2": product("B2", "Two", 8000)},
        )
        outcome2 = _run_cycle(tx_session, c2, max_products=10)
        s = outcome2.summary

        assert s.new_candidates == 0
        assert s.existing_candidates_updated == 2
        assert s.candidates_discovered == 2
        assert s.facts_created == 2
        assert s.signals_emitted == 1  # only B1 improved
        # 2 EvidenceCollected + 2 EvidenceChanged + 1 SignalDetected.
        assert s.events_emitted == 5

        # morning-report shows the latest (second) summary.
        assert get_latest_successful_summary(tx_session).id == s.id

    def test_warnings_recorded_for_missing_products(self, tx_session):
        # B2 is in the bestseller list but the product endpoint omits it.
        client = FakeKeepaClient(
            asin_list=["B1", "B2"],
            products={"B1": product("B1", "One", 5000)},
        )
        outcome = _run_cycle(tx_session, client, max_products=10)
        s = outcome.summary

        assert s.candidates_discovered == 1
        assert len(s.provider_warnings) == 1
        assert "B2" in s.provider_warnings[0]


class TestZeroAndFailure:
    def test_zero_results_still_summarized(self, tx_session):
        client = FakeKeepaClient(asin_list=[], products={})
        outcome = _run_cycle(tx_session, client, max_products=10)
        s = outcome.summary
        assert s is not None
        assert s.status == "succeeded"
        assert s.candidates_discovered == 0
        assert s.new_candidates == 0
        assert s.facts_created == 0
        assert s.signals_emitted == 0
        assert s.observations_stored == 1  # the bestsellers blob

    def test_failed_run_produces_no_summary(self, tx_session):
        client = FakeKeepaClient(fail_on="bestsellers")
        outcome = _run_cycle(tx_session, client)
        assert outcome.result.status == "failed"
        assert outcome.summary is None
        assert get_latest_successful_summary(tx_session) is None


class TestAppendOnly:
    def _summary_row(self, db_session):
        source = db_session.scalar(select(Source).where(Source.key == "keepa"))
        run = CollectionRun(source_id=source.id, status="succeeded", started_at=datetime.now(UTC))
        db_session.add(run)
        db_session.flush()
        summary = CollectionSummary(
            run_id=run.id,
            status="succeeded",
            candidates_discovered=0,
            new_candidates=0,
            existing_candidates_updated=0,
            observations_stored=0,
            facts_created=0,
            signals_emitted=0,
            events_emitted=0,
        )
        db_session.add(summary)
        db_session.flush()
        return summary

    def test_summary_update_rejected(self, db_session):
        summary = self._summary_row(db_session)
        summary.new_candidates = 999
        with pytest.raises(Exception, match="append-only"):
            db_session.flush()

    def test_summary_delete_rejected(self, db_session):
        summary = self._summary_row(db_session)
        db_session.delete(summary)
        with pytest.raises(Exception, match="append-only"):
            db_session.flush()


class TestFormatting:
    def test_format_is_readable_and_complete(self, tx_session):
        client = FakeKeepaClient(
            asin_list=["B1", "B2"],
            products={"B1": product("B1", "One", 5000), "B2": product("B2", "Two", 9000)},
        )
        s = _run_cycle(tx_session, client, max_products=10).summary
        text_out = format_summary(s)

        assert "Atlas Morning Report" in text_out
        assert "Status" in text_out and "succeeded" in text_out
        assert "Candidates discovered" in text_out
        assert "New candidates" in text_out
        assert "Existing (updated)" in text_out
        assert "Observations stored" in text_out
        assert "Facts created" in text_out
        assert "Signals emitted" in text_out
        assert "Events emitted" in text_out
        assert "Provider warnings" in text_out
        assert "Provider errors" in text_out
        assert str(s.run_id) in text_out

    def test_recomputation_is_deterministic(self, tx_session):
        """Recomputing the fields from the persisted run yields identical values —
        the summary is a pure function of what the run stored."""
        client = FakeKeepaClient(
            asin_list=["B1", "B2"],
            products={"B1": product("B1", "One", 5000), "B2": product("B2", "Two", 9000)},
        )
        outcome = _run_cycle(tx_session, client, max_products=10)
        run = tx_session.get(CollectionRun, outcome.result.run_id)

        first = compute_summary_fields(tx_session, run, outcome.result)
        second = compute_summary_fields(tx_session, run, outcome.result)
        assert first == second
        assert first["candidates_discovered"] == outcome.summary.candidates_discovered
