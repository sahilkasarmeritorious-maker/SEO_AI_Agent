from logging.config import fileConfig
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
import os
import sys
from pathlib import Path

# ── Add project root to path ──
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ── Import app modules ──
from app.core.config import get_settings
from app.db.base import Base
from app.db import models  # Import all models

settings = get_settings()

config = context.config

# ── Update sqlalchemy.url ──
# Use async URL for migrations
db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection needed)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Run migrations with a connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with DB connection)."""
    # Use async engine
    async_engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
    )
    
    async with async_engine.begin() as connection:
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Run async migrations
    import asyncio
    asyncio.run(run_migrations_online())


# from logging.config import fileConfig
# from sqlalchemy import create_engine
# from alembic import context
# import os
# import sys

# # ── FIRST: Add AI_Agent/ root to path ──
# sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# # ── THEN: Import app modules ──
# from app.core.config import get_settings
# from app.db.base import Base
# from app.db.models import User, Analysis

# settings = get_settings()

# config = context.config
# config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# if config.config_file_name is not None:
#     fileConfig(config.config_file_name)

# target_metadata = Base.metadata


# def run_migrations_offline() -> None:
#     url = config.get_main_option("sqlalchemy.url")
#     context.configure(
#         url=url,
#         target_metadata=target_metadata,
#         literal_binds=True,
#         dialect_opts={"paramstyle": "named"},
#     )
#     with context.begin_transaction():
#         context.run_migrations()


# def run_migrations_online() -> None:
#     connectable = create_engine(settings.DATABASE_URL)
#     with connectable.connect() as connection:
#         context.configure(
#             connection=connection,
#             target_metadata=target_metadata,
#         )
#         with context.begin_transaction():
#             context.run_migrations()


# if context.is_offline_mode():
#     run_migrations_offline()
# else:
#     run_migrations_online()