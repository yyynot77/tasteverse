"""Tests for the signed state envelope and server-authoritative transitions."""

from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi.testclient import TestClient

from app.agents.deepseek_client import DeepSeekClient
from app.agents.service import DialogueService
from app.core.config import DeepSeekConfig
from app.core.rules import record_npc_interaction
from app.core.state_security import sign_state
from app.main import create_app
from app.models.game import GameState, NpcId, PlayerInterests, Plan
from app.services.qloo_service import QlooClient, QlooConfigurationError

INTERESTS = {
    "movies": ["Inception"],
    "music": ["jazz"],
    "food": ["ramen"],
}


async def _no_sleep(_: float) -> None:
    return None


def _completion(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ]
        },
    )


class _DialogueHarness:
    def __init__(self, replies: list[str]) -> None:
        self.deepseek_requests: list[httpx.Request] = []
        scripts = [_completion(reply) for reply in replies]

        def deepseek_handler(request: httpx.Request) -> httpx.Response:
            self.deepseek_requests.append(request)
            if not scripts:
                return httpx.Response(500, json={"error": "script exhausted"})
            return scripts.pop(0)

        config = DeepSeekConfig(
            api_key="test-secret-key-for-state-tests",
            base_url="https://deepseek.test",
            max_retries=0,
            timeout_seconds=2.0,
            max_tokens=128,
        )
        self.service = DialogueService.create(
            deepseek=DeepSeekClient(
                config,
                transport=httpx.MockTransport(deepseek_handler),
                sleep=_no_sleep,
            ),
            qloo=QlooClient(
                api_key="test-qloo-key",
                base_url="https://qloo.test",
                transport=httpx.MockTransport(
                    lambda _: httpx.Response(200, json={"results": []})
                ),
                sleep=_no_sleep,
                cache_ttl_seconds=0,
            ),
        )

    def app(self, plan_factory=None):
        return create_app(
            dialogue_service_factory=lambda: self.service,
            plan_service_factory=plan_factory,
        )


def _start(client: TestClient) -> tuple[dict[str, Any], str]:
    response = client.post(
        "/api/game/start", json={"player_interests": INTERESTS}
    )
    assert response.status_code == 200
    body = response.json()
    return body["state"], body["state_token"]


def _plan_state(relationships: int = 8) -> GameState:
    state = GameState(
        player_interests=PlayerInterests(
            movies=["Inception"], music=["jazz"], food=["ramen"]
        )
    )
    for npc_id in ("mara", "jun", "theo"):
        state = record_npc_interaction(state, npc_id).state
    for npc_id in ("mara", "jun", "theo"):
        if getattr(state.relationships, npc_id) != relationships:
            setattr(state.relationships, npc_id, relationships)
    return state


def test_start_then_three_signed_dialogues_advance_to_plan() -> None:
    harness = _DialogueHarness(["Hello.", "Welcome.", "Sit down."])

    def unavailable_plan_service():
        raise QlooConfigurationError("QLOO_API_KEY is not configured.")

    with TestClient(harness.app(unavailable_plan_service)) as client:
        state, token = _start(client)
        tokens = [token]
        for npc_id in ("mara", "jun", "theo"):
            response = client.post(
                f"/api/npc/{npc_id}/dialogue",
                json={
                    "state": state,
                    "state_token": token,
                    "message": "Tell me about the festival.",
                },
            )
            assert response.status_code == 200, response.text
            body = response.json()
            state = body["state"]
            token = body["state_token"]
            tokens.append(token)

        assert state["stage"] == "plan"
        assert state["state_version"] == 3
        assert len(set(tokens)) == 4
        assert state["relationships"] == {"mara": 8, "jun": 8, "theo": 8}

        # The returned token chains into a plan request.
        response = client.post(
            "/api/plan/evaluate",
            json={
                "state": state,
                "state_token": token,
                "plan": {"movie": "Inception"},
            },
        )
        # No real Qloo credentials are configured in this test; signature and
        # stage validation happen before provider construction.
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "qloo_configuration_error"


def test_tampered_computed_fields_are_rejected_before_dialogue_provider() -> None:
    harness = _DialogueHarness([])
    with TestClient(harness.app()) as client:
        state, token = _start(client)

        tampers = [
            {"relationships": {"mara": 100, "jun": 0, "theo": 0}},
            {"stage": "plan"},
            {"score": 100},
            {"ending": "perfect_harmony"},
            {"interacted_npcs": ["mara", "jun", "theo"]},
        ]
        for change in tampers:
            tampered = {**state, **change}
            response = client.post(
                "/api/npc/mara/dialogue",
                json={
                    "state": tampered,
                    "state_token": token,
                    "message": "hello",
                },
            )
            assert response.status_code == 409, response.text
            assert response.json()["error"]["code"] == "state_integrity_error"

        assert harness.deepseek_requests == []


def test_token_from_another_session_is_rejected() -> None:
    harness = _DialogueHarness([])
    with TestClient(harness.app()) as client:
        first_state, _ = _start(client)
        second_state, second_token = _start(client)
        assert first_state["session_id"] != second_state["session_id"]

        response = client.post(
            "/api/npc/mara/dialogue",
            json={
                "state": first_state,
                "state_token": second_token,
                "message": "hello",
            },
        )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "state_integrity_error"


def test_tampered_state_is_rejected_on_plan_before_provider() -> None:
    state = _plan_state(relationships=8)
    token = sign_state(state)
    plan = Plan(movie="Inception", music="jazz", food="ramen")

    def fail_factory():
        raise AssertionError("provider factory must not run for forged state")

    app = create_app(plan_service_factory=fail_factory)
    with TestClient(app) as client:
        for change in (
            {"relationships": {"mara": 100, "jun": 100, "theo": 100}},
            {"score": 99},
            {"stage": "explore"},
        ):
            tampered = state.model_dump(mode="json")
            tampered.update(change)
            response = client.post(
                "/api/plan/evaluate",
                json={
                    "state": tampered,
                    "state_token": token,
                    "plan": plan.model_dump(),
                },
            )
            assert response.status_code == 409, response.text
            assert response.json()["error"]["code"] == "state_integrity_error"


def test_missing_token_is_a_validation_error() -> None:
    harness = _DialogueHarness([])
    with TestClient(harness.app()) as client:
        state, _ = _start(client)
        response = client.post(
            "/api/npc/mara/dialogue",
            json={"state": state, "message": "hello"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert harness.deepseek_requests == []
