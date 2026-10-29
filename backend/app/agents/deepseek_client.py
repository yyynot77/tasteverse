"""Small, bounded async client for the DeepSeek chat-completions API.

Only the subset needed by the dialogue agent is implemented:

* ``POST /chat/completions`` with model, messages, tools, and token limits;
* strict parsing of the assistant ``tool_calls`` envelope;
* bounded retries for transient failures (timeouts, transport errors, 429,
  and 5xx), with no retries for authentication/validation failures.

Upstream response bodies are never included in raised error messages, so a
provider error cannot leak credentials or raw content into API responses or
logs.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import DeepSeekConfig

_MAX_RESPONSE_BYTES = 1_000_000
_MAX_RETRY_AFTER_SECONDS = 5.0
_MAX_TOOL_CALLS_PER_MESSAGE = 8
_MAX_TOOL_NAME_LENGTH = 80
_MAX_TOOL_ID_LENGTH = 200

Sleep = Callable[[float], Awaitable[None]]


class DeepSeekError(Exception):
    """Base class for safe, typed DeepSeek failures."""

    code = "deepseek_error"
    status_code = 502
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        retryable: bool | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        if retryable is not None:
            self.retryable = retryable
        if status_code is not None:
            self.status_code = status_code


class DeepSeekAuthenticationError(DeepSeekError):
    code = "deepseek_authentication_error"
    status_code = 502


class DeepSeekRateLimitError(DeepSeekError):
    code = "deepseek_rate_limited"
    status_code = 503
    retryable = True


class DeepSeekTimeoutError(DeepSeekError):
    code = "deepseek_timeout"
    status_code = 504
    retryable = True


class DeepSeekNetworkError(DeepSeekError):
    code = "deepseek_network_error"
    status_code = 502
    retryable = True


class DeepSeekServerError(DeepSeekError):
    code = "deepseek_server_error"
    status_code = 502
    retryable = True


class DeepSeekRequestError(DeepSeekError):
    code = "deepseek_request_error"
    status_code = 502


class DeepSeekResponseError(DeepSeekError):
    code = "deepseek_response_error"
    status_code = 502
    retryable = True


@dataclass(frozen=True, slots=True)
class ToolCall:
    """One normalized function call requested by the model."""

    call_id: str
    name: str
    arguments: str


@dataclass(frozen=True, slots=True)
class AssistantMessage:
    """Parsed assistant message from one completion."""

    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str | None = None


class DeepSeekClient:
    """Async DeepSeek transport with bounded retries and strict parsing."""

    def __init__(
        self,
        config: DeepSeekConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        client: httpx.AsyncClient | None = None,
        sleep: Sleep | None = None,
    ) -> None:
        if client is not None and transport is not None:
            raise ValueError("Pass either client or transport, not both.")

        self._config = config
        self._sleep = sleep or asyncio.sleep
        self._owns_http = client is None
        self._closed = False

        if client is None:
            self._http = httpx.AsyncClient(
                timeout=config.timeout_seconds,
                transport=transport,
                follow_redirects=False,
            )
        else:
            self._http = client

    @property
    def config(self) -> DeepSeekConfig:
        return self._config

    def __repr__(self) -> str:
        return (
            "DeepSeekClient("
            f"base_url={self._config.base_url!r}, "
            f"model={self._config.model!r}, api_key=<redacted>)"
        )

    async def __aenter__(self) -> "DeepSeekClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_http and not self._closed:
            await self._http.aclose()
            self._closed = True

    async def chat(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        tools: Sequence[Mapping[str, Any]] | None = None,
        tool_choice: str | None = None,
        max_tokens: int | None = None,
    ) -> AssistantMessage:
        """Request one completion and return a validated assistant message."""

        if not messages:
            raise DeepSeekRequestError("At least one message is required.")
        if max_tokens is not None and (
            isinstance(max_tokens, bool)
            or not isinstance(max_tokens, int)
            or max_tokens < 1
            or max_tokens > 8_192
        ):
            raise DeepSeekRequestError("max_tokens must be between 1 and 8192.")

        body: dict[str, Any] = {
            "model": self._config.model,
            "messages": list(messages),
            "max_tokens": max_tokens or self._config.max_tokens,
            "temperature": 0.2,
            "stream": False,
        }
        if tools:
            body["tools"] = list(tools)
            body["tool_choice"] = tool_choice or "auto"

        payload = await self._request_json("/chat/completions", body)
        return self._parse_completion(payload)

    async def _request_json(
        self, path: str, body: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        url = f"{self._config.base_url.rstrip('/')}{path}"
        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "TasteVerse-DeepSeekClient/1.0",
        }
        attempts_allowed = self._config.max_retries + 1

        for attempt in range(attempts_allowed):
            try:
                response = await self._http.post(url, json=body, headers=headers)
            except httpx.TimeoutException:
                if attempt < self._config.max_retries:
                    await self._sleep(self._backoff(attempt))
                    continue
                raise DeepSeekTimeoutError(
                    "DeepSeek request timed out after "
                    f"{attempts_allowed} attempt(s)."
                ) from None
            except httpx.TransportError:
                if attempt < self._config.max_retries:
                    await self._sleep(self._backoff(attempt))
                    continue
                raise DeepSeekNetworkError(
                    "DeepSeek network request failed after "
                    f"{attempts_allowed} attempt(s)."
                ) from None

            status = response.status_code
            if status == 429:
                if attempt < self._config.max_retries:
                    await self._sleep(self._retry_delay(response, attempt))
                    continue
                raise DeepSeekRateLimitError(
                    "DeepSeek rate limit remained after "
                    f"{attempts_allowed} attempt(s)."
                )

            if 500 <= status <= 599:
                if attempt < self._config.max_retries:
                    await self._sleep(self._retry_delay(response, attempt))
                    continue
                raise DeepSeekServerError(
                    "DeepSeek service was unavailable after "
                    f"{attempts_allowed} attempt(s)."
                )

            if status in {401, 403}:
                raise DeepSeekAuthenticationError(
                    "DeepSeek authentication failed."
                )

            if status >= 400:
                raise DeepSeekRequestError("DeepSeek rejected the request.")

            if status >= 300:
                raise DeepSeekRequestError(
                    "DeepSeek returned an unexpected redirect."
                )

            if len(response.content) > _MAX_RESPONSE_BYTES:
                raise DeepSeekResponseError(
                    "DeepSeek returned an oversized response."
                )

            try:
                payload = response.json()
            except ValueError:
                raise DeepSeekResponseError(
                    "DeepSeek returned malformed JSON."
                ) from None
            if not isinstance(payload, dict):
                raise DeepSeekResponseError(
                    "DeepSeek returned a malformed response."
                )
            return payload

        raise DeepSeekServerError("DeepSeek request failed.")

    def _backoff(self, attempt: int) -> float:
        # Attempts are capped at a small number; this remains under five
        # seconds so a dialogue request cannot stall for long.
        return min(0.25 * (2**attempt), _MAX_RETRY_AFTER_SECONDS)

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after is not None:
            try:
                delay = float(retry_after.strip())
            except ValueError:
                delay = None
            if delay is not None:
                return min(max(delay, 0.0), _MAX_RETRY_AFTER_SECONDS)
        return self._backoff(attempt)

    @staticmethod
    def _parse_completion(payload: Mapping[str, Any]) -> AssistantMessage:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise DeepSeekResponseError(
                "DeepSeek response did not contain a completion."
            )
        choice = choices[0]
        if not isinstance(choice, dict):
            raise DeepSeekResponseError(
                "DeepSeek returned a malformed choice."
            )
        message = choice.get("message")
        if not isinstance(message, dict):
            raise DeepSeekResponseError(
                "DeepSeek returned a malformed assistant message."
            )

        content = message.get("content")
        if content is None:
            normalized_content = ""
        elif isinstance(content, str):
            normalized_content = content
        else:
            raise DeepSeekResponseError(
                "DeepSeek returned unsupported message content."
            )

        raw_calls = message.get("tool_calls")
        if raw_calls is None:
            normalized_calls: list[ToolCall] = []
        elif isinstance(raw_calls, list):
            if len(raw_calls) > _MAX_TOOL_CALLS_PER_MESSAGE:
                raise DeepSeekResponseError(
                    "DeepSeek returned too many tool calls in one turn."
                )
            normalized_calls = [
                DeepSeekClient._parse_tool_call(item) for item in raw_calls
            ]
        else:
            raise DeepSeekResponseError(
                "DeepSeek returned malformed tool calls."
            )

        finish_reason = choice.get("finish_reason")
        if finish_reason is not None and not isinstance(finish_reason, str):
            finish_reason = None

        return AssistantMessage(
            content=normalized_content,
            tool_calls=tuple(normalized_calls),
            finish_reason=finish_reason,
        )

    @staticmethod
    def _parse_tool_call(raw: Any) -> ToolCall:
        if not isinstance(raw, dict):
            raise DeepSeekResponseError(
                "DeepSeek returned a malformed tool call."
            )
        call_id = raw.get("id")
        if (
            not isinstance(call_id, str)
            or not call_id.strip()
            or len(call_id) > _MAX_TOOL_ID_LENGTH
        ):
            raise DeepSeekResponseError(
                "DeepSeek returned a tool call without a valid ID."
            )
        if raw.get("type") != "function":
            raise DeepSeekResponseError(
                "DeepSeek returned a non-function tool call."
            )
        function = raw.get("function")
        if not isinstance(function, dict):
            raise DeepSeekResponseError(
                "DeepSeek returned a tool call without a function."
            )
        name = function.get("name")
        if (
            not isinstance(name, str)
            or not name.strip()
            or len(name) > _MAX_TOOL_NAME_LENGTH
        ):
            raise DeepSeekResponseError(
                "DeepSeek returned a tool call without a valid name."
            )
        arguments = function.get("arguments")
        if not isinstance(arguments, str):
            raise DeepSeekResponseError(
                "DeepSeek returned non-string tool arguments."
            )
        if len(arguments) > 8_000:
            raise DeepSeekResponseError(
                "DeepSeek returned oversized tool arguments."
            )
        return ToolCall(
            call_id=call_id.strip(),
            name=name.strip(),
            arguments=arguments,
        )


__all__ = [
    "AssistantMessage",
    "DeepSeekAuthenticationError",
    "DeepSeekClient",
    "DeepSeekError",
    "DeepSeekNetworkError",
    "DeepSeekRateLimitError",
    "DeepSeekRequestError",
    "DeepSeekResponseError",
    "DeepSeekServerError",
    "DeepSeekTimeoutError",
    "ToolCall",
]
