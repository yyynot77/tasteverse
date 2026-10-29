"""Tests for CORS configuration and the shared JSON error envelope."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

VALID_BODY = {
    "player_interests": {
        "movies": ["Inception"],
        "music": [],
        "food": [],
    }
}


def _assert_error_envelope(response, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "retryable"}
    assert body["error"]["code"] == code
    assert body["error"]["retryable"] is False
    assert body["error"]["message"]


@pytest.mark.parametrize(
    "origin", ["http://localhost:5173", "http://127.0.0.1:5173"]
)
def test_default_vite_origins_are_allowed(origin: str) -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-origin"] != "*"
    assert "access-control-allow-credentials" not in response.headers


def test_disallowed_origin_gets_no_cors_allow_header() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get(
            "/health", headers={"Origin": "https://not-the-vite-app.example"}
        )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_json_post_preflight_allows_vite_origin_and_json_headers() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.options(
            "/api/game/start",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_preflight_from_disallowed_origin_is_rejected() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.options(
            "/api/game/start",
            headers={
                "Origin": "https://not-the-vite-app.example",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_allow_list_comes_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "https://taste.example, https://staging.taste.example/",
    )
    app = create_app()
    with TestClient(app) as client:
        allowed = client.get(
            "/health", headers={"Origin": "https://taste.example"}
        )
        normalized = client.get(
            "/health", headers={"Origin": "https://staging.taste.example"}
        )
        default = client.get(
            "/health", headers={"Origin": "http://localhost:5173"}
        )

    assert allowed.headers["access-control-allow-origin"] == "https://taste.example"
    assert (
        normalized.headers["access-control-allow-origin"]
        == "https://staging.taste.example"
    )
    assert "access-control-allow-origin" not in default.headers


def test_cors_wildcard_is_rejected() -> None:
    with pytest.raises(ValueError, match="explicit origins"):
        create_app(["*"])


def test_empty_cors_environment_disables_cross_origin_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "")
    app = create_app()
    with TestClient(app) as client:
        response = client.get(
            "/health", headers={"Origin": "http://localhost:5173"}
        )

    assert "access-control-allow-origin" not in response.headers


def test_validation_errors_are_json_envelopes_with_cors_headers() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/game/start",
            json={"player_interests": {"movies": [], "music": [], "food": []}},
            headers={"Origin": "http://localhost:5173"},
        )

    _assert_error_envelope(response, 422, "invalid_request")
    assert (
        response.headers["access-control-allow-origin"] == "http://localhost:5173"
    )


def test_unknown_route_uses_error_envelope() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/does-not-exist")

    _assert_error_envelope(response, 404, "not_found")


def test_wrong_method_uses_error_envelope() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.post("/api/npcs", json=VALID_BODY)

    _assert_error_envelope(response, 405, "method_not_allowed")
