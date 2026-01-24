from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        # 1) Read or generate correlation id
        incoming = request.headers.get("X-Correlation-Id")
        if incoming and isinstance(incoming, str) and incoming.strip():
            cid = incoming.strip()
        else:
            cid = str(uuid.uuid4())

        # 2) Attach to state for downstream handlers / loggers
        request.state.correlation_id = cid

        # 3) Process request
        try:
            response: Response = await call_next(request)
        except Exception as exc:  # pragma: no cover - generic safety net
            # Let global exception handlers format the body, but still ensure header is set
            from fastapi.responses import JSONResponse
            from app.errors import error_response

            response = JSONResponse(
                status_code=500,
                content=error_response("internal_error", "Unexpected server error"),
            )

        # 4) Always set response header
        response.headers["X-Correlation-Id"] = cid
        return response