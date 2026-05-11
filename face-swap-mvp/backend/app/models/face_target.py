"""
app.models.face_target — Entidade FaceTarget (tabela face_targets)
"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow, new_uuid


class FaceTarget(Base):
    __tablename__ = "face_targets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # --- Relacionamentos ---
    user: Mapped["User"] = relationship("User", back_populates="face_targets")
    sessions: Mapped[list["SwapSession"]] = relationship(
        "SwapSession", back_populates="face_target", cascade="all, delete-orphan"
    )
