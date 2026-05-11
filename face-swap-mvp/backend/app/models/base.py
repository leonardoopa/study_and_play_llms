"""
app.models.base — Base declarativa e helpers compartilhados

Todas as entidades ORM herdam de Base.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe base para todos os models SQLAlchemy."""



# -------------------------------------------------------
# Helpers reutilizáveis por todos os models
# -------------------------------------------------------


def utcnow() -> datetime:
    """Retorna o horário atual em UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


def new_uuid() -> uuid.UUID:
    """Gera um UUID v4 para usar como chave primária."""
    return uuid.uuid4()
