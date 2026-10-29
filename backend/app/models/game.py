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
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

NpcId = Literal["mara", "jun", "theo"]

# Task 06 may add further stages; Task 04 only starts a session in ``explore``.
GameStage = Literal["explore"]

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
    """Server-computed cultural match values for a submitted plan."""

    model_config = ConfigDict(extra="forbid")

    movies: float | None = Field(default=None, ge=0, le=1)
    music: float | None = Field(default=None, ge=0, le=1)
    food: float | None = Field(default=None, ge=0, le=1)


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
    plan: Plan | None = None
    cultural_matches: CulturalMatches | None = None
    score: int | None = Field(default=None, ge=0)
    ending: str | None = None


class StartGameResponse(BaseModel):
    """Response body for ``POST /api/game/start``."""

    model_config = ConfigDict(extra="forbid")

    state: GameState
