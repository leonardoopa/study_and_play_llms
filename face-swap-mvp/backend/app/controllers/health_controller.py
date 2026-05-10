"""
app.controllers.health_controller — Healthcheck endpoint

Rota pública usada pelo Docker Compose e pelo frontend
para verificar se o backend está respondendo.
"""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Retorna status do serviço."""
    return {"status": "ok", "service": "face-swap-backend"}
