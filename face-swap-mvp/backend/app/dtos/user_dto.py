"""
app.dtos.user_dto — DTOs de entrada e saída para User
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict


class UserCreateDTO(BaseModel):
    """Dados necessários para cadastrar um novo usuário."""
    email: EmailStr
    password: str


class UserResponseDTO(BaseModel):
    """Dados retornados ao cliente após operações com usuário."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_at: datetime
