"""Async SQLAlchemy database session factory.

Provides an async engine and sessionmaker for the PE Investment Platform.
"""

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://pe_user:pe_password@localhost:5433/pe_platform",
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncSession:
    """Yield an async database session for use as a FastAPI dependency."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# Backwards-compatible alias
get_async_session = get_session


async def init_db() -> None:
    """Create all tables (development helper)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
