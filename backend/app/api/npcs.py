"""Read-only routes for the fixed town cast."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.errors import ApiError, ErrorResponse
from app.models.npc import NPC_BY_ID, NPC_PROFILES, NpcProfile

router = APIRouter(prefix="/api/npcs", tags=["npcs"])

_NOT_FOUND_RESPONSE = {"model": ErrorResponse, "description": "Unknown NPC"}


@router.get("", response_model=list[NpcProfile])
def list_npcs() -> list[NpcProfile]:
    """Return the three fixed NPC profiles in their canonical order."""

    return list(NPC_PROFILES)


@router.get(
    "/{npc_id}",
    response_model=NpcProfile,
    responses={404: _NOT_FOUND_RESPONSE},
)
def get_npc(npc_id: str) -> NpcProfile:
    """Return one public NPC profile or a consistent 404 error envelope."""

    profile = NPC_BY_ID.get(npc_id)  # type: ignore[arg-type]
    if profile is None:
        raise ApiError(
            status_code=404,
            code="npc_not_found",
            message="NPC not found.",
        )
    return profile
