from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import AppError, error_response


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:  # type: ignore[override]
        details = exc.details.copy() if isinstance(exc.details, dict) else {}
        cid = getattr(request.state, "correlation_id", None)
        if cid and "correlation_id" not in details:
            details["correlation_id"] = cid
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.code, exc.message, details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:  # type: ignore[override]
        details: Any = {"errors": exc.errors()}
        cid = getattr(request.state, "correlation_id", None)
        if cid:
            details["correlation_id"] = cid
        return JSONResponse(
            status_code=422,
            content=error_response(
                "validation_error",
                "Request validation failed",
                details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:  # type: ignore[override]
        code = "not_found" if exc.status_code == 404 else "http_error"
        detail: Any = exc.detail
        if isinstance(detail, str):
            message = detail
            details: Any = {}
        elif isinstance(detail, dict):
            message = detail.get("message", "HTTP error")
            details = detail
        else:
            message = "HTTP error"
            details = {}
        cid = getattr(request.state, "correlation_id", None)
        if cid:
            details["correlation_id"] = cid
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(code, message, details),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:  # type: ignore[override]
        # In production you might log exc with traceback here
        details: Any = {}
        cid = getattr(request.state, "correlation_id", None)
        if cid:
            details["correlation_id"] = cid
        return JSONResponse(
            status_code=500,
            content=error_response("internal_error", "Unexpected server error", details),
        )
