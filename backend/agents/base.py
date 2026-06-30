"""Abstract base agent for the PE Investment Platform.

All domain-specific agents (sourcing, financials, memo, etc.) should inherit
from ``BaseAgent`` and implement the ``run()`` coroutine.
"""

from abc import ABC, abstractmethod
from uuid import uuid4

from sqlalchemy import select

from db.crud import create_agent_log, update_agent_log
from db.models import AgentLog, AgentStatus
from db.session import async_session_factory


class BaseAgent(ABC):
    """Abstract base class for every async agent in the platform.

    Subclasses must implement ``run()``.  The base class provides helpers for
    run tracking (UUID generation, persistence, status querying).
    """

    @abstractmethod
    async def run(self, input_data: dict) -> dict:
        """Main execution logic.  Must be implemented by subclasses.

        Args:
            input_data: Arbitrary dict passed by the caller (e.g.
                ``{"company_id": 1, "overrides": {}}``).

        Returns:
            A dict representing the agent output.
        """
        ...

    async def start_run(self, input_data: dict) -> str:
        """Generate a ``run_id``, create a ``PENDING`` log row, and return it.

        Args:
            input_data: The payload that will later be passed to ``run()``.

        Returns:
            A UUID string identifying this run.
        """
        run_id = str(uuid4())
        async with async_session_factory() as session:
            await create_agent_log(
                session,
                run_id=run_id,
                agent_name=self.__class__.__name__,
                status=AgentStatus.PENDING,
                input_data=input_data,
            )
        return run_id

    async def score_confidence(self, output_data: dict) -> float:
        """Self-rate confidence 0–1 based on data quality.

        Subclasses should override this to implement domain-specific scoring.
        The default implementation returns 0.5.

        Args:
            output_data: The dict returned by ``run()``.

        Returns:
            A confidence score between 0.0 and 1.0.
        """
        return 0.5

    async def log_run(self, run_id: str, input_data: dict, output_data: dict) -> None:
        """Update the existing agent log with output data.

        Looks up the log by ``run_id`` and writes ``output_data`` to it via
        the existing CRUD layer.

        Args:
            run_id: The UUID returned by ``start_run()``.
            input_data: The original input (stored for reference).
            output_data: The result returned by ``run()``.
        """
        async with async_session_factory() as session:
            result = await session.execute(
                select(AgentLog).where(AgentLog.run_id == run_id)
            )
            log = result.scalar_one_or_none()
            if log is None:
                raise ValueError(f"AgentLog with run_id={run_id} not found")
            await update_agent_log(session, log.id, output_data=output_data)

    async def get_status(self, run_id: str) -> AgentStatus:
        """Return the current status of a run.

        Args:
            run_id: The UUID returned by ``start_run()``.

        Returns:
            The ``AgentStatus`` enum value stored in the DB.

        Raises:
            ValueError: If the run_id does not exist.
        """
        async with async_session_factory() as session:
            result = await session.execute(
                select(AgentLog).where(AgentLog.run_id == run_id)
            )
            log = result.scalar_one_or_none()
            if log is None:
                raise ValueError(f"AgentLog with run_id={run_id} not found")
            return log.status
