"""Models for the server-authoritative plan-evaluation route.

Only ``plan`` is player-authored. The signed state token, evidence, scores,
ending, and NPC reactions are produced by the server.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.game import (
    CulturalEvidence,
    Ending,
    GameState,
    NpcId,
    Plan,
    PlanComponent,
)

EvidenceStatus = Literal["available", "partial", "unavailable"]
InterpretationStatus = Literal["not_needed", "applied", "fallback"]


class PlanEvaluateRequest(BaseModel):
    """Request body for ``POST /api/plan/evaluate``."""

    model_config = ConfigDict(extra="forbid")

    state: GameState
    state_token: str = Field(min_length=1, max_length=200)
    plan: Plan

    @model_validator(mode="after")
    def require_usable_plan(self) -> "PlanEvaluateRequest":
        """Reject an entirely empty plan before any provider is called."""

        has_component = any(
            getattr(self.plan, component).strip()
            for component in ("movie", "music", "food")
        )
        if not has_component and not self.plan.free_text.strip():
            raise ValueError("plan must contain a selection or free text")
        return self


class PlanComponentScore(BaseModel):
    """Explainable score for one plan component."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    component: PlanComponent
    plan_value: str = Field(default="", max_length=200)
    evidence_count: int = Field(default=0, ge=0)
    evidence_available: bool
    score: int = Field(ge=0, le=100)
    npc_ids: list[NpcId] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list, max_length=10)


class PlanNpcScore(BaseModel):
    """Explainable server-owned score for one NPC."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    npc_id: NpcId
    relationship: int = Field(ge=0, le=100)
    clue_count: int = Field(default=0, ge=0)
    evidence_count: int = Field(default=0, ge=0)
    score: int = Field(ge=0, le=100)
    reasons: list[str] = Field(default_factory=list, max_length=10)


class NpcReaction(BaseModel):
    """Deterministic reaction text for one NPC; never model-authored state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    npc_id: NpcId
    name: str = Field(min_length=1, max_length=40)
    relationship: int = Field(ge=0, le=100)
    npc_score: int = Field(ge=0, le=100)
    reaction: str = Field(min_length=1, max_length=300)


class PlanEvaluateResponse(BaseModel):
    """Response body for ``POST /api/plan/evaluate``."""

    model_config = ConfigDict(extra="forbid")

    analysis: str = Field(min_length=1, max_length=1_000)
    evidence: list[CulturalEvidence] = Field(default_factory=list, max_length=24)
    evidence_status: EvidenceStatus
    interpretation_status: InterpretationStatus
    components: list[PlanComponentScore] = Field(default_factory=list, max_length=3)
    npcs: list[PlanNpcScore] = Field(default_factory=list, max_length=3)
    reactions: list[NpcReaction] = Field(default_factory=list, max_length=3)
    reasons: list[str] = Field(default_factory=list, max_length=20)
    score: int = Field(ge=0, le=100)
    ending: Ending
    state: GameState
    state_token: str = Field(min_length=1, max_length=200)


__all__ = [
    "EvidenceStatus",
    "InterpretationStatus",
    "NpcReaction",
    "PlanComponentScore",
    "PlanEvaluateRequest",
    "PlanEvaluateResponse",
    "PlanNpcScore",
]
