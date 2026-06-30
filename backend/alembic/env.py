from logging.config import fileConfig
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import create_engine, pool

from alembic import context
from core.config import settings
from db.models import Base


def _strip_unsupported_params(url: str) -> str:
    """Remove query params the Postgres drivers reject (e.g. ``pgbouncer``).

    Supabase's pooler connection strings append ``?pgbouncer=true``, which
    psycopg2 and asyncpg don't understand. Strip it so migrations connect with
    either the direct or pooled connection string.
    """
    parts = urlsplit(url)
    if not parts.query:
        return url
    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() != "pgbouncer"
    ]
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment)
    )

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def _sync_database_url() -> str:
    """Derive a synchronous (psycopg2) URL from the app's DATABASE_URL.

    The application runs on asyncpg, but Alembic migrations are synchronous, so we
    swap the async driver for psycopg2. Pulling the URL from settings keeps ``.env``
    the single source of truth for DB credentials — nothing is duplicated in
    ``alembic.ini`` (its ``sqlalchemy.url`` is intentionally ignored here).
    """
    url = _strip_unsupported_params(settings.database_url)
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "+psycopg2")
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=_sync_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(_sync_database_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
