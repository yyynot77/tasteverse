"""Game-session routes that do not call Qloo, DeepSeek, or the rules engine."""

from __future__ import annotations

from fastapi import APIRouter

from app.models.game import (
    GameState,
    NpcRelationships,
    StartGameRequest,
    StartGameResponse,
)

router = APIRouter(prefix="/api/game", tags=["game"])


@router.post("/start", response_model=StartGameResponse)
def start_game(request: StartGameRequest) -> StartGameResponse:
    """Create a fresh, server-owned initial game state.

    Each call returns an independent state with neutral, identical
    relationships and no plan, clues, score, or ending.
    """

    state = GameState(
        player_interests=request.player_interests.model_copy(deep=True),
        stage="explore",
        relationships=NpcRelationships(),
        clues=[],
        plan=None,
        cultural_matches=None,
        score=None,
        ending=None,
    )
    return StartGameResponse(state=state)
