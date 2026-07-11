"""Candidate CRUD endpoints."""

import uuid


def _create(client, name="LED Dog Collar", **extra):
    response = client.post("/candidates", json={"name": name, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_create_candidate_with_defaults(client):
    body = _create(client, niche="pets")
    assert body["name"] == "LED Dog Collar"
    assert body["niche"] == "pets"
    assert body["status"] == "new"
    assert body["seed_urls"] == []
    assert body["notes"] is None
    uuid.UUID(body["id"])  # valid UUID
    assert body["created_at"].endswith(("Z", "+00:00")) or "+" in body["created_at"]


def test_create_rejects_blank_and_whitespace_names(client):
    for bad_name in ("", "   ", "\t\n"):
        response = client.post("/candidates", json={"name": bad_name})
        assert response.status_code == 422, bad_name


def test_create_trims_surrounding_whitespace(client):
    body = _create(client, name="  Neck Massager  ")
    assert body["name"] == "Neck Massager"


def test_get_candidate(client):
    created = _create(client)
    response = client.get(f"/candidates/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_candidate_is_structured_404(client):
    response = client.get(f"/candidates/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


def test_get_malformed_uuid_is_422(client):
    assert client.get("/candidates/not-a-uuid").status_code == 422


def test_list_supports_status_filter_and_pagination(client):
    created = _create(client, name="Posture Corrector")
    client.patch(f"/candidates/{created['id']}", json={"status": "collecting"})

    listed = client.get("/candidates", params={"status": "collecting", "limit": 5}).json()
    assert listed["limit"] == 5
    assert listed["total"] >= 1
    assert all(c["status"] == "collecting" for c in listed["items"])
    assert any(c["id"] == created["id"] for c in listed["items"])

    # Pagination window excludes what came before it.
    page2 = client.get("/candidates", params={"limit": 1, "offset": 1}).json()
    page1 = client.get("/candidates", params={"limit": 1, "offset": 0}).json()
    if page2["items"]:
        assert page1["items"][0]["id"] != page2["items"][0]["id"]


def test_list_rejects_out_of_range_pagination(client):
    assert client.get("/candidates", params={"limit": 0}).status_code == 422
    assert client.get("/candidates", params={"limit": 201}).status_code == 422
    assert client.get("/candidates", params={"offset": -1}).status_code == 422


def test_list_rejects_unknown_status(client):
    assert client.get("/candidates", params={"status": "yolo"}).status_code == 422


def test_patch_updates_only_provided_fields(client):
    created = _create(client, niche="pets", notes="original")
    response = client.patch(
        f"/candidates/{created['id']}",
        json={"status": "collecting", "seed_urls": ["https://example.com/ad"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "collecting"
    assert body["seed_urls"] == ["https://example.com/ad"]
    assert body["niche"] == "pets"  # untouched
    assert body["notes"] == "original"  # untouched


def test_patch_rejects_invalid_status_and_blank_name(client):
    created = _create(client)
    assert (
        client.patch(f"/candidates/{created['id']}", json={"status": "launched"}).status_code == 422
    )
    assert client.patch(f"/candidates/{created['id']}", json={"name": "  "}).status_code == 422


def test_patch_unknown_candidate_is_404(client):
    assert client.patch(f"/candidates/{uuid.uuid4()}", json={"status": "new"}).status_code == 404


def test_candidates_have_no_delete_endpoint(client):
    created = _create(client)
    assert client.delete(f"/candidates/{created['id']}").status_code == 405
