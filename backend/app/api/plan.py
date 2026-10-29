"""Server-authoritative plan evaluation route.

The route verifies the signed state before any provider call, lets DeepSeek
interpret free text only when needed, gathers real Qloo evidence, and then
delegates the score/ending to the deterministic Task 06 rules engine.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.errors import ApiError
from app.core.rules import (
    EvidenceProvenanceError,
    InvalidPlanError,
    RulesError,
    StagePrerequisiteError,
    evaluate_plan,
)
from app.core.state_security import (
    StateConfigurationError,
    StateSecurityError,
    sign_state,
    verify_state,
)
from app.models.game import GameState
from app.models.npc import NPC_BY_ID
from app.models.plan import (
    NpcReaction,
    PlanComponentScore,
    PlanEvaluateRequest,
    PlanEvaluateResponse,
    PlanNpcScore,
)
from app.services.plan_service import (
    PlanInterpretationError,
    PlanService,
    ResolvedPlanEvidence,
)
from app.services.qloo_service import QlooConfigurationError

router = APIRouter(prefix="/api/plan", tags=["plan"])

_REACTION_TEXT = {
    "perfect_harmony": {
        "mara": "Mara sets out warm bread and says the whole square smells like a celebration.",
        "jun": "Jun nods once, already sliding a record from its sleeve for the evening.",
        "theo": "Theo beams and starts rehearsing the story he will tell by the fountain.",
    },
    "mixed_night": {
        "mara": "Mara smiles but quietly sets aside a backup loaf in case the plan shifts.",
        "jun": "Jun calls it a promising mix, though not every track lands smoothly.",
        "theo": "Theo sees a story with rough edges, which he insists can still be charming.",
    },
    "cultural_chaos": {
        "mara": "Mara keeps the oven warm and suggests starting over with something familiar.",
        "jun": "Jun studies the empty record sleeve and says the night needs a steadier rhythm.",
        "theo": "Theo admits the plot has escaped him, but offers to help rewrite the ending.",
    },
}


def _get_service(request: Request) -> PlanService:
    service = getattr(request.app.state, "plan_service", None)
    if service is not None:
        return service

    factory = getattr(request.app.state, "plan_service_factory", None)
    try:
        service = factory() if factory is not None else PlanService.from_env()
    except QlooConfigurationError as exc:
        raise ApiError(
            status_code=503,
            code=exc.code,
            message=str(exc),
            retryable=False,
        ) from None
    request.app.state.plan_service = service
    return service


def _verify_game_state(state: GameState, token: str) -> None:
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


def _rules_api_error(exc: RulesError) -> ApiError:
    if isinstance(exc, (InvalidPlanError, EvidenceProvenanceError)):
        status_code = 422
    else:
        status_code = 409
    return ApiError(
        status_code=status_code,
        code=exc.code,
        message=str(exc),
        retryable=False,
    )


def _analysis(result: ResolvedPlanEvidence, score: int, ending: str) -> str:
    if result.evidence_status == "unavailable":
        return (
            "No verified Qloo evidence was available, so the plan was scored "
            f"conservatively at {score}/100 with ending {ending}."
        )
    if result.evidence_status == "partial":
        return (
            "Only part of the plan had verified Qloo evidence. The plan scored "
            f"{score}/100 with ending {ending}; missing components were not "
            "invented."
        )
    return (
        "All selected components had verified Qloo evidence. The plan scored "
        f"{score}/100 with ending {ending}."
    )


@router.post(
    "/evaluate",
    response_model=PlanEvaluateResponse,
    responses={
        409: {"description": "State integrity or stage error"},
        422: {"description": "Invalid plan"},
        503: {"description": "Provider configuration or interpretation unavailable"},
    },
)
async def evaluate_submitted_plan(
    request: PlanEvaluateRequest,
    http_request: Request,
) -> PlanEvaluateResponse:
    """Evaluate a plan with server-verified evidence and deterministic rules."""

    _verify_game_state(request.state, request.state_token)

    if request.state.stage != "plan":
        raise ApiError(
            status_code=409,
            code="stage_prerequisite",
            message="Meet all three residents before evaluating a plan.",
            retryable=False,
        )

    service = _get_service(http_request)

    try:
        resolved_plan, interpretation_status = await service.resolve(request.plan)
        collected = await service.collect_evidence(resolved_plan)
        transition = evaluate_plan(
            request.state,
            collected.evidence,
            plan=resolved_plan,
        )
    except PlanInterpretationError as exc:
        raise ApiError(
            status_code=503,
            code=exc.code,
            message=str(exc),
            retryable=exc.retryable,
        ) from None
    except RulesError as exc:
        raise _rules_api_error(exc) from None

    reactions = [
        NpcReaction(
            npc_id=npc.npc_id,
            name=NPC_BY_ID[npc.npc_id].name,
            relationship=npc.relationship,
            npc_score=npc.score,
            reaction=_REACTION_TEXT[transition.ending][npc.npc_id],
        )
        for npc in transition.npcs
    ]

    return PlanEvaluateResponse(
        analysis=_analysis(collected, transition.score, transition.ending),
        evidence=collected.evidence,
        evidence_status=collected.evidence_status,
        interpretation_status=interpretation_status,
        components=[
            PlanComponentScore.model_validate(component.model_dump())
            for component in transition.components
        ],
        npcs=[
            PlanNpcScore.model_validate(npc.model_dump())
            for npc in transition.npcs
        ],
        reactions=reactions,
        reasons=transition.reasons,
        score=transition.score,
        ending=transition.ending,
        state=transition.state,
        state_token=sign_state(transition.state),
    )


__all__ = ["router"]
