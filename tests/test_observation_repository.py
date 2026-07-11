"""The raw-observation repository: create/read only, no mutation surface."""

import uuid
from datetime import UTC, datetime

import pytest
from app.ingestion.models import Source
from app.ingestion.repository import RawObservationRepository


@pytest.fixture()
def source(db_session):
    src = Source(key="manual-repo-test", display_name="Manual (repo test)", compliance="manual")
    db_session.add(src)
    db_session.flush()
    return src


@pytest.fixture()
def repo(db_session):
    return RawObservationRepository(db_session)


def test_create_and_get_round_trip(repo, source):
    created = repo.create(
        source_id=source.id,
        observation_type="manual_note",
        payload={"note": "saw this on three ads today"},
        source_url="https://example.com/ad",
        fetched_at=datetime.now(UTC),
    )

    fetched = repo.get(created.id)
    assert fetched is not None
    assert fetched.payload == {"note": "saw this on three ads today"}
    assert fetched.source_url == "https://example.com/ad"
    assert fetched.fetched_at.tzinfo is not None


def test_create_rejects_naive_timestamps(repo, source):
    with pytest.raises(ValueError, match="timezone-aware"):
        repo.create(
            source_id=source.id,
            observation_type="manual_note",
            payload={},
            fetched_at=datetime(2026, 7, 11, 12, 0, 0),  # no tzinfo
        )


def test_get_missing_returns_none(repo):
    assert repo.get(uuid.uuid4()) is None


def test_list_for_source_returns_only_that_source(repo, source, db_session):
    other = Source(key="other-repo-test", display_name="Other", compliance="manual")
    db_session.add(other)
    db_session.flush()

    mine = repo.create(
        source_id=source.id,
        observation_type="manual_note",
        payload={"note": "mine"},
        fetched_at=datetime.now(UTC),
    )
    repo.create(
        source_id=other.id,
        observation_type="manual_note",
        payload={"note": "someone else's"},
        fetched_at=datetime.now(UTC),
    )

    listed = repo.list_for_source(source.id)
    assert [o.id for o in listed] == [mine.id]


def test_create_normalizes_fetched_at_to_utc(repo, source):
    from datetime import timedelta, timezone

    plus_two = timezone(timedelta(hours=2))
    created = repo.create(
        source_id=source.id,
        observation_type="manual_note",
        payload={},
        fetched_at=datetime(2026, 7, 10, 14, 30, tzinfo=plus_two),
    )
    assert created.fetched_at.utcoffset() == timedelta(0)
    assert (created.fetched_at.hour, created.fetched_at.minute) == (12, 30)


def test_list_for_candidate_pages_newest_first(repo, source, db_session):
    from app.catalog.repository import CandidateRepository

    candidate = CandidateRepository(db_session).create(name="Repo pagination target")
    created = [
        repo.create(
            source_id=source.id,
            candidate_id=candidate.id,
            observation_type="manual_note",
            payload={"n": i},
            fetched_at=datetime.now(UTC),
        )
        for i in range(3)
    ]

    # Within one transaction Postgres gives every row the same created_at
    # (now() is transaction-scoped), so the deterministic expectation is the
    # query's own ordering: created_at DESC, then id DESC as tie-breaker.
    expected = sorted(created, key=lambda o: (o.created_at, str(o.id)), reverse=True)

    items, total = repo.list_for_candidate(candidate.id)
    assert total == 3
    assert [o.id for o in items] == [o.id for o in expected]

    page, total = repo.list_for_candidate(candidate.id, limit=1, offset=1)
    assert total == 3
    assert [o.id for o in page] == [expected[1].id]


def test_repository_has_no_update_or_delete_surface():
    forbidden = [
        name
        for name in dir(RawObservationRepository)
        if not name.startswith("_") and ("update" in name or "delete" in name or "remove" in name)
    ]
    assert forbidden == [], f"append-only repository must not expose: {forbidden}"
