"""Middleware HTTP: request_id + latencia + contexto de logs por request."""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

_logger = get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Inyecta request_id en el contexto de structlog y emite un evento por request.

    - Toma X-Request-ID del header entrante si viene; si no, genera uno nuevo.
    - Bindea (request_id, method, path) a los contextvars de structlog de modo
      que todos los logs emitidos durante ese request los llevan automáticamente.
    - Al finalizar emite `http_request_completed` con status + duration_ms.
    - Devuelve el request_id en el header X-Request-ID de la respuesta.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.perf_counter()

        # Limpia contextvars residuales del worker y bindea los nuevos.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            _logger.exception("http_request_failed", duration_ms=duration_ms)
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        _logger.info(
            "http_request_completed",
            status=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response
