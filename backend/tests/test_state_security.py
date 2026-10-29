"""Focused tests for signing-key configuration and token validation."""

from __future__ import annotations

import pytest

from app.core.state_security import (
    StateConfigurationError,
    StateSecurityError,
    sign_state,
    verify_state,
)
from app.models.game import GameState, PlayerInterests


def _state() -> GameState:
    return GameState(
        player_interests=PlayerInterests(
            movies=["Inception"], music=["jazz"], food=["ramen"]
        )
    )


def test_local_development_fallback_is_stable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GAME_STATE_SECRET", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    state = _state()

    first = sign_state(state)
    second = sign_state(state)

    assert first == second
    assert first.startswith("v1.")
    verify_state(state, first)


def test_configured_secret_changes_the_token(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state()
    monkeypatch.setenv("GAME_STATE_SECRET", "a" * 32)
    first = sign_state(state)
    monkeypatch.setenv("GAME_STATE_SECRET", "b" * 32)
    second = sign_state(state)

    assert first != second
    verify_state(state, second)
    with pytest.raises(StateSecurityError):
        verify_state(state, first)


def test_production_requires_a_long_configured_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("GAME_STATE_SECRET", raising=False)

    with pytest.raises(StateConfigurationError):
        sign_state(_state())

    monkeypatch.setenv("GAME_STATE_SECRET", "short")
    with pytest.raises(StateConfigurationError):
        sign_state(_state())


@pytest.mark.parametrize("token", ["", "v1", "v2.abc", "v1.", "v1.not-base64!!"])
def test_malformed_tokens_are_rejected(token: str) -> None:
    with pytest.raises(StateSecurityError):
        verify_state(_state(), token)
