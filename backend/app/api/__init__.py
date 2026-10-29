"""HTTP routers and error handling for the TasteVerse API."""

from app.api.dialogue import router as dialogue_router
from app.api.game import router as game_router
from app.api.npcs import router as npcs_router
from app.api.plan import router as plan_router

__all__ = ["dialogue_router", "game_router", "npcs_router", "plan_router"]
