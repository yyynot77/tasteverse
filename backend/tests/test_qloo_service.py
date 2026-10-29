"""Tests for the async Qloo client using a mocked HTTP transport.

These tests never contact the live Qloo API and never require a real key.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.services.qloo_service import (
    SUPPORTED_INSIGHTS_FILTER_TYPES,
    QlooAuthenticationError,
    QlooClient,
    QlooConfigurationError,
    QlooEntity,
    QlooNetworkError,
    QlooRateLimitError,
    QlooRequestError,
    QlooResponseError,
    QlooServerError,
    QlooTimeoutError,
    QlooValidationError,
)

API_KEY = "test-key-do-not-leak-0123456789"
BASE_URL = "https://qloo.test"


async def _no_sleep(_: float) -> None:
    return None


def _client(
    handler: Callable[[httpx.Request], httpx.Response],
    **kwargs: Any,
) -> QlooClient:
    kwargs.setdefault("cache_ttl_seconds", 0)
    return QlooClient(
        api_key=API_KEY,
        base_url=BASE_URL,
        transport=httpx.MockTransport(handler),
        sleep=_no_sleep,
        **kwargs,
    )


def _run_with_client(
    handler: Callable[[httpx.Request], httpx.Response],
    operation: Callable[[QlooClient], Any],
    **kwargs: Any,
) -> Any:
    async def _scenario() -> Any:
        async with _client(handler, **kwargs) as client:
            return await operation(client)

    return asyncio.run(_scenario())


@pytest.fixture
def fake_dotenv(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, bool]]:
    """Record from_env's dotenv call and emulate override=False loading."""

    calls: list[tuple[Path, bool]] = []

    def _load_dotenv(*, dotenv_path: Path, override: bool) -> bool:
        calls.append((Path(dotenv_path), override))
        if not override:
            os.environ.setdefault("QLOO_BASE_URL", BASE_URL)
            os.environ.setdefault("QLOO_API_KEY", "file-only-key")
        return True

    monkeypatch.setattr("app.services.qloo_service.load_dotenv", _load_dotenv)
    return calls


def test_from_env_loads_dotenv_without_leaking_key(
    fake_dotenv: list[tuple[Path, bool]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("QLOO_BASE_URL", raising=False)
    monkeypatch.delenv("QLOO_API_KEY", raising=False)

    client = QlooClient.from_env(env_file=Path(__file__))
    try:
        assert client.base_url == BASE_URL
        assert API_KEY not in repr(client)
        assert fake_dotenv == [(Path(__file__), False)]
    finally:
        asyncio.run(client.aclose())


def test_process_environment_takes_precedence_over_dotenv(
    fake_dotenv: list[tuple[Path, bool]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QLOO_BASE_URL", BASE_URL)
    monkeypatch.setenv("QLOO_API_KEY", "process-env-key")

    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers["x-api-key"])
        return httpx.Response(200, json={"results": []})

    client = QlooClient.from_env(
        env_file=Path(__file__),
        transport=httpx.MockTransport(handler),
        sleep=_no_sleep,
        cache_ttl_seconds=0,
    )

    async def scenario() -> None:
        async with client:
            assert await client.search_entities("Inception") == []

    asyncio.run(scenario())
    assert seen == ["process-env-key"]
    assert fake_dotenv == [(Path(__file__), False)]


def test_from_env_missing_or_placeholder_key_raises_config_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = Path(__file__).with_name("does-not-exist.env")
    monkeypatch.delenv("QLOO_API_KEY", raising=False)
    with pytest.raises(QlooConfigurationError, match="QLOO_API_KEY"):
        QlooClient.from_env(env_file=missing)

    monkeypatch.setenv("QLOO_API_KEY", "replace_me")
    with pytest.raises(QlooConfigurationError, match="QLOO_API_KEY"):
        QlooClient.from_env(env_file=missing)


def test_search_success_normalizes_and_sends_expected_parameters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/search"
        assert request.headers["x-api-key"] == API_KEY
        assert request.headers["accept"] == "application/json"
        assert request.url.params["query"] == "Inception"
        assert request.url.params["types"] == "urn:entity:movie"
        assert request.url.params["take"] == "2"
        assert request.url.params["page"] == "1"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "entity_id": "movie-1",
                        "name": "Inception",
                        "types": ["urn:entity:movie"],
                        "popularity": 0.91,
                        "disambiguation": "2010 film",
                    }
                ]
            },
        )

    result = _run_with_client(
        handler,
        lambda client: client.search_entities(
            "Inception", types="urn:entity:movie", take=2, page=1
        ),
    )

    assert result == [
        QlooEntity(
            entity_id="movie-1",
            name="Inception",
            types=("urn:entity:movie",),
            popularity=0.91,
            disambiguation="2010 film",
        )
    ]


def test_search_to_insights_uses_returned_entity_id_and_separate_types() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search":
            assert request.url.params["types"] == "urn:entity:movie"
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "entity_id": "returned-movie-id",
                            "name": "Inception",
                            "types": ["urn:entity:movie"],
                        }
                    ]
                },
            )

        assert request.url.path == "/v2/insights"
        captured["filter_type"] = request.url.params["filter.type"]
        captured["entities"] = request.url.params["signal.interests.entities"]
        assert request.url.params["take"] == "3"
        return httpx.Response(
            200,
            json={
                "success": True,
                "results": {
                    "entities": [
                        {
                            "entity_id": "insight-1",
                            "name": "The Matrix",
                            "type": "urn:entity",
                            "subtype": "urn:entity:movie",
                            "popularity": 0.88,
                        }
                    ]
                },
            },
        )

    async def scenario(client: QlooClient) -> list[QlooEntity]:
        search = await client.search_entities("Inception", types=["urn:entity:movie"])
        assert len(search) == 1
        return await client.get_insights(
            filter_type="urn:entity:movie",
            entity_ids=[search[0].entity_id],
            take=3,
        )

    result = _run_with_client(handler, scenario)

    assert captured == {
        "filter_type": "urn:entity:movie",
        "entities": "returned-movie-id",
    }
    assert result[0].entity_id == "insight-1"
    assert result[0].types == ("urn:entity:movie",)
    assert result[0].subtype == "urn:entity:movie"


@pytest.mark.parametrize("filter_type", sorted(SUPPORTED_INSIGHTS_FILTER_TYPES))
def test_insights_accepts_supported_filter_types(filter_type: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/insights"
        assert request.url.params["filter.type"] == filter_type
        return httpx.Response(
            200, json={"success": True, "results": {"entities": []}}
        )

    result = _run_with_client(
        handler,
        lambda client: client.get_insights(
            filter_type=filter_type, entity_ids=["real-returned-id"]
        ),
    )

    assert result == []


@pytest.mark.parametrize(
    "filter_type",
    ["urn:entity:music", "urn:entity:food_and_drink"],
)
def test_insights_rejects_unsupported_filter_types_before_http(
    filter_type: str,
) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"success": True, "results": {"entities": []}})

    with pytest.raises(QlooValidationError, match="filter_type"):
        _run_with_client(
            handler,
            lambda client: client.get_insights(
                filter_type=filter_type, entity_ids=["real-returned-id"]
            ),
        )

    assert calls == 0


def test_search_types_are_not_restricted_by_insights_allowlist() -> None:
    search_type = "urn:entity:tv_show"
    assert search_type not in SUPPORTED_INSIGHTS_FILTER_TYPES

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search"
        assert request.url.params["types"] == search_type
        return httpx.Response(200, json={"results": []})

    result = _run_with_client(
        handler,
        lambda client: client.search_entities("The Bear", types=[search_type]),
    )

    assert result == []


def test_tag_search_uses_filter_query_parameter() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/tags"
        assert request.url.params["filter.query"] == "science fiction"
        assert request.url.params["filter.tag.types"] == "urn:tag:genre"
        assert request.url.params["take"] == "2"
        assert "query" not in request.url.params
        return httpx.Response(
            200,
            json={
                "success": True,
                "results": {
                    "tags": [
                        {
                            "id": "urn:tag:genre:media:science_fiction",
                            "name": "Science Fiction",
                            "type": "urn:tag:genre:media",
                            "popularity": 0.99,
                        }
                    ]
                },
            },
        )

    result = _run_with_client(
        handler,
        lambda client: client.search_tags(
            "science fiction", tag_types=["urn:tag:genre"], take=2
        ),
    )

    assert len(result) == 1
    assert result[0].tag_id == "urn:tag:genre:media:science_fiction"
    assert result[0].name == "Science Fiction"


def test_empty_results_are_successful_empty_lists() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search":
            return httpx.Response(200, json={"results": []})
        if request.url.path == "/v2/tags":
            return httpx.Response(200, json={"success": True, "results": {"tags": []}})
        return httpx.Response(
            200, json={"success": True, "results": {"entities": []}}
        )

    async def scenario(client: QlooClient) -> tuple[list[Any], list[Any], list[Any]]:
        search = await client.search_entities("nothing")
        tags = await client.search_tags("nothing")
        insights = await client.get_insights(
            filter_type="urn:entity:movie", entity_ids=["real-returned-id"]
        )
        return search, tags, insights

    assert _run_with_client(handler, scenario) == ([], [], [])


def test_401_raises_authentication_error_without_retry_or_key_leak() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            401,
            json={"errors": [{"message": f"invalid key {API_KEY}"}]},
        )

    with pytest.raises(QlooAuthenticationError) as caught:
        _run_with_client(
            handler, lambda client: client.search_entities("Inception")
        )

    assert calls == 1
    assert caught.value.status_code == 401
    assert caught.value.retryable is False
    assert API_KEY not in str(caught.value)
    assert API_KEY not in repr(caught.value)
    assert API_KEY not in str(caught.value.to_dict())


def test_429_retries_to_cap_then_raises_rate_limit_error() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(429, headers={"Retry-After": "0"})

    with pytest.raises(QlooRateLimitError) as caught:
        _run_with_client(
            handler,
            lambda client: client.search_entities("Inception"),
            max_retries=2,
        )

    assert calls == 3
    assert caught.value.attempts == 3
    assert caught.value.status_code == 429
    assert caught.value.retryable is True


def test_5xx_is_retried_then_succeeds() -> None:
    statuses = [500, 503, 200]
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        status = statuses[calls]
        calls += 1
        if status == 200:
            return httpx.Response(200, json={"results": []})
        return httpx.Response(status)

    result = _run_with_client(
        handler,
        lambda client: client.search_entities("Inception"),
        max_retries=2,
    )

    assert result == []
    assert calls == 3


def test_5xx_retry_cap_raises_server_error() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    with pytest.raises(QlooServerError) as caught:
        _run_with_client(
            handler,
            lambda client: client.search_entities("Inception"),
            max_retries=1,
        )

    assert calls == 2
    assert caught.value.attempts == 2
    assert caught.value.status_code == 503
    assert caught.value.retryable is True


def test_non_retryable_400_raises_request_error() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            400, json={"errors": [{"message": f"bad request {API_KEY}"}]}
        )

    with pytest.raises(QlooRequestError) as caught:
        _run_with_client(handler, lambda client: client.search_entities("x"))

    assert calls == 1
    assert caught.value.status_code == 400
    assert caught.value.retryable is False
    assert API_KEY not in str(caught.value)


def test_timeout_retries_to_cap_then_raises_timeout_error() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("simulated timeout", request=request)

    with pytest.raises(QlooTimeoutError) as caught:
        _run_with_client(
            handler,
            lambda client: client.search_entities("Inception"),
            max_retries=2,
        )

    assert calls == 3
    assert caught.value.attempts == 3
    assert caught.value.retryable is True


def test_transport_error_retries_to_cap_then_raises_network_error() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("simulated outage", request=request)

    with pytest.raises(QlooNetworkError) as caught:
        _run_with_client(
            handler,
            lambda client: client.search_entities("Inception"),
            max_retries=1,
        )

    assert calls == 2
    assert caught.value.attempts == 2
    assert caught.value.retryable is True


def test_malformed_json_raises_response_error() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"<html>not json</html>", headers={"content-type": "text/html"}
        )

    with pytest.raises(QlooResponseError, match="malformed"):
        _run_with_client(handler, lambda client: client.search_entities("Inception"))


@pytest.mark.parametrize(
    ("endpoint", "payload"),
    [
        ("/search", {"results": {"not": "a list"}}),
        ("/search", {"unexpected": []}),
        ("/v2/tags", {"success": True, "results": {}}),
        ("/v2/insights", {"success": True, "results": {}}),
        ("/v2/insights", {"success": False, "results": {"entities": []}}),
        (
            "/search",
            {"results": [{"name": "No ID", "types": ["urn:entity:movie"]}]},
        ),
    ],
)
def test_malformed_response_shapes_raise_response_error(
    endpoint: str, payload: dict[str, Any]
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async def scenario(client: QlooClient) -> None:
        if endpoint == "/search":
            await client.search_entities("Inception")
        elif endpoint == "/v2/tags":
            await client.search_tags("science fiction")
        else:
            await client.get_insights(
                filter_type="urn:entity:movie", entity_ids=["real-id"]
            )

    with pytest.raises(QlooResponseError):
        _run_with_client(handler, scenario)


def test_validation_rejects_bad_parameters_before_any_http_call() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"results": []})

    async def scenario(client: QlooClient) -> None:
        with pytest.raises(QlooValidationError):
            await client.search_entities("   ")
        with pytest.raises(QlooValidationError):
            await client.search_entities("x", types=["movie"])
        with pytest.raises(QlooValidationError):
            await client.search_entities(
                "x", types=["urn:entity:movie,urn:entity:book"]
            )
        with pytest.raises(QlooValidationError):
            await client.search_entities("x", take=0)
        with pytest.raises(QlooValidationError):
            await client.search_entities("x", take=101)
        with pytest.raises(QlooValidationError):
            await client.search_entities("x", page=0)
        with pytest.raises(QlooValidationError):
            await client.search_tags("")
        with pytest.raises(QlooValidationError):
            await client.search_tags("x", tag_types=["genre"])
        with pytest.raises(QlooValidationError):
            await client.search_tags("x", take=0)
        with pytest.raises(QlooValidationError):
            await client.get_insights(filter_type="movie", entity_ids=["real-id"])
        with pytest.raises(QlooValidationError):
            await client.get_insights(
                filter_type="urn:entity", entity_ids=["real-id"]
            )
        with pytest.raises(QlooValidationError):
            await client.get_insights(filter_type="urn:entity:movie", entity_ids=[])
        with pytest.raises(QlooValidationError):
            await client.get_insights(
                filter_type="urn:entity:movie", entity_ids=[""]
            )
        with pytest.raises(QlooValidationError):
            await client.get_insights(
                filter_type="urn:entity:movie", entity_ids=["a,b"]
            )
        with pytest.raises(QlooValidationError):
            await client.get_insights(
                filter_type="urn:entity:movie", entity_ids=["real-id"], take=0
            )

    _run_with_client(handler, scenario)
    assert calls == 0


def test_cache_hit_avoids_second_request_and_returns_independent_list() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "entity_id": f"movie-{calls}",
                        "name": "Inception",
                        "types": ["urn:entity:movie"],
                    }
                ]
            },
        )

    async def scenario(client: QlooClient) -> None:
        first = await client.search_entities("Inception")
        first.append(
            QlooEntity(entity_id="local-only", name="not from Qloo")
        )
        second = await client.search_entities("Inception")
        assert len(second) == 1
        assert second[0].entity_id == "movie-1"
        third = await client.search_entities("Inception", take=2)
        assert third[0].entity_id == "movie-2"

    _run_with_client(
        handler, scenario, cache_ttl_seconds=60, cache_max_entries=8
    )
    assert calls == 2


def test_cache_expires_after_ttl() -> None:
    calls = 0
    now = [100.0]

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"results": []})

    async def scenario(client: QlooClient) -> None:
        await client.search_entities("Inception")
        now[0] += 11.0
        await client.search_entities("Inception")

    _run_with_client(
        handler,
        scenario,
        cache_ttl_seconds=10,
        cache_max_entries=8,
        clock=lambda: now[0],
    )
    assert calls == 2


def test_client_repr_never_contains_key() -> None:
    client = _client(lambda _: httpx.Response(200, json={"results": []}))
    assert API_KEY not in repr(client)
    assert "api_key" not in repr(client).lower()
    asyncio.run(client.aclose())
