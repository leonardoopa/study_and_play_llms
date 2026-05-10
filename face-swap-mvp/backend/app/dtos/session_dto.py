"""
app.dtos.session_dto — DTOs para sessões de face swap
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionCreateDTO(BaseModel):
    """Dados necessários para iniciar uma sessão de face swap."""
    face_target_id: uuid.UUID


class SessionResponseDTO(BaseModel):
    """Dados retornados ao cliente sobre uma sessão."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    face_target_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
