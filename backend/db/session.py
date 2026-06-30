"""Async SQLAlchemy database session factory.

Provides an async engine and sessionmaker for the PE Investment Platform.
"""

import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base

_RAW_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://pe_user:pe_password@localhost:5433/pe_platform",
)


def _clean_url(url: str) -> tuple[str, bool]:
    """Strip the ``pgbouncer`` query param (asyncpg rejects it).

    Returns the cleaned URL and whether a pooler param was present, so we can
    disable prepared-statement caching when connecting through pgbouncer.
    """
    parts = urlsplit(url)
    if not parts.query:
        return url, False
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    pooled = any(k.lower() == "pgbouncer" for k, _ in pairs)
    kept = [(k, v) for k, v in pairs if k.lower() != "pgbouncer"]
    cleaned = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment)
    )
    return cleaned, pooled


DATABASE_URL, _POOLED = _clean_url(_RAW_DATABASE_URL)

# Through a transaction-mode pooler (pgbouncer), server-side prepared
# statements aren't supported, so disable asyncpg's statement cache.
_connect_args = {"statement_cache_size": 0} if _POOLED else {}

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args=_connect_args,
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
