"""Tests for the fixed NPC catalog routes."""

from fastapi.testclient import TestClient

from app.main import app

EXPECTED_NPCS = [
    ("mara", "Mara", "Baker"),
    ("jun", "Jun", "Record shop owner"),
    ("theo", "Theo", "Town storyteller"),
]


def _assert_error_envelope(response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "retryable"}
    assert body["error"]["code"] == code
    assert body["error"]["retryable"] is False
    assert body["error"]["message"]


def test_list_npcs_returns_the_three_fixed_residents() -> None:
    with TestClient(app) as client:
        response = client.get("/api/npcs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    npcs = response.json()
    assert isinstance(npcs, list)
    assert [(npc["id"], npc["name"], npc["role"]) for npc in npcs] == EXPECTED_NPCS


def test_npc_profiles_have_distinct_public_metadata_only() -> None:
    with TestClient(app) as client:
        npcs = client.get("/api/npcs").json()

    assert len({npc["personality"] for npc in npcs}) == 3
    assert len({tuple(npc["cultural_interests"]) for npc in npcs}) == 3
    for npc in npcs:
        assert npc["greeting"]
        assert len(npc["cultural_interests"]) >= 2
        serialized = str(npc).lower()
        assert "system_prompt" not in serialized
        assert "system prompt" not in serialized


def test_get_known_npc_returns_the_same_profile() -> None:
    with TestClient(app) as client:
        catalog = client.get("/api/npcs").json()
        response = client.get("/api/npcs/jun")

    assert response.status_code == 200
    assert response.json() == catalog[1]


def test_unknown_npc_returns_consistent_error_envelope() -> None:
    with TestClient(app) as client:
        response = client.get("/api/npcs/not-a-resident")

    _assert_error_envelope(response, 404, "npc_not_found")
