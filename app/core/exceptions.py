"""API exception handling."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class NotFoundError(ValueError):
    """Raised when a requested resource does not exist."""


def register_exception_handlers(app: FastAPI) -> None:
    """Register API-wide exception handlers."""

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )
