"""
app — Package principal do Face Swap MVP

Cria a instância FastAPI, registra middleware CORS
e inclui os controllers (routers).
"""

from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.auth_controller import router as auth_router
from app.controllers.health_controller import router as health_router
from app.controllers.swap_controller import router as swap_router


def create_app() -> FastAPI:
    """
    Factory que cria e configura a aplicação FastAPI.
    Facilita testes e evita side-effects na importação.
    """
    application = FastAPI(
        title="Face Swap MVP",
        description="Real-time face swap via webcam",
        version="0.1.0",
    )

    # --- Middleware ---
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Em produção, restringir ao domínio real
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Controllers (routers) ---
    application.include_router(health_router)
    application.include_router(auth_router, prefix="/api")
    application.include_router(swap_router, prefix="/api")
    # Futuros controllers serão registrados aqui:
    # application.include_router(face_router, prefix="/faces", tags=["Faces"])
    # application.include_router(session_router, prefix="/sessions", tags=["Sessions"])

    return application


# Instância global usada pelo Uvicorn
app = create_app()
