"""Allowlisted, server-validated tools for the dialogue agent.

The model may request only the four names in :data:`ALLOWED_TOOL_NAMES`. Every
argument object is parsed and validated server-side before use. Qloo calls go
through the existing :class:`~app.services.qloo_service.QlooClient`; the model
never supplies a URL, header, key, or arbitrary Qloo filter.

Insights calls require an entity ID that was actually returned by a search in
the same run. This prevents the model from inventing IDs or reusing labels as
IDs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.models.dialogue import DialogueEvidence, DialogueToolTrace
from app.models.game import GameState, NpcId
from app.models.npc import NPC_BY_ID
from app.services.qloo_service import (
    SUPPORTED_INSIGHTS_FILTER_TYPES,
    QlooClient,
    QlooEntity,
    QlooError,
)

MAIN_QUEST = (
    "The Lantern Night: meet Mara, Jun, and Theo, learn one cultural memory "
    "from each resident, then help the player plan a movie, music, and food "
    "evening for the town's Lantern Festival."
)

SEARCH_ENTITY_TYPES: tuple[str, ...] = (
    "urn:entity:movie",
    "urn:entity:artist",
    "urn:entity:book",
    "urn:entity:place",
    "urn:entity:brand",
    "urn:entity:destination",
)

MAX_TOOL_TAKE = 6
MAX_TOOL_RESULT_CHARS = 6_000
MAX_TOOL_EVIDENCE = 12
MAX_RESULT_NAME_LENGTH = 160
MAX_RESULT_TYPES = 4

_ALLOWED_INSIGHTS_TYPES = tuple(sorted(SUPPORTED_INSIGHTS_FILTER_TYPES))

SearchEntityType = Literal[
    "urn:entity:movie",
    "urn:entity:artist",
    "urn:entity:book",
    "urn:entity:place",
    "urn:entity:brand",
    "urn:entity:destination",
]


class _Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchCulturalEntityArgs(_Arguments):
    query: str = Field(min_length=1, max_length=120)
    entity_type: SearchEntityType
    take: int = Field(default=4, ge=1, le=MAX_TOOL_TAKE)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("query must not be blank")
        return text


class GetCulturalInsightsArgs(_Arguments):
    entity_id: str = Field(min_length=1, max_length=200)
    filter_type: str = Field(min_length=1, max_length=120)
    take: int = Field(default=4, ge=1, le=MAX_TOOL_TAKE)

    @field_validator("entity_id", "filter_type")
    @classmethod
    def values_must_not_be_blank(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("value must not be blank")
        return text

    @field_validator("filter_type")
    @classmethod
    def filter_type_must_be_supported(cls, value: str) -> str:
        if value not in _ALLOWED_INSIGHTS_TYPES:
            raise ValueError("unsupported insights filter type")
        return value


class GetNpcProfileArgs(_Arguments):
    npc_id: NpcId


class GetGameContextArgs(_Arguments):
    """The context tool takes no arguments."""


TOOL_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "type": "function",
        "function": {
            "name": "search_cultural_entity",
            "description": (
                "Search Qloo for a real cultural entity. Use this before "
                "get_cultural_insights. Returns only real entity IDs, labels, "
                "and types from Qloo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Short cultural title or name to search.",
                        "minLength": 1,
                        "maxLength": 120,
                    },
                    "entity_type": {
                        "type": "string",
                        "enum": list(SEARCH_ENTITY_TYPES),
                    },
                    "take": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_TOOL_TAKE,
                        "default": 4,
                    },
                },
                "required": ["query", "entity_type"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cultural_insights",
            "description": (
                "Fetch Qloo recommendations related to a real entity ID "
                "returned earlier by search_cultural_entity. Never invent an "
                "entity ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "A real entity_id returned by search.",
                        "minLength": 1,
                        "maxLength": 200,
                    },
                    "filter_type": {
                        "type": "string",
                        "enum": list(_ALLOWED_INSIGHTS_TYPES),
                    },
                    "take": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_TOOL_TAKE,
                        "default": 4,
                    },
                },
                "required": ["entity_id", "filter_type"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_npc_profile",
            "description": (
                "Read the server-owned public profile for one town resident."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "npc_id": {
                        "type": "string",
                        "enum": ["mara", "jun", "theo"],
                    }
                },
                "required": ["npc_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_game_context",
            "description": (
                "Read the server-owned main quest, player interests, stage, "
                "relationships, and clue summary. Takes no arguments."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
)

ALLOWED_TOOL_NAMES = frozenset(
    definition["function"]["name"] for definition in TOOL_DEFINITIONS
)


def _bounded_text(value: str, limit: int) -> str:
    text = value.strip()
    return text[:limit]


def _bounded_json(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if len(encoded) <= MAX_TOOL_RESULT_CHARS:
        return encoded
    # This should be unreachable for the bounded payloads below. If it ever
    # happens, fail closed instead of sending malformed/truncated JSON.
    return json.dumps(
        {"error": {"code": "tool_result_too_large"}},
        separators=(",", ":"),
    )


def _signal(value: float | None) -> float | None:
    if value is None:
        return None
    if 0 <= value <= 1:
        return float(value)
    return None


def _entity_to_result(entity: QlooEntity) -> dict[str, Any]:
    return {
        "entity_id": entity.entity_id,
        "label": _bounded_text(entity.name, MAX_RESULT_NAME_LENGTH),
        "types": [
            _bounded_text(item, 120) for item in entity.types[:MAX_RESULT_TYPES]
        ],
    }


def _entity_to_evidence(
    entity: QlooEntity, query_type: str
) -> DialogueEvidence:
    return DialogueEvidence(
        entity_id=entity.entity_id,
        label=_bounded_text(entity.name, 200),
        query_type=query_type,
        signal=_signal(entity.popularity),
    )


@dataclass
class ToolExecution:
    """Result of one model-requested tool call."""

    content: str
    trace: DialogueToolTrace
    evidence: list[DialogueEvidence] = field(default_factory=list)


@dataclass
class ToolContext:
    """Per-run server-owned data available to tools."""

    state: GameState
    npc_id: NpcId
    seen_entity_ids: set[str] = field(default_factory=set)


class ToolRuntime:
    """Validate and dispatch the four allowlisted tools for one run."""

    def __init__(self, qloo: QlooClient, context: ToolContext) -> None:
        self._qloo = qloo
        self._context = context

    async def execute(self, name: str, raw_arguments: str) -> ToolExecution:
        if name not in ALLOWED_TOOL_NAMES:
            return self._rejected(name, "unknown_tool")

        try:
            arguments = json.loads(raw_arguments or "{}")
        except (TypeError, ValueError):
            return self._rejected(name, "malformed_tool_json")
        if not isinstance(arguments, dict):
            return self._rejected(name, "invalid_tool_arguments")

        try:
            if name == "search_cultural_entity":
                return await self._search(arguments)
            if name == "get_cultural_insights":
                return await self._insights(arguments)
            if name == "get_npc_profile":
                return self._npc_profile(arguments)
            if name == "get_game_context":
                return self._game_context(arguments)
        except ValidationError:
            return self._rejected(name, "invalid_tool_arguments")
        except QlooError as exc:
            return self._error(name, exc.code)
        except Exception:
            # Never echo an unexpected exception, its message, or a raw
            # provider payload to the model or client.
            return self._error(name, "tool_internal_error")

        return self._rejected(name, "unknown_tool")

    async def _search(self, raw: dict[str, Any]) -> ToolExecution:
        args = SearchCulturalEntityArgs.model_validate(raw)
        entities = await self._qloo.search_entities(
            args.query,
            types=[args.entity_type],
            take=args.take,
        )
        self._context.seen_entity_ids.update(
            entity.entity_id for entity in entities
        )
        return self._qloo_result(
            "search_cultural_entity", entities, args.entity_type
        )

    async def _insights(self, raw: dict[str, Any]) -> ToolExecution:
        args = GetCulturalInsightsArgs.model_validate(raw)
        if args.entity_id not in self._context.seen_entity_ids:
            return self._rejected(
                "get_cultural_insights", "unverified_entity_id"
            )
        entities = await self._qloo.get_insights(
            filter_type=args.filter_type,
            entity_ids=[args.entity_id],
            take=args.take,
        )
        return self._qloo_result(
            "get_cultural_insights", entities, args.filter_type
        )

    def _npc_profile(self, raw: dict[str, Any]) -> ToolExecution:
        args = GetNpcProfileArgs.model_validate(raw)
        profile = NPC_BY_ID[args.npc_id].model_dump()
        profile["cultural_interests"] = profile["cultural_interests"][:6]
        return ToolExecution(
            content=_bounded_json({"profile": profile}),
            trace=DialogueToolTrace(
                tool="get_npc_profile", status="ok", result_count=1
            ),
        )

    def _game_context(self, raw: dict[str, Any]) -> ToolExecution:
        GetGameContextArgs.model_validate(raw)
        state = self._context.state
        payload = {
            "quest": MAIN_QUEST,
            "stage": state.stage,
            "player_interests": state.player_interests.model_dump(),
            "relationships": state.relationships.model_dump(),
            "interacted_npcs": list(state.interacted_npcs),
            "clue_count": len(state.clues),
            "clue_tags": [
                tag
                for clue in state.clues[:8]
                for tag in clue.tags[:4]
            ][:16],
        }
        return ToolExecution(
            content=_bounded_json(payload),
            trace=DialogueToolTrace(
                tool="get_game_context", status="ok", result_count=1
            ),
        )

    def _qloo_result(
        self,
        name: str,
        entities: list[QlooEntity],
        query_type: str,
    ) -> ToolExecution:
        results = [_entity_to_result(entity) for entity in entities]
        evidence: list[DialogueEvidence] = []
        seen: set[str] = set()
        for entity in entities:
            if entity.entity_id in seen:
                continue
            seen.add(entity.entity_id)
            evidence.append(_entity_to_evidence(entity, query_type))
            if len(evidence) >= MAX_TOOL_EVIDENCE:
                break

        payload = {
            "query_type": query_type,
            "count": len(results),
            "results": results,
        }
        return ToolExecution(
            content=_bounded_json(payload),
            trace=DialogueToolTrace(
                tool=name,
                status="ok" if results else "empty",
                result_count=len(results),
            ),
            evidence=evidence,
        )

    @staticmethod
    def _rejected(name: str, code: str) -> ToolExecution:
        return ToolExecution(
            content=_bounded_json(
                {"error": {"code": code, "message": "Tool call rejected."}}
            ),
            trace=DialogueToolTrace(
                tool=name, status="rejected", error_code=code
            ),
        )

    @staticmethod
    def _error(name: str, code: str) -> ToolExecution:
        return ToolExecution(
            content=_bounded_json(
                {"error": {"code": code, "message": "Tool call failed."}}
            ),
            trace=DialogueToolTrace(tool=name, status="error", error_code=code),
        )


__all__ = [
    "ALLOWED_TOOL_NAMES",
    "MAIN_QUEST",
    "MAX_TOOL_TAKE",
    "SEARCH_ENTITY_TYPES",
    "TOOL_DEFINITIONS",
    "GetCulturalInsightsArgs",
    "GetGameContextArgs",
    "GetNpcProfileArgs",
    "SearchCulturalEntityArgs",
    "ToolContext",
    "ToolExecution",
    "ToolRuntime",
]
