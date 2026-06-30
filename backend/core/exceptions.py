"""Custom exceptions for the LLM integration layer."""

class LLMError(Exception):
    """Base exception for LLM-related errors."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


class LLMBudgetExceeded(LLMError):
    """Raised when the LLM response exceeds the configured token budget."""


class LLMRateLimitError(LLMError):
    """Raised when the LLM rate limit is hit and retries are exhausted."""
