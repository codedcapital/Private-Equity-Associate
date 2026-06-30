import pytest
from pydantic import BaseModel
from unittest.mock import AsyncMock, MagicMock

from core.exceptions import LLMBudgetExceeded, LLMError
from core.llm import LLMClient


class DummyResponseModel(BaseModel):
    name: str
    value: int


def test_count_tokens():
    client = LLMClient(api_key="dummy")
    text = "Hello, this is a test prompt for token counting."
    count = client.count_tokens(text)
    assert isinstance(count, int)
    assert count > 0


def test_estimate_cost():
    client = LLMClient(api_key="dummy")
    prompt_tokens = 2000
    completion_tokens = 500
    cost = client.estimate_cost(prompt_tokens, completion_tokens)
    expected = (prompt_tokens * 5.0 + completion_tokens * 15.0) / 1_000_000
    assert cost == pytest.approx(expected)


def test_missing_api_key_raises_clear_error():
    client = LLMClient(api_key=None)
    with pytest.raises(LLMError, match="API key is not configured"):
        client._get_client()


@pytest.mark.asyncio
async def test_chat_with_mock():
    client = LLMClient(api_key="test-key")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello from assistant"
    mock_response.choices[0].finish_reason = "stop"

    mock_create = AsyncMock(return_value=mock_response)
    client._client = MagicMock()
    client._client.chat.completions.create = mock_create

    result = await client.chat("system prompt", "user prompt")
    assert result == "Hello from assistant"
    mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_structured_with_mock():
    client = LLMClient(api_key="test-key")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"name": "Alpha", "value": 100}'
    mock_response.choices[0].finish_reason = "stop"

    mock_create = AsyncMock(return_value=mock_response)
    client._client = MagicMock()
    client._client.chat.completions.create = mock_create

    result = await client.chat_structured(
        system_prompt="You are a test bot.",
        user_prompt="Return JSON.",
        response_model=DummyResponseModel,
    )

    assert isinstance(result, DummyResponseModel)
    assert result.name == "Alpha"
    assert result.value == 100
    mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_budget_enforcement_raises():
    client = LLMClient(api_key="test-key", max_tokens=100)
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Partial response..."
    mock_response.choices[0].finish_reason = "length"

    mock_create = AsyncMock(return_value=mock_response)
    client._client = MagicMock()
    client._client.chat.completions.create = mock_create

    with pytest.raises(LLMBudgetExceeded, match="exceeded max_tokens"):
        await client.chat(
            system_prompt="You are a test bot.",
            user_prompt="Write a very long story.",
        )

    mock_create.reset_mock()
    with pytest.raises(LLMBudgetExceeded, match="exceeded max_tokens"):
        await client.chat_structured(
            system_prompt="You are a test bot.",
            user_prompt="Write a very long JSON.",
            response_model=DummyResponseModel,
        )
