"""Tests for the validated game-start route and initial GameState."""

from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.game import MAX_INTERESTS_PER_CATEGORY, MAX_INTEREST_LENGTH

VALID_INTERESTS = {
    "movies": ["Inception", "Spirited Away"],
    "music": ["jazz"],
    "food": ["ramen"],
}


def _payload(**overrides: object) -> dict[str, object]:
    interests = {**VALID_INTERESTS, **overrides}
    return {"player_interests": interests}


def _assert_error_envelope(response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "retryable"}
    assert body["error"]["code"] == code
    assert body["error"]["retryable"] is False
    assert body["error"]["message"]


def test_start_returns_fresh_initial_state() -> None:
    with TestClient(app) as client:
        response = client.post("/api/game/start", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"state"}

    state = body["state"]
    assert state["player_interests"] == VALID_INTERESTS
    UUID(state["session_id"])
    assert state["stage"] == "explore"
    assert state["relationships"] == {"mara": 0, "jun": 0, "theo": 0}
    assert len(set(state["relationships"].values())) == 1
    assert state["clues"] == []
    assert state["plan"] is None
    assert state["score"] is None
    assert state["ending"] is None


def test_start_is_independent_on_every_call() -> None:
    with TestClient(app) as client:
        first = client.post("/api/game/start", json=_payload()).json()["state"]
        second = client.post("/api/game/start", json=_payload()).json()["state"]

    assert first["session_id"] != second["session_id"]
    assert first["relationships"] == second["relationships"]
    assert first["clues"] == second["clues"] == []
    assert first["player_interests"] == second["player_interests"]

    # Mutating one response must not bleed into a later server response.
    first["relationships"]["mara"] = 100
    first["clues"].append(
        {
            "clue_id": "local-only",
            "npc_id": "mara",
            "text": "not from the server",
            "tags": [],
        }
    )
    with TestClient(app) as client:
        third = client.post("/api/game/start", json=_payload()).json()["state"]

    assert third["relationships"] == {"mara": 0, "jun": 0, "theo": 0}
    assert third["clues"] == []
    assert third["session_id"] not in {first["session_id"], second["session_id"]}


def test_start_trims_whitespace_around_interests() -> None:
    payload = _payload(
        movies=["  Inception  "],
        music=["\t jazz \n"],
        food=["  ramen  "],
    )
    with TestClient(app) as client:
        response = client.post("/api/game/start", json=payload)

    assert response.status_code == 200
    assert response.json()["state"]["player_interests"] == {
        "movies": ["Inception"],
        "music": ["jazz"],
        "food": ["ramen"],
    }


def test_start_accepts_one_category_and_empty_other_lists() -> None:
    payload = _payload(movies=["Inception"], music=[], food=[])
    with TestClient(app) as client:
        response = client.post("/api/game/start", json=payload)

    assert response.status_code == 200
    assert response.json()["state"]["player_interests"]["movies"] == ["Inception"]


def test_start_accepts_maximum_list_and_string_lengths() -> None:
    longest = "x" * MAX_INTEREST_LENGTH
    payload = _payload(
        movies=[longest] * MAX_INTERESTS_PER_CATEGORY,
        music=[],
        food=[],
    )
    with TestClient(app) as client:
        response = client.post("/api/game/start", json=payload)

    assert response.status_code == 200
    assert response.json()["state"]["player_interests"]["movies"] == [
        longest
    ] * MAX_INTERESTS_PER_CATEGORY


@pytest.mark.parametrize(
    "payload",
    [
        {"player_interests": {"movies": [], "music": [], "food": []}},
        {"player_interests": {"movies": ["   "], "music": [], "food": []}},
        {"player_interests": {"movies": ["Inception"]}},
        {"player_interests": {"movies": []}},
        {"player_interests": []},
        {"player_interests": {}},
        {},
        [],
    ],
)
def test_start_rejects_empty_or_missing_interests(payload: object) -> None:
    with TestClient(app) as client:
        response = client.post("/api/game/start", json=payload)

    _assert_error_envelope(response, 422, "invalid_request")


@pytest.mark.parametrize(
    "overrides",
    [
        {"movies": ["x"] * (MAX_INTERESTS_PER_CATEGORY + 1)},
        {"movies": ["x" * (MAX_INTEREST_LENGTH + 1)]},
        {"movies": [""]},
        {"movies": [None]},
        {"movies": [42]},
        {"movies": ["Inception", "Inception"], "music": ["x"] * 6},
    ],
)
def test_start_rejects_interest_boundary_violations(
    overrides: dict[str, object],
) -> None:
    with TestClient(app) as client:
        response = client.post("/api/game/start", json=_payload(**overrides))

    _assert_error_envelope(response, 422, "invalid_request")


@pytest.mark.parametrize(
    "payload",
    [
        {
            "player_interests": VALID_INTERESTS,
            "stage": "explore",
        },
        {
            "player_interests": VALID_INTERESTS,
            "session_id": "00000000-0000-0000-0000-000000000000",
        },
        {
            "player_interests": {
                **VALID_INTERESTS,
                "books": ["Dune"],
            }
        },
        {
            "player_interests": VALID_INTERESTS,
            "unexpected": True,
        },
        {
            "player_interests": VALID_INTERESTS,
            "relationships": {"mara": 100, "jun": 100, "theo": 100},
        },
    ],
)
def test_start_rejects_unknown_or_server_owned_fields(payload: object) -> None:
    with TestClient(app) as client:
        response = client.post("/api/game/start", json=payload)

    _assert_error_envelope(response, 422, "invalid_request")


def test_start_rejects_malformed_json() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/game/start",
            content=b'{"player_interests": ',
            headers={"content-type": "application/json"},
        )

    _assert_error_envelope(response, 422, "invalid_request")
    assert "player_interests" not in response.json()["error"]["message"]
