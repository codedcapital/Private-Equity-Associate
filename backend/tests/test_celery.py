"""Tests for Celery async job queue integration."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from api.main import app
from core.celery_app import celery_app
from core.tasks import run_agent_task
from db.crud import create_agent_log
from db.models import AgentLog, AgentStatus

TEST_DATABASE_URL = (
    "postgresql+asyncpg://pe_user:pe_password@localhost:5433/pe_platform"
)


# ── Module fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(autouse=True, scope="module")
def setup_always_eager():
    """Run Celery tasks synchronously in the test process and store results."""
    original_always_eager = celery_app.conf.task_always_eager
    original_store_eager = celery_app.conf.task_store_eager_result
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_store_eager_result = True
    yield
    celery_app.conf.task_always_eager = original_always_eager
    celery_app.conf.task_store_eager_result = original_store_eager


@pytest.fixture(autouse=True)
def patch_session_factory(monkeypatch):
    """Replace the global session factory with a test-specific NullPool instance."""
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        pool_pre_ping=True,
    )
    test_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    # Patch all modules that imported async_session_factory at load time
    monkeypatch.setattr("db.session.async_session_factory", test_factory)
    monkeypatch.setattr("core.run_tracker.async_session_factory", test_factory)
    monkeypatch.setattr("api.routers.pipeline.async_session_factory", test_factory)

    yield

    # Cleanup: truncate agent_logs between tests
    import asyncio

    async def _cleanup():
        async with test_factory() as session:
            await session.execute(
                text("TRUNCATE TABLE agent_logs RESTART IDENTITY CASCADE")
            )
            await session.commit()

    asyncio.run(_cleanup())
    # Engine is left for garbage collection; explicit dispose causes
    # asyncpg loop-attachment issues in the test suite.


@pytest.fixture
async def client():
    """Async HTTP client for FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Celery app tests ─────────────────────────────────────────────────────────


class TestCeleryApp:
    """Celery application configuration."""

    def test_celery_app_import(self):
        """Celery app can be imported and has expected config."""
        assert celery_app.main == "pe_platform"
        assert "redis://localhost:6379/0" in str(celery_app.conf.broker_url)
        assert celery_app.conf.task_track_started is True

    def test_beat_schedule(self):
        """Beat schedule includes nightly ingestion at 03:00 UTC."""
        schedule = celery_app.conf.beat_schedule
        assert "nightly-ingestion" in schedule
        assert schedule["nightly-ingestion"]["task"] == "core.tasks.run_nightly_ingestion_task"


# ── Task tests ───────────────────────────────────────────────────────────────


class TestRunAgentTask:
    """run_agent_task Celery task."""

    @pytest.mark.asyncio
    async def test_run_agent_task_apply_success(self):
        """Task executes synchronously via apply() and updates DB."""
        run_id = "test-run-dummy-001"

        # Seed AgentLog using the patched factory
        import db.session

        async with db.session.async_session_factory() as session:
            await create_agent_log(
                session,
                run_id=run_id,
                agent_name="dummy",
                status=AgentStatus.PENDING,
                input_data={"company_id": 1},
            )

        result = run_agent_task.apply(args=["dummy", {"company_id": 1}, run_id])

        assert result.successful() is True
        payload = result.result
        assert payload["run_id"] == run_id
        assert payload["status"] == "complete"
        assert payload["output"]["result"] == "dummy_output"

        # Verify DB side
        async with db.session.async_session_factory() as session:
            db_result = await session.execute(
                select(AgentLog).where(AgentLog.run_id == run_id)
            )
            log = db_result.scalar_one_or_none()
            assert log is not None
            assert log.status == AgentStatus.COMPLETE
            assert log.output_data is not None
            assert log.duration_ms is not None

    def test_run_agent_task_unsupported_agent(self):
        """Task fails for unregistered agents."""
        run_id = "test-run-fail-002"
        result = run_agent_task.apply(
            args=["unknown_agent", {"company_id": 1}, run_id]
        )
        assert result.successful() is False


# ── API endpoint tests ─────────────────────────────────────────────────────────


class TestAgentEndpoints:
    """FastAPI agent dispatch and status endpoints."""

    @pytest.mark.asyncio
    async def test_run_agent_endpoint(self, client):
        """POST /agents/{agent_name}/run returns correct structure."""
        payload = {"company_id": 1, "overrides": {}}
        response = await client.post("/agents/dummy/run", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["status"] == "pending"
        assert "message" in data

    @pytest.mark.asyncio
    async def test_get_run_status_endpoint(self, client):
        """GET /agents/runs/{run_id}/status returns combined status."""
        # 1. Dispatch a run
        payload = {"company_id": 1, "overrides": {}}
        post_resp = await client.post("/agents/dummy/run", json=payload)
        assert post_resp.status_code == 200
        run_id = post_resp.json()["run_id"]

        # 2. Query status
        response = await client.get(f"/agents/runs/{run_id}/status")
        assert response.status_code == 200

        data = response.json()
        assert data["run_id"] == run_id
        assert "celery_status" in data
        assert "agent_status" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_run_status_not_found(self, client):
        """GET /agents/runs/{run_id}/status returns 404 for unknown run."""
        response = await client.get(
            "/agents/runs/00000000-0000-0000-0000-000000000000/status"
        )
        assert response.status_code == 404
