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
        # Let global exception handlers (registered via register_exception_handlers)
        # deal with any exceptions so that tests can see real tracebacks.
        response: Response = await call_next(request)

        # 4) Always set response header
        response.headers["X-Correlation-Id"] = cid
        return response