"""
app.dtos.auth_dto — DTOs de autenticação (tokens)
"""

from pydantic import BaseModel


class TokenResponseDTO(BaseModel):
    """Retorno do login/refresh: par de tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequestDTO(BaseModel):
    """Corpo da requisição de refresh de token."""
    refresh_token: str
