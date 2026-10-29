"""Client-safe models for the NPC dialogue route.

The response deliberately separates four things that must not be conflated:

* ``reply`` — natural-language prose from the model;
* ``evidence`` — only entities actually returned by Qloo tools;
* ``tool_trace`` — bounded metadata about tool calls, never raw payloads;
* ``transition`` — the deterministic Task 06 rules result.

Conversation history is bounded and accepts only user/assistant turns. Tool,
system, and provider messages are server-owned and are never accepted from the
client.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from app.models.game import GameStage, GameState, NpcId

MAX_DIALOGUE_MESSAGE_LENGTH = 500
MAX_CONVERSATION_CONTENT_LENGTH = 1_600
MAX_CONVERSATION_TURNS = 8
MAX_DIALOGUE_REPLY_LENGTH = 1_600
MAX_DIALOGUE_EVIDENCE = 12

DialogueText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=MAX_DIALOGUE_MESSAGE_LENGTH,
    ),
]
ConversationText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=MAX_CONVERSATION_CONTENT_LENGTH,
    ),
]


class DialogueTurn(BaseModel):
    """One client-visible conversation turn."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["user", "assistant"]
    content: ConversationText


class DialogueRequest(BaseModel):
    """Request body for ``POST /api/npc/{npc_id}/dialogue``.

    ``state`` follows the Task 04/06 shape. ``conversation`` is optional,
    bounded prior context supplied by the client; the server re-validates it
    and never trusts it as game authority.
    """

    model_config = ConfigDict(extra="forbid")

    state: GameState
    state_token: str = Field(min_length=1, max_length=200)
    message: DialogueText
    conversation: list[DialogueTurn] = Field(
        default_factory=list,
        max_length=MAX_CONVERSATION_TURNS,
    )


ToolStatus = Literal["ok", "empty", "error", "rejected"]


class DialogueToolTrace(BaseModel):
    """Safe metadata for one requested tool call.

    Neither arguments nor provider payloads are returned. ``error_code`` is a
    stable server-owned code, not an external response body.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: str = Field(min_length=1, max_length=80)
    status: ToolStatus
    result_count: int = Field(default=0, ge=0, le=100)
    error_code: str | None = Field(default=None, max_length=80)


class DialogueEvidence(BaseModel):
    """One real Qloo entity observed during this conversation.

    Construction is server-side only and always comes from a normalized
    :class:`~app.services.qloo_service.QlooEntity` returned by the existing
    client. No label or ID is inferred by the model.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: Literal["qloo"] = "qloo"
    entity_id: str = Field(min_length=1, max_length=200)
    label: str = Field(default="", max_length=200)
    query_type: str = Field(default="", max_length=120)
    signal: float | None = Field(default=None, ge=0, le=1)


class DialogueTransition(BaseModel):
    """Deterministic rules-engine transition for this dialogue turn.

    This is produced by :func:`app.core.rules.record_npc_interaction`, not by
    the model.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    npc_id: NpcId
    applied: bool
    relationship_before: int = Field(ge=0, le=100)
    relationship_after: int = Field(ge=0, le=100)
    stage_before: GameStage
    stage_after: GameStage
    reasons: list[str] = Field(default_factory=list, max_length=10)


class DialogueResponse(BaseModel):
    """Typed dialogue response separating prose, evidence, trace, and state."""

    model_config = ConfigDict(extra="forbid")

    reply: str = Field(min_length=1, max_length=MAX_DIALOGUE_REPLY_LENGTH)
    evidence: list[DialogueEvidence] = Field(
        default_factory=list,
        max_length=MAX_DIALOGUE_EVIDENCE,
    )
    tool_trace: list[DialogueToolTrace] = Field(
        default_factory=list,
        max_length=8,
    )
    tool_calls_executed: int = Field(default=0, ge=0, le=3)
    transition: DialogueTransition
    state: GameState
    state_token: str = Field(min_length=1, max_length=200)
    conversation: list[DialogueTurn] = Field(
        default_factory=list,
        max_length=MAX_CONVERSATION_TURNS + 2,
    )

    @field_validator("evidence")
    @classmethod
    def evidence_ids_must_be_unique(
        cls, value: list[DialogueEvidence]
    ) -> list[DialogueEvidence]:
        """Return at most one evidence item per real Qloo entity ID."""

        seen: set[str] = set()
        for item in value:
            if item.entity_id in seen:
                raise ValueError("dialogue evidence entity IDs must be unique")
            seen.add(item.entity_id)
        return value


__all__ = [
    "MAX_CONVERSATION_CONTENT_LENGTH",
    "MAX_CONVERSATION_TURNS",
    "MAX_DIALOGUE_EVIDENCE",
    "MAX_DIALOGUE_MESSAGE_LENGTH",
    "MAX_DIALOGUE_REPLY_LENGTH",
    "DialogueEvidence",
    "DialogueRequest",
    "DialogueResponse",
    "DialogueToolTrace",
    "DialogueTransition",
    "DialogueTurn",
    "ToolStatus",
]
