"""
app.models.user — Entidade User (tabela users)
"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow, new_uuid


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    # --- Relacionamentos ---
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    face_targets: Mapped[list["FaceTarget"]] = relationship(
        "FaceTarget", back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["SwapSession"]] = relationship(
        "SwapSession", back_populates="user", cascade="all, delete-orphan"
    )
