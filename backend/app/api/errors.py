"""Consistent JSON error envelope and exception handlers."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    """Machine-readable error information returned to clients."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    retryable: bool


class ErrorResponse(BaseModel):
    """Top-level error envelope shared by every application error."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail


class ApiError(Exception):
    """Application error that serializes as the shared error envelope."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    retryable: bool = False,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(code=code, message=message, retryable=retryable)
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


def install_error_handlers(app: FastAPI) -> None:
    """Register handlers that never expose stack traces or internal details."""

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request, __: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            status_code=422,
            code="invalid_request",
            message="Request validation failed.",
        )

    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        if exc.status_code == 404:
            code, message = "not_found", "Resource not found."
        elif exc.status_code == 405:
            code, message = "method_not_allowed", "Method not allowed."
        elif exc.status_code == 400:
            code, message = "bad_request", "Bad request."
        elif exc.status_code == 415:
            code, message = "unsupported_media_type", "Unsupported media type."
        else:
            code, message = "http_error", "The request could not be completed."
        return _error_response(
            status_code=exc.status_code,
            code=code,
            message=message,
            retryable=exc.status_code >= 500,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled application error", exc_info=exc)
        return _error_response(
            status_code=500,
            code="internal_error",
            message="An internal server error occurred.",
            retryable=True,
        )
