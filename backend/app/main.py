"""Minimal TasteVerse FastAPI application.

Task 01 only exposes a health check and prepares a reusable HTTP client for
later Qloo/DeepSeek integrations. No external service is called here.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

import httpx
from fastapi import FastAPI
from pydantic import BaseModel


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


app = FastAPI(
    title="TasteVerse API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return a simple readiness signal used by local checks and deploy probes."""

    return HealthResponse()
