"""Manual evidence entry and observation retrieval."""

import uuid
from datetime import datetime


def _candidate(client, name="Evidence Target"):
    response = client.post("/candidates", json={"name": name})
    assert response.status_code == 201
    return response.json()


def _add_evidence(client, candidate_id, **body):
    body.setdefault("payload", {"note": "some evidence"})
    return client.post(f"/candidates/{candidate_id}/observations", json=body)


def test_manual_evidence_round_trip(client):
    candidate = _candidate(client)
    response = _add_evidence(
        client,
        candidate["id"],
        payload={"note": "40 near-identical ads running", "ad_count": 40},
        source_url="https://example.com/ads?q=collar",
    )
    assert response.status_code == 201, response.text
    obs = response.json()
    assert obs["candidate_id"] == candidate["id"]
    assert obs["observation_type"] == "manual_note"
    assert obs["payload"] == {"note": "40 near-identical ads running", "ad_count": 40}
    assert obs["source_url"].startswith("https://example.com/ads")
    assert obs["run_id"] is None
    # fetched_at defaulted to a timezone-aware timestamp
    assert "+00:00" in obs["fetched_at"] or obs["fetched_at"].endswith("Z")


def test_explicit_fetched_at_is_normalized_to_utc(client):
    candidate = _candidate(client)
    response = _add_evidence(client, candidate["id"], fetched_at="2026-07-10T14:30:00+02:00")
    assert response.status_code == 201
    fetched = datetime.fromisoformat(response.json()["fetched_at"])
    assert fetched.utcoffset().total_seconds() == 0
    assert (fetched.hour, fetched.minute) == (12, 30)  # 14:30+02:00 == 12:30 UTC


def test_naive_fetched_at_is_rejected(client):
    candidate = _candidate(client)
    response = _add_evidence(client, candidate["id"], fetched_at="2026-07-10T14:30:00")
    assert response.status_code == 422
    assert "timezone" in response.text


def test_invalid_source_url_is_rejected(client):
    candidate = _candidate(client)
    for bad in ("not-a-url", "ftp://example.com/file", "javascript:alert(1)"):
        response = _add_evidence(client, candidate["id"], source_url=bad)
        assert response.status_code == 422, bad


def test_evidence_for_unknown_candidate_is_404(client):
    response = _add_evidence(client, uuid.uuid4())
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_list_is_newest_first_paginated_and_isolated(client):
    mine = _candidate(client, "Mine")
    other = _candidate(client, "Other")
    ids = [_add_evidence(client, mine["id"], payload={"n": i}).json()["id"] for i in range(3)]
    _add_evidence(client, other["id"], payload={"n": "not mine"})

    listed = client.get(f"/candidates/{mine['id']}/observations").json()
    assert listed["total"] == 3
    assert [o["id"] for o in listed["items"]] == list(reversed(ids))  # newest first

    page = client.get(
        f"/candidates/{mine['id']}/observations", params={"limit": 1, "offset": 1}
    ).json()
    assert page["total"] == 3
    assert [o["id"] for o in page["items"]] == [ids[1]]


def test_list_rejects_out_of_range_pagination(client):
    candidate = _candidate(client)
    url = f"/candidates/{candidate['id']}/observations"
    assert client.get(url, params={"limit": 0}).status_code == 422
    assert client.get(url, params={"limit": 201}).status_code == 422


def test_get_single_observation_and_404(client):
    candidate = _candidate(client)
    obs = _add_evidence(client, candidate["id"]).json()

    assert client.get(f"/observations/{obs['id']}").json() == obs
    assert client.get(f"/observations/{uuid.uuid4()}").status_code == 404


def test_observations_are_immutable_over_http(client):
    candidate = _candidate(client)
    obs = _add_evidence(client, candidate["id"]).json()

    url = f"/observations/{obs['id']}"
    assert client.patch(url, json={"payload": {}}).status_code == 405
    assert client.put(url, json={"payload": {}}).status_code == 405
    assert client.delete(url).status_code == 405
    # The nested collection accepts POST/GET only.
    assert client.delete(f"/candidates/{candidate['id']}/observations").status_code == 405
