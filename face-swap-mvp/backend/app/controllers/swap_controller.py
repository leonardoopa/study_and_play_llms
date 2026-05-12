"""
app.controllers.swap_controller — Endpoints de Face Swap com Autenticação e Multi-usuário

Endpoints:
- POST /upload-face  → recebe foto com rosto source, salva no banco/disco e em cache
- WS   /ws/swap      → valida token via query param, registra SwapSession e faz streaming
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import cv2
import numpy as np
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.database import async_session, get_db
from app.models.face_target import FaceTarget
from app.models.swap_session import SwapSession
from app.models.user import User
from app.services.auth_service import get_current_user, get_user_from_token
from app.services.face_swap_engine import FaceSwapEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Swap"])

# -------------------------------------------------------
# Cache global em memória para baixa latência no streaming
# Mapeia: face_target_id (str) -> Face Object do InsightFace
# -------------------------------------------------------
_source_faces: dict[str, Any] = {}
_source_previews: dict[str, bytes] = {}
_engine: Optional[FaceSwapEngine] = None


def _get_engine() -> FaceSwapEngine:
    """Lazy-load do engine (singleton)."""
    global _engine
    if _engine is None:
        _engine = FaceSwapEngine()
        _engine.load_models()
    return _engine


# Diretório base para uploads
UPLOADS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
)
os.makedirs(UPLOADS_DIR, exist_ok=True)


# -------------------------------------------------------
# POST /upload-face — Upload da foto de destino (Protegido)
# -------------------------------------------------------
@router.post("/upload-face")
async def upload_face(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Recebe uma foto com o rosto alvo, valida, extrai o rosto,
    salva em disco e registra na tabela face_targets.
    """
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio"
        )

    # Decodificar imagem
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível decodificar a imagem",
        )

    # Detectar rosto
    engine = await run_in_threadpool(_get_engine)
    face = await run_in_threadpool(engine.get_best_face, img)

    if face is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum rosto detectado na imagem enviada",
        )

    # Salvar arquivo em disco com nome único
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOADS_DIR, unique_filename)

    # Operação de I/O em threadpool para não bloquear o loop
    def _save_file():
        with open(file_path, "wb") as f:
            f.write(contents)

    await run_in_threadpool(_save_file)

    # Registrar no banco de dados
    db_target = FaceTarget(
        user_id=current_user.id,
        filename=file.filename or unique_filename,
        file_path=file_path,
    )
    db.add(db_target)
    await db.commit()
    await db.refresh(db_target)

    target_id_str = str(db_target.id)

    # Colocar no cache de memória para acesso instantâneo via WebSocket
    _source_faces[target_id_str] = face

    # Gerar preview em cache
    bbox = face.bbox.astype(int)
    x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
    pad = int((x2 - x1) * 0.2)
    h, w = img.shape[:2]
    x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
    x2, y2 = min(w, x2 + pad), min(h, y2 + pad)
    face_crop = img[y1:y2, x1:x2]

    _, buf = cv2.imencode(".jpg", face_crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
    _source_previews[target_id_str] = buf.tobytes()

    logger.info(
        "Rosto alvo salvo! user_id=%s, target_id=%s", current_user.id, target_id_str
    )

    return {
        "status": "ok",
        "message": "Rosto salvo e processado com sucesso",
        "face_target_id": target_id_str,
        "bbox": bbox.tolist(),
        "has_enhancer": engine.has_enhancer,
    }


# -------------------------------------------------------
# GET /source-preview — Preview do rosto alvo
# -------------------------------------------------------
@router.get("/source-preview")
async def source_preview(face_target_id: str = Query(...)) -> Any:
    """Retorna o JPEG do crop do rosto de destino em cache."""
    from fastapi.responses import Response

    preview_bytes = _source_previews.get(face_target_id)
    if preview_bytes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preview não encontrado em cache",
        )
    return Response(content=preview_bytes, media_type="image/jpeg")


# -------------------------------------------------------
# GET /engine-status — Status geral do motor
# -------------------------------------------------------
@router.get("/engine-status")
async def engine_status() -> Any:
    """Status do motor em memória."""
    engine = _engine
    return {
        "engine_loaded": engine is not None and engine.is_loaded if engine else False,
        "has_enhancer": engine.has_enhancer if engine else False,
        "cached_faces_count": len(_source_faces),
    }


# -------------------------------------------------------
# WS /ws/swap — WebSocket de streaming em tempo real
# -------------------------------------------------------
@router.websocket("/ws/swap")
async def websocket_swap(
    websocket: WebSocket,
    token: str = Query(...),
    face_target_id: str = Query(...),
    enhance: bool = Query(False),
) -> None:
    """
    Endpoint WebSocket de altíssima performance.
    1. Valida token via query parameter (WSS handshake).
    2. Garante que o FaceTarget pertence ao usuário.
    3. Registra SwapSession (tracking e auditoria).
    4. Realiza streaming bidirecional binário sem bloquear pool do DB.
    """
    await websocket.accept()
    logger.info("Tentativa de conexão WS. face_target_id=%s", face_target_id)

    session_id: Optional[uuid.UUID] = None

    # Abrir uma sessão curta de DB para validação e registro inicial
    async with async_session() as db:
        try:
            user = await get_user_from_token(token, db)
        except Exception:
            await websocket.send_json({"error": "Token inválido ou expirado"})
            await websocket.close(code=1008)
            return

        try:
            target_uuid = uuid.UUID(face_target_id)
        except ValueError:
            await websocket.send_json({"error": "ID de target inválido"})
            await websocket.close(code=1008)
            return

        stmt = select(FaceTarget).where(
            FaceTarget.id == target_uuid,
            FaceTarget.user_id == user.id,
        )
        result = await db.execute(stmt)
        face_target = result.scalar_one_or_none()

        if not face_target:
            await websocket.send_json(
                {"error": "Rosto alvo não encontrado ou não autorizado"}
            )
            await websocket.close(code=1008)
            return

        # Criar a SwapSession de auditoria
        sess_record = SwapSession(
            user_id=user.id,
            face_target_id=face_target.id,
            started_at=datetime.now(timezone.utc),
        )
        db.add(sess_record)
        await db.commit()
        session_id = sess_record.id

    # Obter rosto do cache ou carregar do disco (caso o cache tenha limpado)
    source_face = _source_faces.get(face_target_id)
    if source_face is None:
        logger.info(
            "Cache miss para face_target_id=%s. Carregando do disco...", face_target_id
        )

        def _read_img():
            return cv2.imread(face_target.file_path)

        img = await run_in_threadpool(_read_img)
        if img is not None:
            engine = _get_engine()
            source_face = await run_in_threadpool(engine.get_best_face, img)
            if source_face:
                _source_faces[face_target_id] = source_face

    if source_face is None:
        await websocket.send_json({"error": "Falha ao recuperar o modelo do rosto"})
        await websocket.close(code=1011)
        return

    logger.info(
        "Sessão de Swap iniciada com sucesso. session_id=%s, user_id=%s",
        session_id,
        user.id,
    )

    engine = _get_engine()
    processing = False

    try:
        while True:
            data = await websocket.receive_bytes()

            # Backpressure
            if processing:
                continue

            processing = True

            try:
                nparr = np.frombuffer(data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is None:
                    await websocket.send_json({"error": "frame invalido"})
                    processing = False
                    continue

                # Processamento pesado offloaded
                result = await run_in_threadpool(
                    engine.swap_face_on_frame,
                    source_face,
                    frame,
                    enhance,
                )

                # Compressão JPEG
                _, buf = cv2.imencode(".jpg", result, [cv2.IMWRITE_JPEG_QUALITY, 80])

                await websocket.send_bytes(buf.tobytes())

            except Exception as e:
                logger.error("Erro interno no frame de swap: %s", e)
                try:
                    await websocket.send_json({"error": "processing_error"})
                except Exception:
                    pass
            finally:
                processing = False

    except WebSocketDisconnect:
        logger.info("Cliente desconectou do streaming WS. session_id=%s", session_id)
    except Exception as e:
        logger.error("Exceção fatal no loop WS: %s", e)
    finally:
        # Preencher ended_at abrindo uma nova sessão curta
        if session_id:
            try:
                async with async_session() as db:
                    stmt = select(SwapSession).where(SwapSession.id == session_id)
                    res = await db.execute(stmt)
                    db_session = res.scalar_one_or_none()
                    if db_session:
                        db_session.ended_at = datetime.now(timezone.utc)
                        await db.commit()
                        logger.info("Sessão finalizada salva no banco. id=%s", session_id)
            except Exception as e:
                logger.error("Erro ao fechar SwapSession no banco: %s", e)
