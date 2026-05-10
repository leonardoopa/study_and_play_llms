"""
app.database — Conexão assíncrona com PostgreSQL via SQLAlchemy

Expõe:
- engine:        motor assíncrono do SQLAlchemy
- async_session:  factory de sessões assíncronas
- get_db():      dependência FastAPI que injeta a sessão no request
"""

import os

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# -------------------------------------------------------
# URL de conexão — vem do .env (injetada pelo Docker Compose)
# Formato: postgresql+asyncpg://user:pass@host:port/dbname
# -------------------------------------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://faceswap:faceswap@db:5432/faceswap_db",
)

# -------------------------------------------------------
# Engine assíncrono
# -------------------------------------------------------
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
)

# -------------------------------------------------------
# Session factory assíncrona
#   expire_on_commit=False evita lazy-loads acidentais
#   após commit (comum em APIs assíncronas)
# -------------------------------------------------------
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# -------------------------------------------------------
# Dependência FastAPI — injeta sessão em cada request
# -------------------------------------------------------
async def get_db():
    """
    Abre uma sessão de banco, faz commit automático ao final
    do request e rollback se ocorrer exceção.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
