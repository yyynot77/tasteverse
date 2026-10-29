"""Public NPC profile models and the fixed town cast.

Profiles are intentionally public metadata only. They contain no private
system prompts or role-instruction text.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.game import NpcId


class NpcProfile(BaseModel):
    """Public description of a fixed town resident."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: NpcId
    name: str = Field(min_length=1, max_length=40)
    role: str = Field(min_length=1, max_length=80)
    greeting: str = Field(min_length=1, max_length=300)
    personality: str = Field(min_length=1, max_length=300)
    cultural_interests: list[str] = Field(min_length=1, max_length=6)


NPC_PROFILES: tuple[NpcProfile, ...] = (
    NpcProfile(
        id="mara",
        name="Mara",
        role="Baker",
        greeting=(
            "The ovens are still warm. Smell that? Every loaf here starts "
            "with a story."
        ),
        personality=(
            "Warm, practical, and attentive to the stories hidden in everyday "
            "food."
        ),
        cultural_interests=["regional baking", "folk music", "food history"],
    ),
    NpcProfile(
        id="jun",
        name="Jun",
        role="Record shop owner",
        greeting=(
            "You can learn a lot about a town from the records it keeps. "
            "Listen closely."
        ),
        personality=(
            "Quiet, wry, and meticulous about music scenes and the people who "
            "shape them."
        ),
        cultural_interests=["vinyl records", "jazz", "film soundtracks"],
    ),
    NpcProfile(
        id="theo",
        name="Theo",
        role="Town storyteller",
        greeting=(
            "Sit by the fountain a while. Every face in this square has a "
            "favourite film."
        ),
        personality=(
            "Theatrical, reflective, and always ready to connect a film to a "
            "town memory."
        ),
        cultural_interests=["classic cinema", "local legends", "documentaries"],
    ),
)

NPC_BY_ID: dict[NpcId, NpcProfile] = {npc.id: npc for npc in NPC_PROFILES}
