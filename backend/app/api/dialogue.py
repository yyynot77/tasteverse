"""NPC dialogue route with DeepSeek tool calling and deterministic rules."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.agents.deepseek_client import DeepSeekError
from app.agents.orchestrator import AgentError
from app.agents.service import DialogueService
from app.api.errors import ApiError
from app.core.config import DeepSeekConfigurationError
from app.core.rules import RulesError, record_npc_interaction
from app.core.state_security import (
    StateConfigurationError,
    StateSecurityError,
    sign_state,
    verify_state,
)
from app.models.dialogue import (
    DialogueRequest,
    DialogueResponse,
    DialogueToolTrace,
    DialogueTransition,
    DialogueTurn,
)
from app.models.game import GameState
from app.models.npc import NPC_BY_ID
from app.services.qloo_service import QlooConfigurationError

router = APIRouter(prefix="/api/npc", tags=["dialogue"])

_NOT_FOUND = {"description": "Unknown NPC"}
_AGENT_FAILURE = {"description": "Recoverable dialogue failure"}


def _get_service(request: Request) -> DialogueService:
    """Return the app-scoped service, creating it lazily on first use."""

    service = getattr(request.app.state, "dialogue_service", None)
    if service is not None:
        return service

    factory = getattr(request.app.state, "dialogue_service_factory", None)
    try:
        service = factory() if factory is not None else DialogueService.from_env()
    except (DeepSeekConfigurationError, QlooConfigurationError) as exc:
        raise ApiError(
            status_code=503,
            code=getattr(exc, "code", "agent_configuration_error"),
            message=str(exc),
            retryable=False,
        ) from None

    request.app.state.dialogue_service = service
    return service


def _agent_api_error(exc: Exception) -> ApiError:
    """Map agent/provider failures to the shared safe error envelope."""

    if isinstance(exc, DeepSeekError):
        return ApiError(
            status_code=exc.status_code,
            code=exc.code,
            message=str(exc),
            retryable=exc.retryable,
        )
    if isinstance(exc, AgentError):
        return ApiError(
            status_code=exc.status_code,
            code=exc.code,
            message=str(exc),
            retryable=exc.retryable,
        )
    return ApiError(
        status_code=502,
        code="agent_error",
        message="The dialogue service could not complete the turn.",
        retryable=True,
    )


def _verify_game_state(state: GameState, token: str) -> None:
    """Validate the signed envelope before any provider or rules call."""

    try:
        verify_state(state, token)
    except StateConfigurationError as exc:
        raise ApiError(
            status_code=503,
            code=exc.code,
            message=str(exc),
            retryable=False,
        ) from None
    except StateSecurityError as exc:
        raise ApiError(
            status_code=409,
            code=exc.code,
            message=str(exc),
            retryable=False,
        ) from None


@router.post(
    "/{npc_id}/dialogue",
    response_model=DialogueResponse,
    responses={404: _NOT_FOUND, 409: _AGENT_FAILURE, 422: _AGENT_FAILURE},
)
async def talk_to_npc(
    npc_id: str,
    request: DialogueRequest,
    http_request: Request,
) -> DialogueResponse:
    """Run one bounded dialogue turn and apply the Task 06 interaction rule.

    The model's prose and tool requests are advisory. The returned
    ``transition`` comes exclusively from ``record_npc_interaction``.
    """

    profile = NPC_BY_ID.get(npc_id)  # type: ignore[arg-type]
    if profile is None:
        raise ApiError(
            status_code=404,
            code="npc_not_found",
            message="NPC not found.",
        )

    _verify_game_state(request.state, request.state_token)

    if request.state.stage == "complete":
        raise ApiError(
            status_code=409,
            code="stage_prerequisite",
            message="The game is complete; dialogue transitions are closed.",
        )

    service = _get_service(http_request)
    try:
        result = await service.run(
            npc_id=profile.id,
            state=request.state,
            message=request.message,
            conversation=request.conversation,
        )
    except (DeepSeekError, AgentError) as exc:
        raise _agent_api_error(exc) from None

    try:
        transition = record_npc_interaction(
            request.state,
            profile.id,
            event_id=f"dialogue:{request.state.session_id}:{profile.id}",
        )
    except RulesError as exc:
        raise ApiError(
            status_code=409,
            code=exc.code,
            message=str(exc),
            retryable=False,
        ) from None

    trace = [
        DialogueToolTrace.model_validate(item) for item in result.tool_trace
    ]
    conversation = [
        *request.conversation,
        DialogueTurn(role="user", content=request.message),
        DialogueTurn(role="assistant", content=result.reply),
    ]

    return DialogueResponse(
        reply=result.reply,
        evidence=result.evidence,
        tool_trace=trace,
        tool_calls_executed=result.tool_calls_executed,
        transition=DialogueTransition(
            npc_id=transition.npc_id,
            applied=transition.applied,
            relationship_before=transition.relationship_before,
            relationship_after=transition.relationship_after,
            stage_before=transition.stage_before,
            stage_after=transition.stage_after,
            reasons=transition.reasons,
        ),
        state=transition.state,
        state_token=sign_state(transition.state),
        conversation=conversation,
    )


__all__ = ["router"]
