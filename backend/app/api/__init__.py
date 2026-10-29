"""HTTP routers and error handling for the TasteVerse API."""

from app.api.game import router as game_router
from app.api.npcs import router as npcs_router

__all__ = ["game_router", "npcs_router"]
