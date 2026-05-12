"""
app.controllers.auth_controller — Endpoints de Autenticação e Usuário
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dtos.auth_dto import RefreshTokenRequestDTO, TokenResponseDTO
from app.dtos.user_dto import UserCreateDTO, UserResponseDTO
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserResponseDTO,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserCreateDTO,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Cadastra um novo usuário no sistema."""
    # Verifica se e-mail já existe
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="E-mail já cadastrado no sistema",
        )

    # Cria o novo usuário
    hashed_password = get_password_hash(data.password)
    new_user = User(
        email=data.email,
        hashed_password=hashed_password,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/login", response_model=TokenResponseDTO)
async def login(
    data: UserCreateDTO,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Autentica o usuário com e-mail e senha,
    retornando os tokens de acesso e refresh.
    """
    stmt = select(User).where(User.email == data.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )

    access_token = create_access_token(user.id)
    refresh_token = await create_refresh_token(user.id, db)

    return TokenResponseDTO(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponseDTO)
async def refresh_token(
    data: RefreshTokenRequestDTO,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Recebe um refresh_token válido, revoga-o para evitar reuso
    e emite um novo par de tokens de acesso e refresh.
    """
    stmt = select(RefreshToken).where(
        RefreshToken.token == data.refresh_token,
        RefreshToken.revoked == False,
    )
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido, revogado ou não encontrado",
        )

    # Verifica se expirou
    if db_token.expires_at < datetime.now(timezone.utc):
        db_token.revoked = True
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expirado. Faça login novamente.",
        )

    # Revoga o token atual (rotação de tokens)
    db_token.revoked = True
    await db.commit()

    # Gera novo par de tokens
    access_token = create_access_token(db_token.user_id)
    new_refresh_token = await create_refresh_token(db_token.user_id, db)

    return TokenResponseDTO(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/logout")
async def logout(
    data: RefreshTokenRequestDTO,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Revoga o refresh token associado para realizar logout seguro."""
    stmt = select(RefreshToken).where(RefreshToken.token == data.refresh_token)
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()

    if db_token:
        db_token.revoked = True
        await db.commit()

    return {"status": "ok", "message": "Logout realizado com sucesso"}


@router.get("/me", response_model=UserResponseDTO)
async def get_me(current_user: User = Depends(get_current_user)) -> Any:
    """Retorna os dados do usuário atualmente autenticado."""
    return current_user
