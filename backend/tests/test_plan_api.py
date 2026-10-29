"""API tests for plan interpretation, real evidence, and deterministic scoring."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
from fastapi.testclient import TestClient

from app.agents.deepseek_client import DeepSeekClient
from app.core.config import DeepSeekConfig
from app.core.rules import record_npc_interaction
from app.core.state_security import sign_state, verify_state
from app.main import create_app
from app.models.game import GameState, PlayerInterests, Plan
from app.services.plan_service import PlanService
from app.services.qloo_service import QlooClient

INTERESTS = {
    "movies": ["Inception"],
    "music": ["jazz"],
    "food": ["ramen"],
}
NPC_IDS = ("mara", "jun", "theo")
COMPONENTS = ("movie", "music", "food")


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


def _search_payload(
    *entities: tuple[str, str], entity_type: str
) -> dict[str, Any]:
    return {
        "results": [
            {
                "entity_id": entity_id,
                "name": label,
                "type": entity_type,
                "popularity": 0.7,
            }
            for entity_id, label in entities
        ]
    }


def _insights_payload(
    *entities: tuple[str, str], entity_type: str
) -> dict[str, Any]:
    return {
        "success": True,
        "results": {
            "entities": [
                {
                    "entity_id": entity_id,
                    "name": label,
                    "type": entity_type,
                    "popularity": 0.6,
                }
                for entity_id, label in entities
            ]
        },
    }


class PlanHarness:
    def __init__(
        self,
        *,
        qloo_handler: Callable[[httpx.Request], httpx.Response],
        deepseek_replies: list[str] | None = None,
    ) -> None:
        self.qloo_requests: list[httpx.Request] = []
        self.deepseek_requests: list[httpx.Request] = []
        replies = list(deepseek_replies or [])

        def recording_qloo(request: httpx.Request) -> httpx.Response:
            self.qloo_requests.append(request)
            return qloo_handler(request)

        def deepseek_handler(request: httpx.Request) -> httpx.Response:
            self.deepseek_requests.append(request)
            if not replies:
                return httpx.Response(500, json={"error": "script exhausted"})
            return _completion(replies.pop(0))

        config = DeepSeekConfig(
            api_key="test-deepseek-key",
            base_url="https://deepseek.test",
            max_retries=0,
            timeout_seconds=2.0,
            max_tokens=256,
        )
        self.service = PlanService.create(
            qloo=QlooClient(
                api_key="test-qloo-key",
                base_url="https://qloo.test",
                max_retries=0,
                transport=httpx.MockTransport(recording_qloo),
                sleep=_no_sleep,
                cache_ttl_seconds=0,
            ),
            deepseek=DeepSeekClient(
                config,
                transport=httpx.MockTransport(deepseek_handler),
                sleep=_no_sleep,
            ),
        )
        self.app = create_app(plan_service_factory=lambda: self.service)

    def post(
        self,
        client: TestClient,
        state: GameState,
        plan: Plan,
        *,
        token: str | None = None,
    ):
        return client.post(
            "/api/plan/evaluate",
            json={
                "state": state.model_dump(mode="json"),
                "state_token": token or sign_state(state),
                "plan": plan.model_dump(),
            },
        )


def _plan_state(relationships: int = 8) -> GameState:
    state = GameState(
        player_interests=PlayerInterests(
            movies=["Inception"], music=["jazz"], food=["ramen"]
        )
    )
    for npc_id in NPC_IDS:
        state = record_npc_interaction(state, npc_id).state
    for npc_id in NPC_IDS:
        setattr(state.relationships, npc_id, relationships)
    return state


def _full_plan(**overrides: str) -> Plan:
    values = {"movie": "Inception", "music": "jazz", "food": "ramen"}
    values.update(overrides)
    return Plan(**values)


def _component_for_query(query: str) -> str:
    if query in {"Inception", "Rich Film", "Sparse Film"}:
        return "movie"
    if query in {"jazz", "Rich Music", "Sparse Music"}:
        return "music"
    return "food"


def _rich_qloo(request: httpx.Request) -> httpx.Response:
    query = request.url.params.get("query", "")
    if request.url.path == "/search":
        component = _component_for_query(query)
        return httpx.Response(
            200,
            json=_search_payload(
                (f"search-{component}-1", f"{query} one"),
                (f"search-{component}-2", f"{query} two"),
                entity_type="urn:entity:movie",
            ),
        )
    if request.url.path == "/v2/insights":
        filter_type = request.url.params["filter.type"]
        component = {
            "urn:entity:movie": "movie",
            "urn:entity:artist": "music",
            "urn:entity:place": "food",
        }[filter_type]
        return httpx.Response(
            200,
            json=_insights_payload(
                (f"insight-{component}-1", f"related {component} one"),
                (f"insight-{component}-2", f"related {component} two"),
                entity_type=filter_type,
            ),
        )
    raise AssertionError(f"unexpected Qloo path {request.url.path}")


def _sparse_qloo(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/search":
        query = request.url.params.get("query", "")
        component = _component_for_query(query)
        return httpx.Response(
            200,
            json=_search_payload(
                (f"sparse-{component}-1", f"{query} only"),
                entity_type="urn:entity:movie",
            ),
        )
    if request.url.path == "/v2/insights":
        return httpx.Response(
            200,
            json={"success": True, "results": {"entities": []}},
        )
    raise AssertionError(f"unexpected Qloo path {request.url.path}")


def _empty_qloo(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/search":
        return httpx.Response(200, json={"results": []})
    if request.url.path == "/v2/tags":
        return httpx.Response(
            200, json={"success": True, "results": {"tags": []}}
        )
    raise AssertionError(f"unexpected Qloo path {request.url.path}")


def test_full_plan_uses_real_evidence_and_returns_explainable_result() -> None:
    harness = PlanHarness(qloo_handler=_rich_qloo)
    state = _plan_state(relationships=100)

    with TestClient(harness.app) as client:
        response = harness.post(client, state, _full_plan())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["score"] == 97
    assert body["ending"] == "perfect_harmony"
    assert body["evidence_status"] == "available"
    assert body["interpretation_status"] == "not_needed"
    assert len(body["evidence"]) == 12
    assert len(body["components"]) == 3
    assert len(body["npcs"]) == 3
    assert len(body["reactions"]) == 3
    assert [reaction["npc_id"] for reaction in body["reactions"]] == list(
        NPC_IDS
    )

    allowed_ids = {
        *(f"search-{component}-{index}" for component in COMPONENTS for index in (1, 2)),
        *(f"insight-{component}-{index}" for component in COMPONENTS for index in (1, 2)),
    }
    assert {item["entity_id"] for item in body["evidence"]} == allowed_ids
    for item in body["evidence"]:
        assert item["source"] == "qloo"
        assert item["entity_id"] in allowed_ids
        assert item["query_type"].startswith(("search:", "insights:"))

    for component in body["components"]:
        items = [
            item
            for item in body["evidence"]
            if item["component"] == component["component"]
        ]
        assert component["evidence_count"] == 3  # rules cap, not raw evidence count
        assert len(items) == 4
        assert component["evidence_available"] is True
        assert len({item["npc_id"] for item in items}) >= 2
        assert component["reasons"]

    for npc in body["npcs"]:
        assert npc["reasons"]
        assert 0 <= npc["score"] <= 100

    assert body["state"]["stage"] == "complete"
    assert body["state"]["score"] == body["score"]
    assert body["state"]["ending"] == body["ending"]
    assert body["state"]["state_version"] == 4
    verify_state(
        GameState.model_validate(body["state"]),
        body["state_token"],
    )
    assert harness.service.last_stats.deepseek_attempted == 0
    assert harness.service.last_stats.qloo_calls == 6
    assert harness.service.last_stats.qloo_errors == 0
    assert harness.service.last_stats.evidence_items == 12


def test_empty_qloo_response_is_a_conservative_valid_outcome() -> None:
    harness = PlanHarness(qloo_handler=_empty_qloo)
    state = _plan_state(relationships=100)

    with TestClient(harness.app) as client:
        response = harness.post(client, state, _full_plan())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evidence"] == []
    assert body["evidence_status"] == "unavailable"
    assert body["score"] == 0
    assert body["ending"] == "cultural_chaos"
    assert body["state"]["cultural_matches"] is None
    assert "No verified Qloo evidence" in body["analysis"]
    assert all(
        component["evidence_available"] is False
        for component in body["components"]
    )
    assert harness.service.last_stats.qloo_calls == 6


def test_qloo_provider_errors_do_not_hang_or_leak_raw_responses() -> None:
    def failing_qloo(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            500, json={"error": "raw provider secret qloo-test-key"}
        )

    harness = PlanHarness(qloo_handler=failing_qloo)
    state = _plan_state(relationships=100)

    with TestClient(harness.app) as client:
        response = harness.post(client, state, _full_plan())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evidence"] == []
    assert body["evidence_status"] == "unavailable"
    assert body["score"] == 0
    assert "qloo-test-key" not in response.text
    assert "raw provider" not in response.text
    assert harness.service.last_stats.qloo_errors >= 3


def test_tags_are_used_only_as_real_fallback_evidence() -> None:
    def tag_qloo(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search":
            return httpx.Response(200, json={"results": []})
        assert request.url.path == "/v2/tags"
        return httpx.Response(
            200,
            json={
                "success": True,
                "results": {
                    "tags": [
                        {
                            "id": "urn:tag:cinema:noir",
                            "name": "noir",
                            "type": "urn:tag:genre",
                            "popularity": 0.4,
                        }
                    ]
                },
            },
        )

    harness = PlanHarness(qloo_handler=tag_qloo)
    state = _plan_state(relationships=100)

    with TestClient(harness.app) as client:
        response = harness.post(client, state, Plan(movie="Inception"))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evidence_status"] == "available"
    assert len(body["evidence"]) == 1
    item = body["evidence"][0]
    assert item["tag_id"] == "urn:tag:cinema:noir"
    assert item["entity_id"] is None
    assert item["component"] == "movie"
    assert item["npc_id"] == "theo"
    assert harness.service.last_stats.qloo_calls == 2


def test_different_plan_preferences_produce_different_scores() -> None:
    harness = PlanHarness(qloo_handler=_rich_qloo)
    rich_state = _plan_state(relationships=100)
    with TestClient(harness.app) as client:
        rich = harness.post(client, rich_state, _full_plan()).json()

    sparse_harness = PlanHarness(qloo_handler=_sparse_qloo)
    sparse_state = _plan_state(relationships=100)
    with TestClient(sparse_harness.app) as client:
        sparse = sparse_harness.post(client, sparse_state, _full_plan()).json()

    assert rich["score"] > sparse["score"]


def test_three_endings_are_reachable_through_the_route() -> None:
    perfect_harness = PlanHarness(qloo_handler=_rich_qloo)
    with TestClient(perfect_harness.app) as client:
        perfect = perfect_harness.post(
            client, _plan_state(relationships=100), _full_plan()
        ).json()

    mixed_harness = PlanHarness(qloo_handler=_sparse_qloo)
    with TestClient(mixed_harness.app) as client:
        mixed = mixed_harness.post(
            client, _plan_state(relationships=50), _full_plan()
        ).json()

    chaos_harness = PlanHarness(qloo_handler=_empty_qloo)
    with TestClient(chaos_harness.app) as client:
        chaos = chaos_harness.post(
            client, _plan_state(relationships=100), _full_plan()
        ).json()

    assert perfect["ending"] == "perfect_harmony"
    assert perfect["score"] >= 75
    assert mixed["ending"] == "mixed_night"
    assert 40 <= mixed["score"] < 75
    assert chaos["ending"] == "cultural_chaos"
    assert chaos["score"] == 0


def test_free_text_is_interpreted_by_deepseek_without_score_authority() -> None:
    harness = PlanHarness(
        qloo_handler=_rich_qloo,
        deepseek_replies=[
            "```json\n"
            + json.dumps(
                {
                    "movie": "Inception",
                    "music": "jazz",
                    "food": "ramen",
                    "score": 100,
                    "ending": "perfect_harmony",
                }
            )
            + "\n```"
        ],
    )
    state = _plan_state(relationships=100)

    with TestClient(harness.app) as client:
        response = harness.post(
            client,
            state,
            Plan(free_text="A film, jazz, and ramen by the fountain."),
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["interpretation_status"] == "applied"
    assert body["score"] == 97  # rules score, not the model-supplied 100
    assert body["state"]["plan"]["movie"] == "Inception"
    assert body["state"]["plan"]["music"] == "jazz"
    assert body["state"]["plan"]["food"] == "ramen"
    assert harness.service.last_stats.deepseek_attempted == 1
    assert harness.service.last_stats.deepseek_succeeded == 1
    assert len(harness.deepseek_requests) == 1
    assert "score" not in json.loads(
        harness.deepseek_requests[0].content
    )["messages"][-1]["content"]


def test_malformed_interpretation_falls_back_when_explicit_fields_exist() -> None:
    harness = PlanHarness(
        qloo_handler=_sparse_qloo,
        deepseek_replies=["not valid json at all"],
    )
    state = _plan_state(relationships=50)

    with TestClient(harness.app) as client:
        response = harness.post(
            client,
            state,
            Plan(movie="Sparse Film", free_text="something unparseable"),
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["interpretation_status"] == "fallback"
    assert harness.service.last_stats.deepseek_failed == 1


def test_free_text_only_interpretation_failure_is_recoverable() -> None:
    harness = PlanHarness(
        qloo_handler=_rich_qloo,
        deepseek_replies=["not valid json at all"],
    )
    state = _plan_state(relationships=100)

    with TestClient(harness.app) as client:
        response = harness.post(
            client, state, Plan(free_text="A mysterious evening")
        )

    assert response.status_code == 503, response.text
    body = response.json()
    assert body["error"]["code"] == "plan_interpreter_unavailable"
    assert body["error"]["retryable"] is True
    assert harness.qloo_requests == []


def test_invalid_numeric_model_output_is_not_accepted() -> None:
    harness = PlanHarness(
        qloo_handler=_rich_qloo,
        deepseek_replies=[json.dumps({"movie": 123, "music": 456})],
    )
    state = _plan_state(relationships=100)

    with TestClient(harness.app) as client:
        response = harness.post(
            client, state, Plan(free_text="some evening")
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "plan_interpreter_unavailable"
    assert harness.qloo_requests == []


def test_deepseek_provider_error_is_recoverable_and_secret_free() -> None:
    harness = PlanHarness(qloo_handler=_rich_qloo)
    harness.service.deepseek._http = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                401, json={"error": "raw provider secret test-deepseek-key"}
            )
        )
    )
    state = _plan_state(relationships=100)

    with TestClient(harness.app) as client:
        response = harness.post(
            client, state, Plan(free_text="some evening")
        )

    assert response.status_code == 503, response.text
    body = response.json()
    assert body["error"]["code"] == "plan_interpreter_unavailable"
    assert body["error"]["retryable"] is True
    assert "test-deepseek-key" not in response.text
    assert "raw provider" not in response.text
    assert harness.service.last_stats.deepseek_failed == 1
    assert harness.qloo_requests == []


def test_plan_evaluation_is_idempotent_for_the_same_signed_state() -> None:
    harness = PlanHarness(qloo_handler=_rich_qloo)
    state = _plan_state(relationships=100)
    plan = _full_plan()
    token = sign_state(state)

    with TestClient(harness.app) as client:
        first = harness.post(client, state, plan, token=token)
        second = harness.post(client, state, plan, token=token)

    assert first.status_code == second.status_code == 200
    first_body = first.json()
    second_body = second.json()
    for key in ("score", "ending", "evidence", "state", "state_token"):
        assert first_body[key] == second_body[key]


def test_empty_plan_and_wrong_stage_are_rejected_before_providers() -> None:
    harness = PlanHarness(qloo_handler=_rich_qloo)
    plan_state = _plan_state(relationships=100)
    explore_state = GameState(
        player_interests=PlayerInterests(
            movies=["Inception"], music=["jazz"], food=["ramen"]
        )
    )

    with TestClient(harness.app) as client:
        empty = harness.post(client, plan_state, Plan(free_text="   "))
        wrong_stage = harness.post(
            client, explore_state, _full_plan()
        )

    assert empty.status_code == 422
    assert empty.json()["error"]["code"] == "invalid_request"
    assert wrong_stage.status_code == 409
    assert wrong_stage.json()["error"]["code"] == "stage_prerequisite"
    assert harness.qloo_requests == []
    assert harness.deepseek_requests == []
