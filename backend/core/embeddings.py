"""OpenAI embedding generation with retry logic."""

from openai import AsyncOpenAI
from openai import RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from core.config import settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """Return a lazily-initialized AsyncOpenAI client."""
    global _client
    if _client is None:
        api_key = settings.openai_api_key
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Add it to your .env file or environment "
                "before running embedding operations."
            )
        _client = AsyncOpenAI(api_key=api_key)
    return _client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(RateLimitError),
    reraise=True,
)
async def generate_embedding(text: str) -> list[float]:
    """Generate OpenAI text-embedding-3-small embedding (1536-dim).

    Args:
        text: The text to embed.

    Returns:
        A list of 1536 floats representing the embedding vector.

    Raises:
        ValueError: If OPENAI_API_KEY is not set.
        RateLimitError: If rate limit is hit after all retries.
    """
    client = _get_client()
    response = await client.embeddings.create(
        input=text,
        model=settings.openai_embedding_model,
    )
    return response.data[0].embedding
