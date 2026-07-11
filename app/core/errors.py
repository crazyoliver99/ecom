"""Application error types and global exception handlers."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for expected, handled application errors."""

    status_code = 400
    error_code = "app_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AppendOnlyViolation(AppError):
    """Raised when code tries to update or delete an append-only record."""

    status_code = 409
    error_code = "append_only_violation"


class NotFoundError(AppError):
    """Raised when a requested record does not exist."""

    status_code = 404
    error_code = "not_found"


class ConfigurationError(AppError):
    """Raised when the system is misconfigured (e.g. missing seed data)."""

    status_code = 500
    error_code = "configuration_error"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        logger.warning("handled error on %s %s: %s", request.method, request.url.path, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error_code, "detail": exc.message},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "detail": "An unexpected error occurred."},
        )
