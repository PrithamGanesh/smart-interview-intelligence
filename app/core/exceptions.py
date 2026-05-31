"""API exception handling."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class NotFoundError(ValueError):
    """Raised when a requested resource does not exist."""


class ValidationError(ValueError):
    """Raised when input cannot be accepted safely."""


def register_exception_handlers(app: FastAPI) -> None:
    """Register API-wide exception handlers."""

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )
