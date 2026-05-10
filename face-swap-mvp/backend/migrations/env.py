"""
migrations/env.py — Configuração do Alembic para migrations assíncronas

Pontos-chave:
- Usa asyncpg (driver assíncrono) via run_async_migrations()
- Lê DATABASE_URL da variável de ambiente
- Importa Base.metadata do package app.models para autogenerate
"""

import os
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# -------------------------------------------------------
# Configuração do Alembic
# -------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# -------------------------------------------------------
# Injeta a DATABASE_URL da variável de ambiente
# -------------------------------------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://faceswap:faceswap@db:5432/faceswap_db",
)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# -------------------------------------------------------
# Importa metadata dos models (package app.models)
# O import do __init__.py garante que todos os models
# são registrados no metadata do Base.
# -------------------------------------------------------
from app.models import Base  # noqa: E402

target_metadata = Base.metadata


# -------------------------------------------------------
# Modo offline: gera SQL sem conectar ao banco
# -------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# -------------------------------------------------------
# Modo online assíncrono
# -------------------------------------------------------
def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# -------------------------------------------------------
# Entrypoint
# -------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
