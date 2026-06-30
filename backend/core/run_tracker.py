"""Run tracker for agent execution lifecycle.

``RunTracker`` is a thin coordinator that sits between the FastAPI layer and
``db.crud``.  It handles UUID generation, status transitions, error logging,
and retrieval — without modifying the underlying CRUD functions.
"""

from uuid import uuid4

from sqlalchemy import select

from db.crud import create_agent_log, list_agent_logs, update_agent_log
from db.models import AgentLog, AgentStatus
from db.session import async_session_factory


class RunTracker:
    """High-level tracker for agent runs.

    All DB mutations are delegated to the existing ``db.crud`` module.
    Direct SQLAlchemy queries are used only for lookups that the CRUD does not
    yet expose (e.g. by ``run_id``).
    """

    async def start_run(self, agent_name: str, input_data: dict) -> str:
        """Create a new ``AgentLog`` with status ``PENDING``.

        Args:
            agent_name: Machine-friendly agent identifier (e.g. ``"dummy"``).
            input_data: The payload that will be passed to the agent.

        Returns:
            The generated UUID ``run_id``.
        """
        run_id = str(uuid4())
        async with async_session_factory() as session:
            await create_agent_log(
                session,
                run_id=run_id,
                agent_name=agent_name,
                status=AgentStatus.PENDING,
                input_data=input_data,
            )
        return run_id

    async def _get_log_by_run_id(self, session, run_id: str) -> AgentLog | None:
        """Internal helper — look up an ``AgentLog`` by its UUID ``run_id``."""
        result = await session.execute(select(AgentLog).where(AgentLog.run_id == run_id))
        return result.scalar_one_or_none()

    async def update_status(
        self,
        run_id: str,
        status: AgentStatus,
        output_data: dict | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Transition a run to a new status and optionally store output / duration.

        Args:
            run_id: The UUID returned by ``start_run()``.
            status: The new status to set.
            output_data: Optional result payload to persist.
            duration_ms: Optional execution duration in milliseconds.
        """
        async with async_session_factory() as session:
            log = await self._get_log_by_run_id(session, run_id)
            if log is None:
                raise ValueError(f"AgentLog with run_id={run_id} not found")
            kwargs: dict = {"status": status}
            if output_data is not None:
                kwargs["output_data"] = output_data
            if duration_ms is not None:
                kwargs["duration_ms"] = duration_ms
            await update_agent_log(session, log.id, **kwargs)

    async def log_error(self, run_id: str, error: str) -> None:
        """Append an error message and set status to ``FAILED``.

        Args:
            run_id: The UUID returned by ``start_run()``.
            error: Human-readable error string.
        """
        async with async_session_factory() as session:
            log = await self._get_log_by_run_id(session, run_id)
            if log is None:
                raise ValueError(f"AgentLog with run_id={run_id} not found")
            errors = log.errors or []
            errors.append(error)
            await update_agent_log(
                session, log.id, errors=errors, status=AgentStatus.FAILED
            )

    async def get_run(self, run_id: str) -> AgentLog | None:
        """Fetch a single run by its UUID.

        Args:
            run_id: The UUID returned by ``start_run()``.

        Returns:
            The ``AgentLog`` ORM instance, or ``None`` if not found.
        """
        async with async_session_factory() as session:
            return await self._get_log_by_run_id(session, run_id)

    async def list_runs(self, agent_name: str | None = None, limit: int = 50) -> list[AgentLog]:
        """List recent runs, optionally filtered by agent name.

        Args:
            agent_name: If provided, only logs for this agent are returned.
            limit: Maximum rows to return (default 50).

        Returns:
            A list of ``AgentLog`` ORM instances ordered by creation time.
        """
        async with async_session_factory() as session:
            logs = await list_agent_logs(session, limit=limit, agent_name=agent_name)
            return list(logs)
