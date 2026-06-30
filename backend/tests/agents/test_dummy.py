"""Tests for DummyAgent, RunTracker, and agent-related API endpoints."""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agents.dummy import DummyAgent
from api.main import app
from core.run_tracker import RunTracker
from db.crud import truncate_all_tables, update_agent_log
from db.models import AgentLog, AgentStatus
from db.session import async_session_factory

pytestmark = pytest.mark.asyncio(loop_scope="session")

TEST_DATABASE_URL = (
    "postgresql+asyncpg://pe_user:pe_password@localhost:5433/pe_platform"
)


@pytest.fixture
async def session():
    """Provide a fresh async session and truncate all tables after the test."""
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with factory() as session:
        yield session
        await truncate_all_tables(session)
    await engine.dispose()


@pytest.fixture
async def tracker():
    """Provide a fresh RunTracker instance."""
    return RunTracker()


# ── DummyAgent unit tests ────────────────────────────────────────────────────

async def test_dummy_agent_run():
    """DummyAgent.run() should echo input and return a success result."""
    agent = DummyAgent()
    input_data = {"company_id": 42, "overrides": {"foo": "bar"}}
    output = await agent.run(input_data)
    assert output["result"] == "ok"
    assert output["echo"] == input_data


# ── RunTracker unit tests ──────────────────────────────────────────────────

async def test_tracker_start_run(session: AsyncSession, tracker: RunTracker) -> None:
    """start_run() should create a valid AgentLog with PENDING status."""
    input_data = {"company_id": 1, "overrides": {}}
    run_id = await tracker.start_run("dummy", input_data)

    # run_id should be a valid UUID string
    assert isinstance(run_id, str)
    assert len(run_id) == 36

    # Verify in DB
    log = await tracker.get_run(run_id)
    assert log is not None
    assert log.run_id == run_id
    assert log.agent_name == "dummy"
    assert log.status == AgentStatus.PENDING
    assert log.input_data == input_data


async def test_tracker_update_status(session: AsyncSession, tracker: RunTracker) -> None:
    """update_status() should change the status and optionally write output."""
    run_id = await tracker.start_run("dummy", {"company_id": 2})

    await tracker.update_status(run_id, AgentStatus.RUNNING)
    log = await tracker.get_run(run_id)
    assert log is not None
    assert log.status == AgentStatus.RUNNING
    assert log.output_data is None

    await tracker.update_status(
        run_id, AgentStatus.COMPLETE, output_data={"result": "ok"}
    )
    log = await tracker.get_run(run_id)
    assert log is not None
    assert log.status == AgentStatus.COMPLETE
    assert log.output_data == {"result": "ok"}


async def test_tracker_log_error(session: AsyncSession, tracker: RunTracker) -> None:
    """log_error() should append an error and set status to FAILED."""
    run_id = await tracker.start_run("dummy", {"company_id": 3})
    await tracker.log_error(run_id, "Something went wrong")

    log = await tracker.get_run(run_id)
    assert log is not None
    assert log.status == AgentStatus.FAILED
    assert log.errors == ["Something went wrong"]


async def test_tracker_list_runs(session: AsyncSession, tracker: RunTracker) -> None:
    """list_runs() should filter by agent_name and respect the limit."""
    await tracker.start_run("agent_a", {})
    await tracker.start_run("agent_a", {})
    await tracker.start_run("agent_b", {})

    all_logs = await tracker.list_runs()
    assert len(all_logs) == 3

    a_logs = await tracker.list_runs(agent_name="agent_a")
    assert len(a_logs) == 2

    b_logs = await tracker.list_runs(agent_name="agent_b", limit=1)
    assert len(b_logs) == 1


# ── API endpoint tests ───────────────────────────────────────────────────────

async def test_api_run_dummy(session: AsyncSession) -> None:
    """POST /agents/dummy/run should return a valid run_id and create a log entry."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/agents/dummy/run",
            json={"company_id": 1, "overrides": {}},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["message"] == "Agent run dispatched"
    assert "run_id" in data
    assert len(data["run_id"]) == 36

    # Verify DB side — log was created for the correct agent
    tracker = RunTracker()
    log = await tracker.get_run(data["run_id"])
    assert log is not None
    assert log.agent_name == "dummy"


async def test_api_get_run(session: AsyncSession) -> None:
    """GET /agents/runs/{run_id} should return the full AgentLog."""
    tracker = RunTracker()
    run_id = await tracker.start_run("dummy", {"company_id": 5, "overrides": {}})
    # Manually update status so the response has meaningful data
    await tracker.update_status(run_id, AgentStatus.COMPLETE, output_data={"result": "ok"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/agents/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert data["agent_name"] == "dummy"
    assert data["status"] == "complete"
    assert data["output_data"] == {"result": "ok"}
    assert data["input_data"] == {"company_id": 5, "overrides": {}}


async def test_api_list_runs(session: AsyncSession) -> None:
    """GET /agents/runs should return a paginated list of runs."""
    tracker = RunTracker()
    await tracker.start_run("dummy", {"company_id": 6})
    await tracker.start_run("dummy", {"company_id": 7})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/agents/runs?agent_name=dummy&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["logs"]) == 2


async def test_api_get_run_not_found(session: AsyncSession) -> None:
    """GET /agents/runs/{run_id} should return 404 for unknown run_id."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/agents/runs/{uuid4()}")
    assert response.status_code == 404
