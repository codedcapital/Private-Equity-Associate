"""Retry utilities for LLM nodes and JSON parsing.

Provides a decorator for retrying LLM calls with exponential backoff and a
helper for retrying functions that may return malformed JSON.
"""

import json
from typing import Any, Awaitable, Callable

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from core.exceptions import LLMError, LLMRateLimitError


def retry_llm(max_attempts: int = 3):
    """Decorator for retrying LLM calls with exponential backoff.

    Retries on ``LLMError``, ``LLMRateLimitError``, and ``TimeoutError``.
    Uses exponential backoff with a 2-second multiplier, minimum 2 seconds,
    maximum 30 seconds.

    Args:
        max_attempts: Maximum number of retry attempts (default 3).

    Returns:
        A tenacity ``retry`` decorator.
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type((LLMError, LLMRateLimitError, TimeoutError)),
        reraise=True,
    )


async def retry_with_json_fix(
    fn: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any
) -> Any:
    """Retry a function that returns JSON. If malformed JSON, retry once with stricter prompt.

    On the first call, ``fn`` is invoked normally. If it raises a
    ``json.JSONDecodeError``, the keyword argument ``strict_json`` is set to
    ``True`` and ``fn`` is called once more. This allows the wrapped function
    to detect the flag and append "Respond with valid JSON only." to its
    prompt before re-executing.

    Args:
        fn: An async callable expected to return a JSON-parseable result.
        *args: Positional arguments forwarded to ``fn``.
        **kwargs: Keyword arguments forwarded to ``fn``.

    Returns:
        The result of ``fn`` (on first or second attempt).

    Raises:
        json.JSONDecodeError: If the second attempt also fails with malformed JSON.
        Any other exception raised by ``fn`` on the first or second attempt.
    """
    try:
        return await fn(*args, **kwargs)
    except json.JSONDecodeError:
        # Retry once with stricter prompt
        kwargs["strict_json"] = True
        return await fn(*args, **kwargs)
