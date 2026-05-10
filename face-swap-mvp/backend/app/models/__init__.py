"""
app.models — Re-exporta Base e todos os models

Importar este package garante que todos os models são registrados
no metadata do SQLAlchemy (necessário para Alembic autogenerate).

Uso:
    from app.models import Base, User, RefreshToken, FaceTarget, SwapSession
"""

from app.models.base import Base
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.face_target import FaceTarget
from app.models.swap_session import SwapSession

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "FaceTarget",
    "SwapSession",
]
