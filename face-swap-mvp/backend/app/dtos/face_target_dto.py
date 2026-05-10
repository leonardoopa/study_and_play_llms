"""
app.dtos.face_target_dto — DTOs para upload de rosto (face target)
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FaceTargetResponseDTO(BaseModel):
    """Dados retornados ao cliente após upload de uma face target."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    filename: str
    file_path: str
    created_at: datetime
