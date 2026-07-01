"""Rate limiting middleware for the PE Investment Platform.

Phase 4: Rate limiting on expensive endpoints (LLM, refresh, etc.)

For MVP: In-memory sliding window. Production: Redis-backed.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Rate limit config: {path_prefix: (requests, window_seconds)}
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/deals/": (60, 60),
    "/pipeline/run": (10, 60),
    "/agents/": (30, 60),
}


class _SlidingWindow:
    """In-memory sliding window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: list[float] = []

    def is_allowed(self) -> bool:
        now = time.time()
        # Remove expired timestamps
        cutoff = now - self.window_seconds
        self._timestamps = [t for t in self._timestamps if t > cutoff]

        if len(self._timestamps) < self.max_requests:
            self._timestamps.append(now)
            return True
        return False


# In-memory store: client_id -> path -> _SlidingWindow
_limiters: dict[str, dict[str, _SlidingWindow]] = defaultdict(dict)


def _get_client_id(request: Request) -> str:
    """Extract a stable client identifier from the request."""
    # Prefer X-User-Id header, fallback to IP address
    user_id = request.headers.get("X-User-Id")
    if user_id:
        return user_id

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    if request.client:
        return str(request.client.host)

    return "anonymous"


def _get_limiter(client_id: str, path: str) -> _SlidingWindow:
    """Get or create a rate limiter for a client+path."""
    for pattern, (max_req, window) in RATE_LIMITS.items():
        if path.startswith(pattern) or path.startswith(pattern.rstrip("0123456789/")):
            key = f"{pattern}:{client_id}"
            if key not in _limiters[client_id]:
                _limiters[client_id][key] = _SlidingWindow(max_req, window)
            return _limiters[client_id][key]

    # Default: no limit
    return _SlidingWindow(10_000, 1)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit middleware using sliding window."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip non-API paths
        if not request.url.path.startswith("/"):
            return await call_next(request)

        client_id = _get_client_id(request)
        limiter = _get_limiter(client_id, request.url.path)

        if not limiter.is_allowed():
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(limiter.window_seconds)},
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, limiter.max_requests - len(limiter._timestamps))
        )
        response.headers["X-RateLimit-Window"] = str(limiter.window_seconds)

        return response
