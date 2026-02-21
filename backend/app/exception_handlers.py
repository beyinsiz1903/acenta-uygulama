from __future__ import annotations

import logging
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import AppError, ErrorCode, error_response

logger = logging.getLogger("exception_handlers")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:  # type: ignore[override]
        details = exc.details.copy() if isinstance(exc.details, dict) else {}
        cid = getattr(request.state, "correlation_id", None)
        if cid and "correlation_id" not in details:
            details["correlation_id"] = cid

        # Add request path for debugging
        details["path"] = str(request.url.path)

        # Log structured error
        logger.warning(
            "AppError: code=%s status=%d path=%s message=%s cid=%s",
            exc.code, exc.status_code, request.url.path, exc.message, cid,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.code, exc.message, details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:  # type: ignore[override]
        # Simplify validation errors for cleaner client-side handling
        simplified_errors = []
        for err in exc.errors():
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            simplified_errors.append({
                "field": loc,
                "message": err.get("msg", "Invalid value"),
                "type": err.get("type", "unknown"),
            })

        details: Any = {"errors": simplified_errors}
        cid = getattr(request.state, "correlation_id", None)
        if cid:
            details["correlation_id"] = cid
        details["path"] = str(request.url.path)

        logger.warning(
            "ValidationError: path=%s errors=%d cid=%s",
            request.url.path, len(simplified_errors), cid,
        )

        return JSONResponse(
            status_code=422,
            content=error_response(
                ErrorCode.VALIDATION_ERROR,
                "İstek doğrulama hatası",
                details,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:  # type: ignore[override]
        # Map HTTP status codes to standardized error codes
        code_map = {
            400: ErrorCode.INVALID_INPUT,
            401: ErrorCode.AUTH_REQUIRED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            409: ErrorCode.CONFLICT,
            429: ErrorCode.RATE_LIMITED,
        }
        code = code_map.get(exc.status_code, "http_error")

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
        details["path"] = str(request.url.path)

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(code, message, details),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:  # type: ignore[override]
        # Log the full traceback for server errors
        cid = getattr(request.state, "correlation_id", None)
        logger.error(
            "Unhandled exception: path=%s cid=%s error=%s\n%s",
            request.url.path, cid, str(exc), traceback.format_exc(),
        )

        details: Any = {"path": str(request.url.path)}
        if cid:
            details["correlation_id"] = cid

        return JSONResponse(
            status_code=500,
            content=error_response(
                ErrorCode.INTERNAL_ERROR,
                "Beklenmeyen bir sunucu hatası oluştu",
                details,
            ),
        )
