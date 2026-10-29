"""Async, typed client for the Qloo Hackathon API.

The client is intentionally small and framework-free so it can be reused by the
FastAPI application, scripts, and tests. It keeps the API key private, validates
inputs before making a request, retries only transient failures, and caches
successful normalized results in process memory.

Qloo endpoints used (verified against the live hackathon API):

* ``GET /search`` with ``query``, ``types``, ``take``, and ``page``.
* ``GET /v2/tags`` with ``filter.query``, ``filter.tag.types``, and ``take``.
* ``GET /v2/insights`` with ``filter.type``, ``signal.interests.entities``, and
  ``take``.

Search ``types`` and insights ``filter.type`` are deliberately separate: a
search type describes the entities being searched, while an insights filter
type describes the entity type of the returned recommendations.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv

DEFAULT_BASE_URL = "https://hackathon.api.qloo.com"
DEFAULT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Search accepts a broad entity-type URN pattern and validates it separately
# from the Insights filter allowlist below. Do not reuse one for the other.
_SEARCH_ENTITY_TYPE_RE = re.compile(r"^urn:entity:[a-z][a-z0-9_]*$")

# Explicit allowlist for the live ``GET /v2/insights`` ``filter.type``
# parameter. Unsupported URNs such as ``urn:entity:music`` and
# ``urn:entity:food_and_drink`` are rejected before any HTTP request.
SUPPORTED_INSIGHTS_FILTER_TYPES = frozenset(
    {
        "urn:entity:movie",
        "urn:entity:artist",
        "urn:entity:book",
        "urn:entity:place",
        "urn:entity:brand",
        "urn:entity:destination",
    }
)
_INSIGHTS_FILTER_TYPES_MESSAGE = ", ".join(
    sorted(SUPPORTED_INSIGHTS_FILTER_TYPES)
)
_TAG_TYPE_RE = re.compile(r"^urn:tag:[a-z0-9_:]+$")
_PLACEHOLDER_KEYS = frozenset({"replace_me", "changeme", "your_api_key"})
_MAX_TEXT_LENGTH = 256
_MAX_TAKE = 100
_MAX_ENTITY_IDS = 50
_MAX_RETRY_AFTER_SECONDS = 5.0

T = TypeVar("T")


class QlooError(Exception):
    """Base class for every error raised by this module."""

    code = "qloo_error"

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
        attempts: int = 0,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status_code = status_code
        self.attempts = attempts

    def to_dict(self) -> dict[str, Any]:
        """Return a safe representation suitable for an API error envelope."""

        return {
            "code": self.code,
            "message": str(self),
            "retryable": self.retryable,
        }


class QlooConfigurationError(QlooError):
    """Raised when Qloo credentials or configuration are missing/invalid."""

    code = "qloo_configuration_error"


class QlooValidationError(QlooError):
    """Raised before a request when caller input is invalid."""

    code = "qloo_validation_error"


class QlooAuthenticationError(QlooError):
    """Raised for HTTP 401/403 responses."""

    code = "qloo_authentication_error"


class QlooRateLimitError(QlooError):
    """Raised after the bounded retry budget for HTTP 429 is exhausted."""

    code = "qloo_rate_limit_error"


class QlooServerError(QlooError):
    """Raised after the bounded retry budget for Qloo 5xx responses."""

    code = "qloo_server_error"


class QlooTimeoutError(QlooError):
    """Raised after the bounded retry budget for request timeouts."""

    code = "qloo_timeout_error"


class QlooNetworkError(QlooError):
    """Raised after the bounded retry budget for transport failures."""

    code = "qloo_network_error"


class QlooRequestError(QlooError):
    """Raised for non-retryable 4xx responses."""

    code = "qloo_request_error"


class QlooResponseError(QlooError):
    """Raised when Qloo returns JSON that does not match the expected shape."""

    code = "qloo_response_error"


@dataclass(frozen=True, slots=True)
class QlooEntity:
    """A normalized entity returned by search or insights."""

    entity_id: str
    name: str
    types: tuple[str, ...] = ()
    subtype: str | None = None
    popularity: float | None = None
    disambiguation: str | None = None


@dataclass(frozen=True, slots=True)
class QlooTag:
    """A normalized tag returned by the optional tag endpoint."""

    tag_id: str
    name: str
    type: str | None = None
    popularity: float | None = None


@dataclass(slots=True)
class _CacheEntry:
    expires_at: float
    values: tuple[Any, ...]


def _normalise_base_url(value: str) -> str:
    if not isinstance(value, str):
        raise QlooConfigurationError("QLOO_BASE_URL must be a string.")
    candidate = value.strip().rstrip("/")
    parsed = urlsplit(candidate)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise QlooConfigurationError("QLOO_BASE_URL is not a valid HTTP(S) URL.")
    return candidate


def _normalise_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise QlooValidationError(f"{field} must be a string.")
    text = value.strip()
    if not text:
        raise QlooValidationError(f"{field} must not be empty.")
    if len(text) > _MAX_TEXT_LENGTH:
        raise QlooValidationError(
            f"{field} must be at most {_MAX_TEXT_LENGTH} characters."
        )
    return text


def _normalise_type_list(
    values: str | Sequence[str] | None,
    *,
    field: str,
    pattern: re.Pattern[str],
) -> list[str] | None:
    if values is None:
        return None
    if isinstance(values, str):
        items: list[Any] = values.split(",")
    elif isinstance(values, Sequence):
        items = list(values)
    else:
        raise QlooValidationError(f"{field} must be a string or sequence of strings.")

    normalised: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise QlooValidationError(f"{field} entries must be strings.")
        value = item.strip()
        if not pattern.fullmatch(value):
            raise QlooValidationError(f"{field} contains an unsupported value.")
        if value not in normalised:
            normalised.append(value)
    if not normalised:
        raise QlooValidationError(f"{field} must not be empty.")
    return normalised


def _normalise_entity_ids(values: str | Sequence[str]) -> list[str]:
    if isinstance(values, str):
        items: list[Any] = values.split(",")
    elif isinstance(values, Sequence):
        items = list(values)
    else:
        raise QlooValidationError("entity_ids must be a string or sequence of strings.")

    entity_ids: list[str] = []
    for item in items:
        if not isinstance(item, str):
            raise QlooValidationError("entity_ids entries must be strings.")
        entity_id = item.strip()
        if not entity_id:
            raise QlooValidationError("entity_ids must not contain empty values.")
        if "," in entity_id or len(entity_id) > _MAX_TEXT_LENGTH:
            raise QlooValidationError("entity_ids contains an invalid value.")
        if entity_id not in entity_ids:
            entity_ids.append(entity_id)
    if not entity_ids:
        raise QlooValidationError("entity_ids must contain at least one value.")
    if len(entity_ids) > _MAX_ENTITY_IDS:
        raise QlooValidationError(
            f"entity_ids must contain at most {_MAX_ENTITY_IDS} values."
        )
    return entity_ids


def _normalise_take(value: int | None, *, field: str = "take") -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise QlooValidationError(f"{field} must be an integer.")
    if value < 1 or value > _MAX_TAKE:
        raise QlooValidationError(f"{field} must be between 1 and {_MAX_TAKE}.")
    return value


def _normalise_page(value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise QlooValidationError("page must be an integer.")
    if value < 1:
        raise QlooValidationError("page must be at least 1.")
    return value


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _normalise_entity(payload: Any) -> QlooEntity:
    if not isinstance(payload, dict):
        raise QlooResponseError("Qloo returned a malformed entity.")

    entity_id = payload.get("entity_id") or payload.get("id")
    if not isinstance(entity_id, str) or not entity_id.strip():
        raise QlooResponseError("Qloo returned an entity without an ID.")

    name = payload.get("name")
    if not isinstance(name, str):
        name = ""

    raw_types: list[Any] = []
    declared_types = payload.get("types")
    if isinstance(declared_types, list):
        raw_types.extend(declared_types)
    subtype = payload.get("subtype")
    if isinstance(subtype, str):
        raw_types.append(subtype)
    declared_type = payload.get("type")
    if isinstance(declared_type, str) and declared_type != "urn:entity":
        raw_types.append(declared_type)

    seen: list[str] = []
    for item in raw_types:
        if isinstance(item, str) and item and item not in seen:
            seen.append(item)

    disambiguation = payload.get("disambiguation")
    if not isinstance(disambiguation, str):
        disambiguation = None

    return QlooEntity(
        entity_id=entity_id.strip(),
        name=name,
        types=tuple(seen),
        subtype=subtype if isinstance(subtype, str) else None,
        popularity=_optional_float(payload.get("popularity")),
        disambiguation=disambiguation,
    )


def _normalise_tag(payload: Any) -> QlooTag:
    if not isinstance(payload, dict):
        raise QlooResponseError("Qloo returned a malformed tag.")

    tag_id = payload.get("id") or payload.get("tag_id")
    if not isinstance(tag_id, str) or not tag_id.strip():
        raise QlooResponseError("Qloo returned a tag without an ID.")

    name = payload.get("name")
    if not isinstance(name, str):
        name = ""
    tag_type = payload.get("type")
    if not isinstance(tag_type, str):
        tag_type = None

    return QlooTag(
        tag_id=tag_id.strip(),
        name=name,
        type=tag_type,
        popularity=_optional_float(payload.get("popularity")),
    )


class QlooClient:
    """Small async client for Qloo search, tags, and insights.

    The instance owns an ``httpx.AsyncClient`` unless one is injected. It can be
    used directly with ``await`` and as an async context manager.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
        max_retries: int = 2,
        backoff_seconds: float = 0.25,
        cache_ttl_seconds: float = 300.0,
        cache_max_entries: int = 256,
        transport: httpx.AsyncBaseTransport | None = None,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise QlooConfigurationError("QLOO_API_KEY is not configured.")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise QlooConfigurationError("timeout must be a positive number.")
        if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 0:
            raise QlooConfigurationError("max_retries must be a non-negative integer.")
        if backoff_seconds < 0:
            raise QlooConfigurationError("backoff_seconds must not be negative.")
        if cache_ttl_seconds < 0:
            raise QlooConfigurationError("cache_ttl_seconds must not be negative.")
        if (
            isinstance(cache_max_entries, bool)
            or not isinstance(cache_max_entries, int)
            or cache_max_entries < 0
        ):
            raise QlooConfigurationError("cache_max_entries must not be negative.")
        if client is not None and transport is not None:
            raise QlooConfigurationError("Pass either client or transport, not both.")

        self._api_key = api_key.strip()
        self._base_url = _normalise_base_url(base_url)
        self._timeout = float(timeout)
        self._max_retries = max_retries
        self._backoff_seconds = float(backoff_seconds)
        self._cache_ttl_seconds = float(cache_ttl_seconds)
        self._cache_max_entries = cache_max_entries
        self._sleep = sleep or asyncio.sleep
        self._clock = clock or time.monotonic
        self._cache: OrderedDict[
            tuple[str, tuple[tuple[str, str], ...]], _CacheEntry
        ] = OrderedDict()
        self._owns_http = client is None
        self._closed = False
        self._headers = {
            "X-Api-Key": self._api_key,
            "Accept": "application/json",
            "User-Agent": "TasteVerse-QlooClient/1.0",
        }

        if client is None:
            self._http = httpx.AsyncClient(
                timeout=self._timeout,
                transport=transport,
                follow_redirects=False,
            )
        else:
            self._http = client

    @property
    def base_url(self) -> str:
        """The configured base URL (never includes credentials)."""

        return self._base_url

    @property
    def cache_size(self) -> int:
        """Number of unexpired, cached result sets."""

        self._purge_expired()
        return len(self._cache)

    def __repr__(self) -> str:
        return (
            f"QlooClient(base_url={self._base_url!r}, timeout={self._timeout!r}, "
            f"max_retries={self._max_retries!r})"
        )

    @classmethod
    def from_env(
        cls,
        *,
        env_file: str | Path | None = None,
        **client_kwargs: Any,
    ) -> "QlooClient":
        """Build a client from process environment or ``backend/.env``.

        Process environment values take precedence over the dotenv file.
        ``client_kwargs`` are forwarded to the constructor (for example a
        transport in tests).
        """

        dotenv_path = Path(env_file) if env_file is not None else DEFAULT_ENV_FILE
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path, override=False)

        api_key = os.environ.get("QLOO_API_KEY", "").strip()
        if not api_key or api_key.lower() in _PLACEHOLDER_KEYS:
            raise QlooConfigurationError("QLOO_API_KEY is not configured.")

        base_url = os.environ.get("QLOO_BASE_URL", DEFAULT_BASE_URL)
        return cls(api_key=api_key, base_url=base_url, **client_kwargs)

    async def __aenter__(self) -> "QlooClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the owned HTTP client. Injected clients are left untouched."""

        if self._owns_http and not self._closed:
            await self._http.aclose()
            self._closed = True

    async def search_entities(
        self,
        query: str,
        *,
        types: str | Sequence[str] | None = None,
        take: int | None = None,
        page: int | None = None,
    ) -> list[QlooEntity]:
        """Search Qloo entities with ``GET /search``.

        ``types`` must be explicit entity URNs such as
        ``urn:entity:movie``. It is not an insights filter type.
        """

        normalised_query = _normalise_text(query, field="query")
        normalised_types = _normalise_type_list(
            types, field="types", pattern=_SEARCH_ENTITY_TYPE_RE
        )
        normalised_take = _normalise_take(take)
        normalised_page = _normalise_page(page)

        params: dict[str, Any] = {"query": normalised_query}
        if normalised_types:
            params["types"] = ",".join(normalised_types)
        if normalised_take is not None:
            params["take"] = normalised_take
        if normalised_page is not None:
            params["page"] = normalised_page

        return await self._cached_results(
            "search",
            "/search",
            params,
            self._parse_search_results,
        )

    async def search_tags(
        self,
        query: str,
        *,
        tag_types: str | Sequence[str] | None = None,
        take: int | None = None,
    ) -> list[QlooTag]:
        """Search Qloo tags with ``GET /v2/tags``.

        The live endpoint expects the text query as ``filter.query`` (not the
        plain ``query`` parameter used by entity search).
        """

        normalised_query = _normalise_text(query, field="query")
        normalised_types = _normalise_type_list(
            tag_types, field="tag_types", pattern=_TAG_TYPE_RE
        )
        normalised_take = _normalise_take(take)

        params: dict[str, Any] = {"filter.query": normalised_query}
        if normalised_types:
            params["filter.tag.types"] = ",".join(normalised_types)
        if normalised_take is not None:
            params["take"] = normalised_take

        return await self._cached_results(
            "tags",
            "/v2/tags",
            params,
            self._parse_tag_results,
        )

    async def get_insights(
        self,
        *,
        filter_type: str,
        entity_ids: str | Sequence[str],
        take: int | None = None,
    ) -> list[QlooEntity]:
        """Fetch recommendations with ``GET /v2/insights``.

        ``filter_type`` is the explicit insights type such as
        ``urn:entity:movie``. ``entity_ids`` must be real IDs returned by an
        earlier search; this method never derives or invents one.
        """

        if not isinstance(filter_type, str):
            raise QlooValidationError("filter_type must be a string.")
        normalised_filter_type = filter_type.strip()
        if normalised_filter_type not in SUPPORTED_INSIGHTS_FILTER_TYPES:
            raise QlooValidationError(
                "filter_type must be one of the supported Qloo insights types: "
                f"{_INSIGHTS_FILTER_TYPES_MESSAGE}."
            )
        normalised_ids = _normalise_entity_ids(entity_ids)
        normalised_take = _normalise_take(take)

        params: dict[str, Any] = {
            "filter.type": normalised_filter_type,
            "signal.interests.entities": ",".join(normalised_ids),
        }
        if normalised_take is not None:
            params["take"] = normalised_take

        return await self._cached_results(
            "insights",
            "/v2/insights",
            params,
            self._parse_insight_results,
        )

    async def _cached_results(
        self,
        endpoint: str,
        path: str,
        params: dict[str, Any],
        parser: Callable[[Any], list[T]],
    ) -> list[T]:
        key = (
            endpoint,
            tuple(sorted((name, str(value)) for name, value in params.items())),
        )
        cached = self._cache_get(key)
        if cached is not None:
            return list(cached)

        payload = await self._request_json(path, params)
        values = tuple(parser(payload))
        self._cache_put(key, values)
        return list(values)

    def _cache_get(
        self, key: tuple[str, tuple[tuple[str, str], ...]]
    ) -> tuple[Any, ...] | None:
        if self._cache_ttl_seconds == 0 or self._cache_max_entries == 0:
            return None
        self._purge_expired()
        entry = self._cache.get(key)
        if entry is None:
            return None
        self._cache.move_to_end(key)
        return entry.values

    def _cache_put(
        self,
        key: tuple[str, tuple[tuple[str, str], ...]],
        values: tuple[Any, ...],
    ) -> None:
        if self._cache_ttl_seconds == 0 or self._cache_max_entries == 0:
            return
        self._cache[key] = _CacheEntry(
            expires_at=self._clock() + self._cache_ttl_seconds,
            values=values,
        )
        self._cache.move_to_end(key)
        while len(self._cache) > self._cache_max_entries:
            self._cache.popitem(last=False)

    def _purge_expired(self) -> None:
        now = self._clock()
        expired = [
            key for key, entry in self._cache.items() if entry.expires_at <= now
        ]
        for key in expired:
            del self._cache[key]

    async def _request_json(self, path: str, params: dict[str, Any]) -> Any:
        url = f"{self._base_url}{path}"
        attempts_allowed = self._max_retries + 1

        for attempt in range(attempts_allowed):
            try:
                response = await self._http.get(
                    url, params=params, headers=self._headers
                )
            except httpx.TimeoutException:
                if attempt < self._max_retries:
                    await self._sleep(self._backoff(attempt))
                    continue
                raise QlooTimeoutError(
                    "Qloo request timed out after "
                    f"{attempts_allowed} attempt(s).",
                    retryable=True,
                    attempts=attempts_allowed,
                ) from None
            except httpx.TransportError:
                if attempt < self._max_retries:
                    await self._sleep(self._backoff(attempt))
                    continue
                raise QlooNetworkError(
                    "Qloo network request failed after "
                    f"{attempts_allowed} attempt(s).",
                    retryable=True,
                    attempts=attempts_allowed,
                ) from None

            status = response.status_code

            if status == 429:
                if attempt < self._max_retries:
                    await self._sleep(self._retry_delay(response, attempt))
                    continue
                raise QlooRateLimitError(
                    "Qloo rate limit was not resolved after "
                    f"{attempts_allowed} attempt(s).",
                    retryable=True,
                    status_code=status,
                    attempts=attempts_allowed,
                )

            if 500 <= status <= 599:
                if attempt < self._max_retries:
                    await self._sleep(self._retry_delay(response, attempt))
                    continue
                raise QlooServerError(
                    f"Qloo service error (HTTP {status}) after "
                    f"{attempts_allowed} attempt(s).",
                    retryable=True,
                    status_code=status,
                    attempts=attempts_allowed,
                )

            if status in {401, 403}:
                raise QlooAuthenticationError(
                    f"Qloo authentication failed (HTTP {status}).",
                    status_code=status,
                    attempts=attempt + 1,
                )

            if status >= 400:
                raise QlooRequestError(
                    f"Qloo rejected the request (HTTP {status}).",
                    status_code=status,
                    attempts=attempt + 1,
                )

            if status >= 300:
                raise QlooRequestError(
                    f"Qloo returned an unexpected redirect (HTTP {status}).",
                    status_code=status,
                    attempts=attempt + 1,
                )

            try:
                payload = response.json()
            except ValueError:
                raise QlooResponseError(
                    "Qloo returned a malformed response.",
                    status_code=status,
                    attempts=attempt + 1,
                ) from None

            if not isinstance(payload, dict):
                raise QlooResponseError(
                    "Qloo returned a malformed response.",
                    status_code=status,
                    attempts=attempt + 1,
                )
            return payload

        # The loop always returns or raises; this is defensive for type checkers.
        raise QlooServerError("Qloo request failed.", attempts=attempts_allowed)

    def _backoff(self, attempt: int) -> float:
        return min(self._backoff_seconds * (2**attempt), _MAX_RETRY_AFTER_SECONDS)

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
    def _parse_search_results(payload: Any) -> list[QlooEntity]:
        if not isinstance(payload, dict) or not isinstance(
            payload.get("results"), list
        ):
            raise QlooResponseError("Qloo search response was malformed.")
        return [_normalise_entity(item) for item in payload["results"]]

    @staticmethod
    def _parse_tag_results(payload: Any) -> list[QlooTag]:
        if not isinstance(payload, dict):
            raise QlooResponseError("Qloo tag response was malformed.")
        if payload.get("success") is False:
            raise QlooResponseError("Qloo tag search reported a failure.")
        results = payload.get("results")
        if not isinstance(results, dict) or not isinstance(results.get("tags"), list):
            raise QlooResponseError("Qloo tag response was malformed.")
        return [_normalise_tag(item) for item in results["tags"]]

    @staticmethod
    def _parse_insight_results(payload: Any) -> list[QlooEntity]:
        if not isinstance(payload, dict):
            raise QlooResponseError("Qloo insights response was malformed.")
        if payload.get("success") is False:
            raise QlooResponseError("Qloo insights reported a failure.")
        results = payload.get("results")
        if not isinstance(results, dict) or not isinstance(
            results.get("entities"), list
        ):
            raise QlooResponseError("Qloo insights response was malformed.")
        return [_normalise_entity(item) for item in results["entities"]]


# A descriptive alias for callers that prefer the module's "service" naming.
QlooService = QlooClient
