"""
app.services.face_swap_engine — Motor de Face Swap (InsightFace + inswapper_128)

Padrão Singleton: os modelos são carregados uma única vez e reutilizados
em todas as chamadas subsequentes.

Componentes:
- FaceAnalysis (buffalo_l): detecção de rostos + extração de embeddings
- inswapper_128.onnx:       modelo ONNX que realiza o swap de faces

Uso:
    from app.services.face_swap_engine import FaceSwapEngine

    engine = FaceSwapEngine()
    engine.load_models()
    result = engine.swap_face(source_img, target_img)
"""

import logging
import os
import time
from typing import Optional

import cv2
import numpy as np
import insightface
from insightface.app import FaceAnalysis

logger = logging.getLogger(__name__)

# -------------------------------------------------------
# Caminhos padrão dos modelos
# -------------------------------------------------------
DEFAULT_MODEL_PATH = os.getenv(
    "SWAP_MODEL_PATH",
    "/app/models/inswapper_128.onnx",
)


class FaceSwapEngine:
    """
    Motor de face swap baseado no InsightFace.

    Carrega os modelos de detecção (buffalo_l) e swap (inswapper_128)
    e expõe métodos para trocar rostos em imagens e frames de vídeo.
    """

    _instance: Optional["FaceSwapEngine"] = None

    def __new__(cls) -> "FaceSwapEngine":
        """Singleton — garante uma única instância do engine."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._face_analyser: Optional[FaceAnalysis] = None
        self._swapper = None
        self._enhancer = None
        self._models_loaded = False

    # -------------------------------------------------------
    # Carregamento dos modelos
    # -------------------------------------------------------
    def load_models(self, model_path: Optional[str] = None) -> None:
        """
        Inicializa o FaceAnalysis e carrega o modelo inswapper.

        Args:
            model_path: caminho para o inswapper_128.onnx.
                        Se None, usa DEFAULT_MODEL_PATH.
        """
        if self._models_loaded:
            logger.info("Modelos já carregados — reutilizando.")
            return

        model_path = model_path or DEFAULT_MODEL_PATH

        if not os.path.isfile(model_path):
            raise FileNotFoundError(
                f"Modelo não encontrado: {model_path}\n"
                "Baixe o inswapper_128.onnx e coloque na pasta models/."
            )

        logger.info("Carregando FaceAnalysis (buffalo_l)...")
        t0 = time.perf_counter()

        self._face_analyser = FaceAnalysis(
            name="buffalo_l",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        self._face_analyser.prepare(ctx_id=0, det_size=(640, 640))

        t1 = time.perf_counter()
        logger.info("FaceAnalysis carregado em %.2fs", t1 - t0)

        logger.info("Carregando modelo inswapper: %s", model_path)
        self._swapper = insightface.model_zoo.get_model(
            model_path, 
            download=False,
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )

        t2 = time.perf_counter()
        logger.info("Modelo inswapper carregado em %.2fs", t2 - t1)
        logger.info("Total de carregamento: %.2fs", t2 - t0)

        # Carrega enhancer (GFPGAN) se disponível
        try:
            from app.services.face_enhancer import FaceEnhancer
            self._enhancer = FaceEnhancer()
            self._enhancer.load_model()
            logger.info("GFPGAN enhancer disponível.")
        except FileNotFoundError:
            logger.warning("GFPGAN não encontrado — enhance desabilitado.")
            self._enhancer = None
        except Exception as e:
            logger.warning("Erro ao carregar GFPGAN: %s", e)
            self._enhancer = None

        self._models_loaded = True

    # -------------------------------------------------------
    # Detecção de rostos
    # -------------------------------------------------------
    def detect_faces(self, image: np.ndarray) -> list:
        """
        Detecta todos os rostos em uma imagem.

        Args:
            image: imagem BGR (formato OpenCV).

        Returns:
            Lista de objetos Face do InsightFace (com bbox, kps, embedding).
        """
        self._ensure_loaded()
        faces = self._face_analyser.get(image)
        logger.debug("Detectados %d rosto(s)", len(faces))
        return faces

    def get_best_face(self, image: np.ndarray):
        """
        Retorna o rosto com maior área (bbox) na imagem.
        Útil quando se espera um rosto principal (ex: foto de perfil).

        Returns:
            Objeto Face ou None se nenhum rosto for detectado.
        """
        faces = self.detect_faces(image)
        if not faces:
            return None
        # Ordena por área do bounding box (maior primeiro)
        return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

    # -------------------------------------------------------
    # Face Swap — estático (duas imagens)
    # -------------------------------------------------------
    def swap_face(
        self,
        source_img: np.ndarray,
        target_img: np.ndarray,
        enhance: bool = False,
    ) -> Optional[np.ndarray]:
        """
        Troca o rosto da target_img pelo rosto da source_img.

        Args:
            source_img: imagem com o rosto de ORIGEM (quem quer "virar").
            target_img: imagem com o rosto de DESTINO (onde o rosto será colado).
            enhance: se True, aplica GFPGAN no resultado.

        Returns:
            Imagem resultante com o swap, ou None se algum rosto não for detectado.
        """
        self._ensure_loaded()

        source_face = self.get_best_face(source_img)
        if source_face is None:
            logger.warning("Nenhum rosto detectado na imagem source.")
            return None

        target_face = self.get_best_face(target_img)
        if target_face is None:
            logger.warning("Nenhum rosto detectado na imagem target.")
            return None

        logger.info("Realizando face swap...")
        t0 = time.perf_counter()

        result = self._swapper.get(
            target_img.copy(), target_face, source_face, paste_back=True
        )

        t1 = time.perf_counter()
        logger.info("Face swap concluído em %.3fs", t1 - t0)

        # Enhance com GFPGAN (pós-processamento)
        if enhance and self._enhancer is not None:
            logger.info("Aplicando GFPGAN enhance...")
            t2 = time.perf_counter()
            # Re-detecta o rosto no resultado para alinhar o enhance
            result_face = self.get_best_face(result)
            if result_face is not None:
                result = self._enhancer.enhance_face(result, result_face)
            t3 = time.perf_counter()
            logger.info("GFPGAN concluído em %.3fs", t3 - t2)

        return result

    # -------------------------------------------------------
    # Face Swap — frame (para real-time, FASE 5)
    # -------------------------------------------------------
    def swap_face_on_frame(
        self,
        source_face,
        frame: np.ndarray,
        enhance: bool = False,
    ) -> Optional[np.ndarray]:
        """
        Aplica o face swap num frame de vídeo usando um rosto source
        pré-computado (evita re-detectar o source a cada frame).

        Args:
            source_face: objeto Face do InsightFace (pré-computado via get_best_face).
            frame: frame BGR da webcam.
            enhance: se True, aplica GFPGAN no resultado.

        Returns:
            Frame com o rosto trocado, ou o frame original se nenhum
            rosto for detectado no frame.
        """
        self._ensure_loaded()

        target_face = self.get_best_face(frame)
        if target_face is None:
            return frame  # Sem rosto no frame, retorna original

        result = self._swapper.get(
            frame.copy(), target_face, source_face, paste_back=True
        )

        if enhance and self._enhancer is not None:
            result_face = self.get_best_face(result)
            if result_face is not None:
                result = self._enhancer.enhance_face(result, result_face)

        return result

    @property
    def has_enhancer(self) -> bool:
        """True se o GFPGAN está carregado e disponível."""
        return self._enhancer is not None and self._enhancer.is_loaded

    # -------------------------------------------------------
    # Propriedades
    # -------------------------------------------------------
    @property
    def is_loaded(self) -> bool:
        """True se os modelos foram carregados com sucesso."""
        return self._models_loaded

    # -------------------------------------------------------
    # Helpers internos
    # -------------------------------------------------------
    def _ensure_loaded(self) -> None:
        """Garante que os modelos estão carregados antes de operar."""
        if not self._models_loaded:
            raise RuntimeError(
                "Modelos não carregados. Chame engine.load_models() primeiro."
            )
