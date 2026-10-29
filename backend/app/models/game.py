"""Typed game-state models shared by the API and later game-rule tasks.

The start request intentionally accepts only the fields a player supplies
(``player_interests``). Everything else in :class:`GameState` is server-owned
and is initialized here so later dialogue, rules, and scoring code can extend
the state without falling back to arbitrary dictionaries.
"""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

NpcId = Literal["mara", "jun", "theo"]

# ``explore`` is the Task 04 initial stage. Task 06 advances a state to
# ``plan`` once all three NPCs have been met, and to ``complete`` after the
# deterministic plan evaluation has selected an ending.
GameStage = Literal["explore", "plan", "complete"]

PlanComponent = Literal["movie", "music", "food"]
Ending = Literal["perfect_harmony", "mixed_night", "cultural_chaos"]

MAX_INTERESTS_PER_CATEGORY = 5
MAX_INTEREST_LENGTH = 80

InterestText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=MAX_INTEREST_LENGTH,
    ),
]
InterestList = Annotated[
    list[InterestText],
    Field(max_length=MAX_INTERESTS_PER_CATEGORY),
]


class PlayerInterests(BaseModel):
    """Player-supplied cultural interests for movie, music, and food."""

    model_config = ConfigDict(extra="forbid")

    movies: InterestList
    music: InterestList
    food: InterestList

    @model_validator(mode="after")
    def require_at_least_one_interest(self) -> PlayerInterests:
        """Reject an entirely empty interests profile."""

        if not (self.movies or self.music or self.food):
            raise ValueError("at least one interest is required")
        return self


class StartGameRequest(BaseModel):
    """Request body for ``POST /api/game/start``.

    Only player-supplied values are accepted. Server-computed game state is
    never accepted from this endpoint.
    """

    model_config = ConfigDict(extra="forbid")

    player_interests: PlayerInterests


class NpcRelationships(BaseModel):
    """Server-owned relationship values for the three fixed NPCs.

    Values are deliberately identical for every new session. Range is 0-100
    so deterministic rules in Task 06 can update them safely.
    """

    model_config = ConfigDict(extra="forbid")

    mara: int = Field(default=0, ge=0, le=100)
    jun: int = Field(default=0, ge=0, le=100)
    theo: int = Field(default=0, ge=0, le=100)


class Clue(BaseModel):
    """A clue discovered through a conversation.

    Task 04 starts with no clues; the shape is defined now so later tasks do
    not need an untyped list.
    """

    model_config = ConfigDict(extra="forbid")

    clue_id: str = Field(min_length=1, max_length=80)
    npc_id: NpcId
    text: str = Field(min_length=1, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=10)


class Plan(BaseModel):
    """Player-authored movie/music/food plan, validated by Task 07 later."""

    model_config = ConfigDict(extra="forbid")

    movie: str = Field(default="", max_length=200)
    music: str = Field(default="", max_length=200)
    food: str = Field(default="", max_length=200)
    free_text: str = Field(default="", max_length=1_000)


class CulturalMatches(BaseModel):
    """Server-computed cultural match values for a submitted plan.

    These values are informational output only. The deterministic rules engine
    never uses client-supplied values in this model as scoring authority.
    """

    model_config = ConfigDict(extra="forbid")

    movies: float | None = Field(default=None, ge=0, le=1)
    music: float | None = Field(default=None, ge=0, le=1)
    food: float | None = Field(default=None, ge=0, le=1)


class CulturalEvidence(BaseModel):
    """One verified Qloo evidence item linked to a plan component and NPC.

    Provenance is the authority, not prose or a numeric match value. An item
    must come from Qloo and expose at least one real entity/tag identifier. A
    label is for display only. ``signal`` is optional provider metadata and is
    deliberately not used as a score by the rules engine.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    source: Literal["qloo"] = "qloo"
    entity_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("entity_id", "qloo_entity_id", "entity"),
    )
    tag_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("tag_id", "qloo_tag_id", "tag"),
    )
    label: str = Field(default="", max_length=200)
    query_type: str = Field(default="", max_length=120)
    component: PlanComponent = Field(
        validation_alias=AliasChoices(
            "component", "plan_component", "category"
        )
    )
    npc_id: NpcId = Field(
        validation_alias=AliasChoices("npc_id", "npc")
    )
    signal: float | None = Field(default=None, ge=0, le=1)

    @field_validator("entity_id", "tag_id", mode="before")
    @classmethod
    def blank_identifier_is_none(cls, value: object) -> object:
        """Treat whitespace-only identifiers as absent."""

        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @model_validator(mode="before")
    @classmethod
    def normalise_component_alias(cls, value: object) -> object:
        """Accept the plural spelling used by the interests profile."""

        if isinstance(value, dict):
            data = dict(value)
            for key in ("component", "plan_component", "category"):
                component = data.get(key)
                if component == "movies":
                    data[key] = "movie"
                elif component == "foods":
                    data[key] = "food"
            return data
        return value

    @model_validator(mode="after")
    def require_identifier(self) -> CulturalEvidence:
        """Require at least one non-blank entity or tag identifier."""

        entity_id = (self.entity_id or "").strip()
        tag_id = (self.tag_id or "").strip()
        if not entity_id and not tag_id:
            raise ValueError("evidence requires a Qloo entity_id or tag_id")
        return self


# The API contract uses the short name ``Evidence`` for the same shape.
Evidence = CulturalEvidence


class GameState(BaseModel):
    """Serializable game state.

    ``player_interests`` is the only player-supplied portion. The remaining
    fields are owned and initialized by the server.
    """

    model_config = ConfigDict(extra="forbid")

    # Player-supplied data.
    player_interests: PlayerInterests

    # Server-computed data.
    session_id: UUID = Field(default_factory=uuid4)
    stage: GameStage = "explore"
    relationships: NpcRelationships = Field(default_factory=NpcRelationships)
    clues: list[Clue] = Field(default_factory=list)
    # Task 06 tracking keeps transitions idempotent across serialized states.
    interacted_npcs: list[NpcId] = Field(default_factory=list, max_length=3)
    applied_event_ids: list[str] = Field(default_factory=list, max_length=500)
    plan: Plan | None = None
    cultural_matches: CulturalMatches | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    ending: Ending | None = None

    @field_validator("interacted_npcs")
    @classmethod
    def interacted_npcs_must_be_unique(cls, value: list[NpcId]) -> list[NpcId]:
        """Keep the interaction set explicit and free of duplicate counts."""

        if len(set(value)) != len(value):
            raise ValueError("interacted_npcs must not contain duplicates")
        return value

    @field_validator("applied_event_ids")
    @classmethod
    def event_ids_must_be_unique(cls, value: list[str]) -> list[str]:
        """Reject a corrupted event log instead of silently double-counting."""

        if len(set(value)) != len(value):
            raise ValueError("applied_event_ids must not contain duplicates")
        for event_id in value:
            if not event_id.strip():
                raise ValueError("applied_event_ids must not contain blanks")
        return value


class StartGameResponse(BaseModel):
    """Response body for ``POST /api/game/start``."""

    model_config = ConfigDict(extra="forbid")

    state: GameState
