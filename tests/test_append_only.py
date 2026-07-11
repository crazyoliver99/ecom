"""raw_observations must be append-only at the application layer (FOUNDATION.md §7)."""

from datetime import UTC, datetime

import pytest
from app.core.errors import AppendOnlyViolation
from app.ingestion.models import RawObservation, Source


@pytest.fixture()
def observation(db_session):
    source = Source(key="manual-test", display_name="Manual (test)", compliance="manual")
    db_session.add(source)
    db_session.flush()

    obs = RawObservation(
        source_id=source.id,
        observation_type="manual_note",
        payload={"note": "spotted this product in an ad"},
        source_url="https://example.com/evidence",
        fetched_at=datetime.now(UTC),
    )
    db_session.add(obs)
    db_session.flush()
    return obs


def test_observations_can_be_inserted(observation):
    assert observation.id is not None
    assert observation.fetched_at.tzinfo is not None


def test_observation_update_is_rejected(db_session, observation):
    observation.payload = {"note": "history revisionism"}
    with pytest.raises(AppendOnlyViolation):
        db_session.flush()


def test_observation_delete_is_rejected(db_session, observation):
    db_session.delete(observation)
    with pytest.raises(AppendOnlyViolation):
        db_session.flush()
