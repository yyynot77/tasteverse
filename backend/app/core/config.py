"""Environment-backed configuration for the DeepSeek agent.

Secrets are loaded from the process environment or ``backend/.env`` through
``python-dotenv``. This module never prints or serializes the API key, and the
configuration object's ``repr`` is redacted.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

DEFAULT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-flash"
DEFAULT_DEEPSEEK_TIMEOUT_SECONDS = 20.0
DEFAULT_DEEPSEEK_MAX_RETRIES = 1
DEFAULT_DEEPSEEK_MAX_TOKENS = 700
_PLACEHOLDER_KEYS = frozenset({"replace_me", "changeme", "your_api_key"})


class DeepSeekConfigurationError(ValueError):
    """Raised when DeepSeek configuration is absent or invalid.

    The message is safe to show to an operator and never contains the key.
    """

    code = "deepseek_configuration_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)


@dataclass(frozen=True, repr=False)
class DeepSeekConfig:
    """Validated DeepSeek settings.

    ``api_key`` is excluded from the generated representation by the custom
    ``__repr__`` below.
    """

    api_key: str = field(repr=False)
    base_url: str = DEFAULT_DEEPSEEK_BASE_URL
    model: str = DEFAULT_DEEPSEEK_MODEL
    timeout_seconds: float = DEFAULT_DEEPSEEK_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_DEEPSEEK_MAX_RETRIES
    max_tokens: int = DEFAULT_DEEPSEEK_MAX_TOKENS

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str) or not self.api_key.strip():
            raise DeepSeekConfigurationError(
                "DEEPSEEK_API_KEY is not configured."
            )
        if self.api_key.strip().lower() in _PLACEHOLDER_KEYS:
            raise DeepSeekConfigurationError(
                "DEEPSEEK_API_KEY is not configured."
            )

        parsed = urlsplit(self.base_url.strip().rstrip("/"))
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise DeepSeekConfigurationError(
                "DEEPSEEK_BASE_URL is not a valid HTTP(S) URL."
            )

        if not self.model.strip():
            raise DeepSeekConfigurationError("DEEPSEEK_MODEL must not be empty.")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or self.timeout_seconds <= 0
        ):
            raise DeepSeekConfigurationError(
                "DEEPSEEK_TIMEOUT_SECONDS must be positive."
            )
        if (
            isinstance(self.max_retries, bool)
            or not isinstance(self.max_retries, int)
            or self.max_retries < 0
        ):
            raise DeepSeekConfigurationError(
                "DEEPSEEK_MAX_RETRIES must be a non-negative integer."
            )
        if (
            isinstance(self.max_tokens, bool)
            or not isinstance(self.max_tokens, int)
            or self.max_tokens < 1
        ):
            raise DeepSeekConfigurationError(
                "DEEPSEEK_MAX_TOKENS must be a positive integer."
            )

    def __repr__(self) -> str:
        return (
            "DeepSeekConfig("
            f"base_url={self.base_url!r}, model={self.model!r}, "
            f"timeout_seconds={self.timeout_seconds!r}, "
            f"max_retries={self.max_retries!r}, api_key=<redacted>)"
        )

    @classmethod
    def from_env(
        cls, *, env_file: str | Path | None = None
    ) -> "DeepSeekConfig":
        """Load settings from process environment or the local dotenv file."""

        dotenv_path = Path(env_file) if env_file is not None else DEFAULT_ENV_FILE
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path, override=False)

        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        base_url = os.environ.get(
            "DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL
        ).strip()
        model = os.environ.get("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL).strip()

        timeout_raw = os.environ.get(
            "DEEPSEEK_TIMEOUT_SECONDS", str(DEFAULT_DEEPSEEK_TIMEOUT_SECONDS)
        )
        retries_raw = os.environ.get(
            "DEEPSEEK_MAX_RETRIES", str(DEFAULT_DEEPSEEK_MAX_RETRIES)
        )
        max_tokens_raw = os.environ.get(
            "DEEPSEEK_MAX_TOKENS", str(DEFAULT_DEEPSEEK_MAX_TOKENS)
        )

        try:
            timeout_seconds = float(timeout_raw)
        except (TypeError, ValueError) as exc:
            raise DeepSeekConfigurationError(
                "DEEPSEEK_TIMEOUT_SECONDS must be a number."
            ) from exc
        try:
            max_retries = int(retries_raw)
        except (TypeError, ValueError) as exc:
            raise DeepSeekConfigurationError(
                "DEEPSEEK_MAX_RETRIES must be an integer."
            ) from exc
        try:
            max_tokens = int(max_tokens_raw)
        except (TypeError, ValueError) as exc:
            raise DeepSeekConfigurationError(
                "DEEPSEEK_MAX_TOKENS must be an integer."
            ) from exc

        return cls(
            api_key=api_key.strip(),
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            max_tokens=max_tokens,
        )


__all__ = [
    "DEFAULT_DEEPSEEK_BASE_URL",
    "DEFAULT_DEEPSEEK_MAX_RETRIES",
    "DEFAULT_DEEPSEEK_MAX_TOKENS",
    "DEFAULT_DEEPSEEK_MODEL",
    "DEFAULT_DEEPSEEK_TIMEOUT_SECONDS",
    "DEFAULT_ENV_FILE",
    "DeepSeekConfig",
    "DeepSeekConfigurationError",
]
