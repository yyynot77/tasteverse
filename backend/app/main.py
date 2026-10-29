"""TasteVerse FastAPI application.

Task 04 adds the fixed NPC catalog and a validated game-start route. No Qloo,
DeepSeek, dialogue, scoring, or plan-evaluation calls are made here.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api import game_router, npcs_router
from app.api.errors import install_error_handlers

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


class HealthResponse(BaseModel):
    """Response body for the service health probe."""

    status: Literal["ok"] = "ok"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and tear down the process-wide outbound HTTP client."""

    app.state.http_client = httpx.AsyncClient(timeout=10.0)
    try:
        yield
    finally:
        await app.state.http_client.aclose()


def _normalize_origins(origins: Sequence[str]) -> list[str]:
    """Validate an explicit CORS allow-list.

    A wildcard is rejected because credentialed/wildcard CORS is easy to
    misconfigure. Set ``CORS_ALLOWED_ORIGINS`` to a comma-separated list of
    exact browser origins instead.
    """

    normalized = [origin.strip().rstrip("/") for origin in origins]
    normalized = [origin for origin in normalized if origin]
    if "*" in normalized:
        raise ValueError(
            "CORS_ALLOWED_ORIGINS must contain explicit origins, not '*'"
        )
    return normalized


def _cors_origins_from_env() -> list[str]:
    """Read the CORS allow-list from an explicit environment variable."""

    raw = os.getenv("CORS_ALLOWED_ORIGINS")
    if raw is None:
        return list(DEFAULT_CORS_ORIGINS)
    return _normalize_origins(raw.split(","))


def create_app(cors_origins: Sequence[str] | None = None) -> FastAPI:
    """Build the application, optionally overriding the CORS allow-list."""

    origins = (
        _cors_origins_from_env()
        if cors_origins is None
        else _normalize_origins(cors_origins)
    )

    application = FastAPI(
        title="TasteVerse API",
        version="0.1.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )

    install_error_handlers(application)
    application.include_router(npcs_router)
    application.include_router(game_router)

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        """Return the same readiness signal exposed by Task 01."""

        return HealthResponse()

    return application


app = create_app()
