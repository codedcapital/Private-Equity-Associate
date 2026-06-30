import json
from unittest.mock import AsyncMock

import pytest
from tenacity import RetryError

from core.exceptions import LLMError, LLMRateLimitError
from core.retry import retry_llm, retry_with_json_fix


# ─────────────────────────────────────────────────────────────────────────────
# retry_llm decorator tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retry_decorator_retries_on_llm_error():
    """The decorator should retry when an LLMError is raised."""
    call_count = 0

    @retry_llm(max_attempts=3)
    async def flaky_llm_call():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise LLMError("transient failure")
        return "success"

    result = await flaky_llm_call()
    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_succeeds_after_transient_failure():
    """The decorator should succeed after a single transient failure."""
    call_count = 0

    @retry_llm(max_attempts=3)
    async def mostly_stable():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise LLMRateLimitError("rate limited")
        return "ok"

    result = await mostly_stable()
    assert result == "ok"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_gives_up_after_max_attempts():
    """The decorator should re-raise the last exception after max retries."""
    call_count = 0

    @retry_llm(max_attempts=3)
    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise LLMError("persistent failure")

    with pytest.raises(LLMError, match="persistent failure"):
        await always_fails()

    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_on_timeout_error():
    """The decorator should retry on TimeoutError."""
    call_count = 0

    @retry_llm(max_attempts=2)
    async def timeout_prone():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("connection timeout")
        return "recovered"

    result = await timeout_prone()
    assert result == "recovered"
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_does_not_retry_on_unexpected_exception():
    """The decorator should not retry on exceptions not in the retry list."""
    call_count = 0

    @retry_llm(max_attempts=3)
    async def raises_value_error():
        nonlocal call_count
        call_count += 1
        raise ValueError("not a retryable error")

    with pytest.raises(ValueError):
        await raises_value_error()

    assert call_count == 1


# ─────────────────────────────────────────────────────────────────────────────
# retry_with_json_fix tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retry_with_json_fix_succeeds_first_time():
    """If the function succeeds, no retry is attempted."""
    mock_fn = AsyncMock(return_value={"status": "ok"})

    result = await retry_with_json_fix(mock_fn)

    assert result == {"status": "ok"}
    assert mock_fn.call_count == 1
    assert "strict_json" not in mock_fn.call_args.kwargs


@pytest.mark.asyncio
async def test_retry_with_json_fix_retries_on_malformed_json():
    """On JSONDecodeError, the function is retried with strict_json=True."""
    mock_fn = AsyncMock(side_effect=[
        json.JSONDecodeError("bad", "doc", 0),
        {"status": "ok"},
    ])

    result = await retry_with_json_fix(mock_fn)

    assert result == {"status": "ok"}
    assert mock_fn.call_count == 2
    # First call: no strict_json
    assert mock_fn.call_args_list[0].kwargs.get("strict_json") is None
    # Second call: strict_json=True
    assert mock_fn.call_args_list[1].kwargs.get("strict_json") is True


@pytest.mark.asyncio
async def test_retry_with_json_fix_reraises_on_second_failure():
    """If the retry also fails, the JSONDecodeError is propagated."""
    mock_fn = AsyncMock(side_effect=[
        json.JSONDecodeError("bad", "doc", 0),
        json.JSONDecodeError("still bad", "doc", 0),
    ])

    with pytest.raises(json.JSONDecodeError):
        await retry_with_json_fix(mock_fn)

    assert mock_fn.call_count == 2
