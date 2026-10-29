"""Game-session routes that do not call Qloo, DeepSeek, or the rules engine."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.errors import ApiError
from app.core.state_security import StateConfigurationError, sign_state
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
    try:
        token = sign_state(state)
    except StateConfigurationError as exc:
        raise ApiError(
            status_code=503,
            code=exc.code,
            message=str(exc),
            retryable=False,
        ) from None
    return StartGameResponse(state=state, state_token=token)
