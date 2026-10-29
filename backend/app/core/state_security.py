"""Server-signed envelopes for client-carried game state.

The client may persist a state between requests (for example in
``localStorage``), but it must not be able to change computed fields such as
relationships, stage, clues, score, or ending. Every mutating route therefore
requires a token signed by the server with an HMAC-SHA256 key.

The signed message covers the full serialized state plus a schema version, the
session ID, and the monotonic ``state_version``. Any change to any field
invalidates the token before game rules or providers run. The token contains
only a version prefix and a digest; it never contains the secret.

Deployments must set ``GAME_STATE_SECRET`` (at least 32 characters). When the
environment is not marked as production, a fixed local-development key is used
so a developer can restart the API without losing a saved game. That fallback
is deliberately rejected when ``APP_ENV`` or ``ENVIRONMENT`` is ``production``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os

from app.models.game import GameState

TOKEN_PREFIX = "v1"
TOKEN_CONTEXT = b"tasteverse-game-state-v1"
TOKEN_SCHEMA_VERSION = 1
MIN_SECRET_LENGTH = 32
MAX_TOKEN_LENGTH = 200

_LOCAL_DEVELOPMENT_SECRET = (
    b"tasteverse-local-development-state-key-do-not-use-in-production"
)
_PRODUCTION_ENVIRONMENTS = frozenset({"production", "prod"})


class StateSecurityError(ValueError):
    """Raised when a state token is missing, malformed, or does not match."""

    code = "state_integrity_error"


class StateConfigurationError(ValueError):
    """Raised when no safe signing key is configured for production."""

    code = "state_configuration_error"


def _is_production() -> bool:
    environment = (
        os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or ""
    ).strip().lower()
    return environment in _PRODUCTION_ENVIRONMENTS


def _secret() -> bytes:
    configured = os.getenv("GAME_STATE_SECRET", "").strip()
    if configured:
        if len(configured) < MIN_SECRET_LENGTH:
            raise StateConfigurationError(
                "GAME_STATE_SECRET must be at least "
                f"{MIN_SECRET_LENGTH} characters."
            )
        return configured.encode("utf-8")
    if _is_production():
        raise StateConfigurationError(
            "GAME_STATE_SECRET must be configured in production."
        )
    return _LOCAL_DEVELOPMENT_SECRET


def _canonical_message(state: GameState) -> bytes:
    """Serialize every state field in a stable, unambiguous order."""

    state_payload = state.model_dump(mode="json")
    envelope = {
        "schema": TOKEN_SCHEMA_VERSION,
        "session_id": state_payload["session_id"],
        "state_version": state_payload["state_version"],
        "state": state_payload,
    }
    rendered = json.dumps(
        envelope,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return TOKEN_CONTEXT + b"\n" + rendered


def sign_state(state: GameState) -> str:
    """Return a URL-safe token binding this exact state to the server key."""

    digest = hmac.new(
        _secret(), _canonical_message(state), hashlib.sha256
    ).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{TOKEN_PREFIX}.{encoded}"


def verify_state(state: GameState, token: str) -> None:
    """Reject a missing or forged token before any state mutation.

    ``hmac.compare_digest`` is used so a caller cannot learn the expected token
    through timing differences.
    """

    if not isinstance(token, str):
        raise StateSecurityError("Game state token is missing or invalid.")
    token = token.strip()
    if not token or len(token) > MAX_TOKEN_LENGTH:
        raise StateSecurityError("Game state token is missing or invalid.")
    prefix, separator, _ = token.partition(".")
    if separator != "." or prefix != TOKEN_PREFIX:
        raise StateSecurityError("Game state token is missing or invalid.")
    expected = sign_state(state)
    if not hmac.compare_digest(expected, token):
        raise StateSecurityError(
            "Game state could not be verified; start or resume a valid session."
        )


__all__ = [
    "MAX_TOKEN_LENGTH",
    "MIN_SECRET_LENGTH",
    "TOKEN_PREFIX",
    "TOKEN_SCHEMA_VERSION",
    "StateConfigurationError",
    "StateSecurityError",
    "sign_state",
    "verify_state",
]
