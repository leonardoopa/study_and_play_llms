"""
app.controllers.swap_controller — Endpoints de Face Swap

Endpoints:
- POST /upload-face  → recebe foto com rosto source, extrai e guarda em memória
- WS   /ws/swap      → recebe frames da webcam, faz swap, retorna frames processados
"""

import asyncio
import logging
import time
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, WebSocket, WebSocketDisconnect, Query
from starlette.concurrency import run_in_threadpool

from app.services.face_swap_engine import FaceSwapEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Swap"])

# -------------------------------------------------------
# Estado em memória (MVP — sem auth, sem multi-user)
# -------------------------------------------------------
_source_face = None        # Objeto Face do InsightFace (pré-computado)
_source_preview: Optional[bytes] = None  # JPEG preview da source face
_engine: Optional[FaceSwapEngine] = None


def _get_engine() -> FaceSwapEngine:
    """Lazy-load do engine (singleton)."""
    global _engine
    if _engine is None:
        _engine = FaceSwapEngine()
        _engine.load_models()
    return _engine


# -------------------------------------------------------
# POST /upload-face — Upload da foto source
# -------------------------------------------------------
@router.post("/upload-face")
async def upload_face(file: UploadFile = File(...)):
    """
    Recebe uma foto com um rosto (ex: Neymar).
    Extrai o rosto e guarda em memória para uso no WebSocket.
    """
    global _source_face, _source_preview

    # Ler bytes do upload
    contents = await file.read()
    if not contents:
        return {"error": "Arquivo vazio"}

    # Decodificar imagem
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "Não foi possível decodificar a imagem"}

    # Detectar rosto
    engine = await run_in_threadpool(_get_engine)
    face = await run_in_threadpool(engine.get_best_face, img)

    if face is None:
        return {"error": "Nenhum rosto detectado na imagem"}

    _source_face = face

    # Gerar preview (crop do rosto)
    bbox = face.bbox.astype(int)
    x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
    # Expandir um pouco o crop
    pad = int((x2 - x1) * 0.2)
    h, w = img.shape[:2]
    x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
    x2, y2 = min(w, x2 + pad), min(h, y2 + pad)
    face_crop = img[y1:y2, x1:x2]

    _, buf = cv2.imencode(".jpg", face_crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
    _source_preview = buf.tobytes()

    logger.info("Rosto source carregado! bbox=%s", bbox.tolist())

    return {
        "status": "ok",
        "message": "Rosto carregado com sucesso",
        "bbox": bbox.tolist(),
        "has_enhancer": engine.has_enhancer,
    }


# -------------------------------------------------------
# GET /source-preview — Preview do rosto source
# -------------------------------------------------------
@router.get("/source-preview")
async def source_preview():
    """Retorna o JPEG do rosto source carregado."""
    from fastapi.responses import Response

    if _source_preview is None:
        return {"error": "Nenhum rosto source carregado"}
    return Response(content=_source_preview, media_type="image/jpeg")


# -------------------------------------------------------
# GET /engine-status — Status do engine
# -------------------------------------------------------
@router.get("/engine-status")
async def engine_status():
    """Retorna o status do engine e modelos carregados."""
    engine = _engine
    return {
        "engine_loaded": engine is not None and engine.is_loaded if engine else False,
        "has_enhancer": engine.has_enhancer if engine else False,
        "source_loaded": _source_face is not None,
    }


# -------------------------------------------------------
# WS /ws/swap — WebSocket de face swap real-time
# -------------------------------------------------------
@router.websocket("/ws/swap")
async def websocket_swap(
    websocket: WebSocket,
    enhance: bool = Query(False),
):
    """
    WebSocket que recebe frames JPEG binários da webcam,
    aplica face swap e retorna o frame processado como JPEG binário.
    """
    await websocket.accept()
    logger.info("WebSocket conectado (enhance=%s)", enhance)

    if _source_face is None:
        await websocket.send_json({
            "error": "Nenhum rosto source carregado. Use POST /upload-face primeiro."
        })
        await websocket.close()
        return

    engine = _get_engine()
    processing = False  # Flag de backpressure

    try:
        while True:
            # Receber frame binário
            data = await websocket.receive_bytes()

            # Backpressure: se estiver processando, ignora frame
            if processing:
                continue

            processing = True

            try:
                # Decodificar JPEG → numpy
                nparr = np.frombuffer(data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is None:
                    processing = False
                    continue

                # Face swap em thread (CPU-bound, não bloqueia asyncio)
                result = await run_in_threadpool(
                    engine.swap_face_on_frame,
                    _source_face,
                    frame,
                    enhance,
                )

                # Encodar resultado como JPEG
                _, buf = cv2.imencode(
                    ".jpg", result, [cv2.IMWRITE_JPEG_QUALITY, 80]
                )

                # Enviar frame processado
                await websocket.send_bytes(buf.tobytes())

            except Exception as e:
                logger.error("Erro processando frame: %s", e)
            finally:
                processing = False

    except WebSocketDisconnect:
        logger.info("WebSocket desconectado")
    except Exception as e:
        logger.error("Erro no WebSocket: %s", e)
