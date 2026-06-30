from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import tiktoken
from openai import APIError, AsyncOpenAI, AuthenticationError, BadRequestError, RateLimitError
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import settings
from core.exceptions import LLMBudgetExceeded, LLMError, LLMRateLimitError

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class LLMClient:
    """Async OpenAI client with retry, token counting, cost estimation, and budget enforcement."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_chat_model
        self.max_tokens = max_tokens if max_tokens is not None else settings.max_llm_tokens_per_run
        self._encoding = self._resolve_encoding(self.model)
        self._client: AsyncOpenAI | None = None

    @staticmethod
    def _resolve_encoding(model: str) -> "tiktoken.Encoding":
        """Return the tiktoken encoding for ``model``, falling back to o200k_base.

        ``encoding_for_model`` raises KeyError for models tiktoken doesn't know
        (e.g. newer or custom deployments), so we degrade gracefully instead of
        crashing when a non-default chat model is configured.
        """
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            return tiktoken.get_encoding("o200k_base")

    def _get_client(self) -> AsyncOpenAI:
        """Lazy initialization of the AsyncOpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise LLMError(
                    "OpenAI API key is not configured. Set OPENAI_API_KEY or pass api_key."
                )
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken."""
        return len(self._encoding.encode(text))

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimate cost in USD for gpt-4o.

        Pricing:
          Input:  $5.00 per 1M tokens
          Output: $15.00 per 1M tokens
        """
        return (prompt_tokens * 5.0 + completion_tokens * 15.0) / 1_000_000

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2),
        retry=retry_if_exception_type(RateLimitError),
        reraise=True,
    )
    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
    ) -> str:
        """Send a chat completion and return the response text."""
        client = self._get_client()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=self.max_tokens,
            )
        except RateLimitError as exc:
            raise LLMRateLimitError(f"Rate limit exceeded: {exc}") from exc
        except BadRequestError as exc:
            raise LLMError(f"Bad request: {exc}") from exc
        except APIError as exc:
            raise LLMError(f"API error: {exc}") from exc
        except AuthenticationError as exc:
            raise LLMError(f"Authentication error: {exc}") from exc

        choice = response.choices[0]
        content = choice.message.content or ""

        if choice.finish_reason == "length":
            raise LLMBudgetExceeded(
                f"Response exceeded max_tokens budget ({self.max_tokens}). "
                "Increase max_tokens or reduce prompt length."
            )

        return content

    async def chat_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[BaseModel],
    ) -> BaseModel:
        """Send a chat completion and parse the response into a Pydantic model."""
        client = self._get_client()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                response_format={"type": "json_object"},
                max_tokens=self.max_tokens,
            )
        except RateLimitError as exc:
            raise LLMRateLimitError(f"Rate limit exceeded: {exc}") from exc
        except BadRequestError as exc:
            raise LLMError(f"Bad request: {exc}") from exc
        except APIError as exc:
            raise LLMError(f"API error: {exc}") from exc
        except AuthenticationError as exc:
            raise LLMError(f"Authentication error: {exc}") from exc

        choice = response.choices[0]
        content = choice.message.content or "{}"

        if choice.finish_reason == "length":
            raise LLMBudgetExceeded(
                f"Response exceeded max_tokens budget ({self.max_tokens}). "
                "Increase max_tokens or reduce prompt length."
            )

        try:
            parsed = response_model.model_validate_json(content)
        except ValidationError as exc:
            raise LLMError(f"Failed to parse structured response: {exc}") from exc

        return parsed
