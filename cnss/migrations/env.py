# ==============================================================================
# CnSS Alembic Environment Configuration
# Configures the Alembic migration engine for asynchronous TimescaleDB operations.
# Dynamically loads database URLs from core.config.settings and registers all
# SQLAlchemy ORM models to support schema introspection and autogeneration.
# ==============================================================================

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

from core.config import settings
from core.models.base import Base

# --- Model Registration ---
# Explicitly import all ORM models to ensure they are registered in Base.metadata.
# Without these imports, Alembic cannot detect tables for autogenerate or migrations.
import core.models.users  # noqa: F401
import core.models.channels  # noqa: F401
import core.models.packet_flows  # noqa: F401

# --- Alembic Configuration Object ---
# Provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Metadata Binding ---
# Bind the SQLAlchemy metadata from our Base class to Alembic.
# This allows Alembic to compare the database schema against the ORM models.
target_metadata = Base.metadata

# --- Dynamic Database URL Injection ---
# Override the placeholder URL from alembic.ini with the actual async URL from settings.
# This ensures migrations use the correct credentials and host defined in .env.
config.set_main_option("sqlalchemy.url", settings.database_url)


# --- Offline Migration Execution ---
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Generates SQL scripts without connecting to the database.
    Useful for reviewing migration DDL before applying it to production.
    """
    # Retrieve the configured URL for script generation
    url = config.get_main_option("sqlalchemy.url")
    
    # Configure the context with the URL and metadata
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    # Execute the migration context to generate SQL output
    with context.begin_transaction():
        context.run_migrations()


# --- Online Migration Execution (Async) ---
def do_run_migrations(connection: Connection) -> None:
    """
    Synchronous helper to execute migrations within an active connection context.
    Called by the async wrapper to perform the actual schema modifications.
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Asynchronous wrapper for online migrations.
    Creates an async engine, establishes a connection, and delegates execution.
    Required because our database driver (asyncpg) is strictly asynchronous.
    """
    # Create an asynchronous SQLAlchemy engine using the configured URL
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    # Establish an async connection and run the synchronous migration helper
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    # Dispose of the engine to cleanly close database connections
    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Entry point for running migrations in 'online' mode.
    Manages the asyncio event loop to execute the async migration runner.
    """
    # Run the async migration function in the current event loop
    asyncio.run(run_async_migrations())


# --- Execution Context Routing ---
# Determine whether Alembic is running in offline (script generation) 
# or online (direct database execution) mode and invoke the appropriate function.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()