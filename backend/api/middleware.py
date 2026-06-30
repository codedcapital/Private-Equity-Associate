"""Custom FastAPI middleware for the PE Investment Platform."""

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with timestamp, method, path, status code, and duration."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start_time = time.perf_counter()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000
        status_code = response.status_code
        method = request.method
        path = request.url.path

        log_line = f"{timestamp} | {method} {path} | {status_code} | {duration_ms:.2f}ms"
        print(log_line)  # noqa: T201

        return response
