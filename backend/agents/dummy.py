"""Dummy agent for integration testing.

A minimal concrete agent that sleeps for 0.5 s and echoes its input.  Useful for
verifying the ``BaseAgent`` → ``RunTracker`` → FastAPI pipeline end-to-end.
"""

import asyncio

from agents.base import BaseAgent


class DummyAgent(BaseAgent):
    """Concrete agent that does nothing useful but exercises the framework."""

    async def run(self, input_data: dict) -> dict:
        """Simulate work and return a simple echo response.

        Args:
            input_data: Arbitrary dict from the caller.

        Returns:
            ``{"result": "ok", "echo": <input_data>}``
        """
        await asyncio.sleep(0.5)
        return {"result": "ok", "echo": input_data}
