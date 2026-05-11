"""
app.services.face_enhancer — Face Enhancer via GFPGAN (ONNX puro)

Melhora a qualidade do rosto após o face swap usando o modelo
GFPGANv1.4.onnx. Roda via onnxruntime — sem PyTorch.

Pipeline:
    1. Alinha o rosto com template FFHQ (5-point landmarks)
    2. Preprocessa para tensor NCHW float32 [-1, 1]
    3. Roda inferência ONNX
    4. Pós-processa e cola de volta no frame com feathered blending

Uso:
    from app.services.face_enhancer import FaceEnhancer

    enhancer = FaceEnhancer()
    enhancer.load_model()
    enhanced_frame = enhancer.enhance_face(frame, face)
"""

import logging
import os
import time
from typing import Optional

import cv2
import numpy as np
import onnxruntime

logger = logging.getLogger(__name__)

# -------------------------------------------------------
# Caminhos padrão
# -------------------------------------------------------
DEFAULT_ENHANCER_PATH = os.getenv(
    "ENHANCER_MODEL_PATH",
    "/app/models/GFPGANv1.4.onnx",
)

# -------------------------------------------------------
# Template FFHQ para alinhamento de rosto (5 pontos, base 512)
# -------------------------------------------------------
FFHQ_TEMPLATE_512 = np.array(
    [
        [192.98138, 239.94708],
        [318.90277, 240.19366],
        [256.63416, 314.01935],
        [201.26117, 371.41043],
        [313.08905, 371.15118],
    ],
    dtype=np.float32,
)


class FaceEnhancer:
    """
    Enhancer de rosto baseado no GFPGAN (ONNX puro).

    Singleton — carrega o modelo uma vez e reutiliza.
    """

    _instance: Optional["FaceEnhancer"] = None

    def __new__(cls) -> "FaceEnhancer":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._session: Optional[onnxruntime.InferenceSession] = None
        self._input_name: Optional[str] = None
        self._align_size: int = 512
        self._model_loaded = False
        self._mask_cache: dict = {"mask": None, "size": 0}

    # -------------------------------------------------------
    # Carregamento do modelo
    # -------------------------------------------------------
    def load_model(self, model_path: Optional[str] = None) -> None:
        """Carrega o modelo GFPGAN ONNX."""
        if self._model_loaded:
            logger.info("GFPGAN já carregado — reutilizando.")
            return

        model_path = model_path or DEFAULT_ENHANCER_PATH

        if not os.path.isfile(model_path):
            raise FileNotFoundError(
                f"Modelo GFPGAN não encontrado: {model_path}\n"
                "Baixe o GFPGANv1.4.onnx e coloque na pasta models/."
            )

        logger.info("Carregando GFPGAN: %s", model_path)
        t0 = time.perf_counter()

        self._session = onnxruntime.InferenceSession(
            model_path,
            providers=["CPUExecutionProvider"],
        )

        input_info = self._session.get_inputs()[0]
        self._input_name = input_info.name

        # Determina resolução do modelo
        try:
            self._align_size = int(input_info.shape[2])
            if self._align_size <= 0:
                self._align_size = 512
        except (ValueError, TypeError, IndexError):
            self._align_size = 512

        t1 = time.perf_counter()
        logger.info("GFPGAN carregado em %.2fs (input: %s)", t1 - t0, input_info.shape)

        self._model_loaded = True

    # -------------------------------------------------------
    # Enhance de um rosto
    # -------------------------------------------------------
    def enhance_face(self, frame: np.ndarray, face) -> np.ndarray:
        """
        Melhora a qualidade do rosto no frame.

        Args:
            frame: imagem BGR (formato OpenCV).
            face: objeto Face do InsightFace (com kps).

        Returns:
            Frame com o rosto melhorado.
        """
        self._ensure_loaded()

        if not hasattr(face, "kps") or face.kps is None:
            logger.warning("Face sem landmarks — pulando enhance.")
            return frame

        landmarks_5 = face.kps.astype(np.float32)
        if landmarks_5.shape[0] < 5:
            logger.warning("Face com menos de 5 landmarks — pulando.")
            return frame

        # 1. Alinhar rosto
        aligned_face, affine_matrix = self._align_face(
            frame, landmarks_5, self._align_size
        )
        if aligned_face is None:
            return frame

        # 2. Preprocessar
        input_tensor = self._preprocess(aligned_face)

        # 3. Inferência ONNX
        try:
            output = self._session.run(None, {self._input_name: input_tensor})
            enhanced_bgr = self._postprocess(output[0])
        except Exception as e:
            logger.error("Erro na inferência GFPGAN: %s", e)
            return frame

        # 4. Redimensionar se necessário
        eh, ew = enhanced_bgr.shape[:2]
        if eh != self._align_size or ew != self._align_size:
            enhanced_bgr = cv2.resize(
                enhanced_bgr,
                (self._align_size, self._align_size),
                interpolation=cv2.INTER_LANCZOS4,
            )

        # 5. Colar de volta com feathered blending
        result = self._paste_back(
            frame.copy(), enhanced_bgr, affine_matrix, self._align_size
        )
        return result

    # -------------------------------------------------------
    # Alinhamento do rosto
    # -------------------------------------------------------
    def _align_face(
        self,
        frame: np.ndarray,
        landmarks_5: np.ndarray,
        output_size: int,
    ) -> tuple:
        """Alinha e recorta o rosto usando landmarks e template FFHQ."""
        scale = output_size / 512.0
        template = FFHQ_TEMPLATE_512 * scale

        affine_matrix, _ = cv2.estimateAffinePartial2D(
            landmarks_5, template, method=cv2.LMEDS
        )
        if affine_matrix is None:
            return None, None

        aligned_face = cv2.warpAffine(
            frame,
            affine_matrix,
            (output_size, output_size),
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(135, 133, 132),
        )
        return aligned_face, affine_matrix

    # -------------------------------------------------------
    # Pre/Post processamento
    # -------------------------------------------------------
    @staticmethod
    def _preprocess(aligned_face: np.ndarray) -> np.ndarray:
        """BGR uint8 → NCHW float32 [-1, 1]."""
        rgb = aligned_face[:, :, ::-1]  # BGR → RGB (zero-copy view)
        chw = np.transpose(rgb, (2, 0, 1)).astype(np.float32)
        chw *= (1.0 / 127.5)
        chw -= 1.0
        return chw[np.newaxis, ...]  # (1, 3, H, W)

    @staticmethod
    def _postprocess(output: np.ndarray) -> np.ndarray:
        """NCHW float32 [-1, 1] → BGR uint8."""
        face = output[0]  # remove batch dim → (3, H, W)
        face = (face + 1.0) * 127.5
        np.clip(face, 0, 255, out=face)
        face = face.astype(np.uint8).transpose(1, 2, 0)  # CHW → HWC
        return face[:, :, ::-1].copy()  # RGB → BGR

    # -------------------------------------------------------
    # Paste-back com feathered blending
    # -------------------------------------------------------
    def _paste_back(
        self,
        frame: np.ndarray,
        enhanced_face: np.ndarray,
        affine_matrix: np.ndarray,
        output_size: int,
    ) -> np.ndarray:
        """Cola o rosto melhorado de volta no frame com bordas suaves."""
        h, w = frame.shape[:2]
        inv_matrix = cv2.invertAffineTransform(affine_matrix)

        # Máscara com bordas suaves (cached)
        if self._mask_cache["size"] != output_size:
            mask_f = np.ones((output_size, output_size), dtype=np.float32)
            border = max(1, int(output_size * 0.05))
            ramp_up = np.linspace(0.0, 1.0, border, dtype=np.float32)
            ramp_down = np.linspace(1.0, 0.0, border, dtype=np.float32)
            mask_f[:border, :] *= ramp_up[:, None]
            mask_f[-border:, :] *= ramp_down[:, None]
            mask_f[:, :border] *= ramp_up[None, :]
            mask_f[:, -border:] *= ramp_down[None, :]
            self._mask_cache["mask"] = (mask_f * 255.0).astype(np.uint8)
            self._mask_cache["size"] = output_size

        # Bounding box no espaço original
        corners = np.array(
            [[0, 0], [output_size, 0],
             [output_size, output_size], [0, output_size]],
            dtype=np.float32,
        )
        transformed = (inv_matrix[:, :2] @ corners.T).T + inv_matrix[:, 2]
        x1 = max(0, int(np.floor(transformed[:, 0].min())))
        x2 = min(w, int(np.ceil(transformed[:, 0].max())))
        y1 = max(0, int(np.floor(transformed[:, 1].min())))
        y2 = min(h, int(np.ceil(transformed[:, 1].max())))
        if x1 >= x2 or y1 >= y2:
            return frame

        pad = max(1, int(output_size * 0.05)) + 2
        y1p, y2p = max(0, y1 - pad), min(h, y2 + pad)
        x1p, x2p = max(0, x1 - pad), min(w, x2 + pad)
        crop_w, crop_h = x2p - x1p, y2p - y1p

        inv_crop = inv_matrix.copy()
        inv_crop[0, 2] -= x1p
        inv_crop[1, 2] -= y1p

        inv_restored = cv2.warpAffine(
            enhanced_face, inv_crop, (crop_w, crop_h),
            borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0),
        )
        inv_mask = cv2.warpAffine(
            self._mask_cache["mask"], inv_crop, (crop_w, crop_h),
            borderMode=cv2.BORDER_CONSTANT, borderValue=0,
        )

        target_crop = frame[y1p:y2p, x1p:x2p]

        # Blending via cv2 SIMD (rápido em CPU)
        alpha_3c = cv2.merge([inv_mask, inv_mask, inv_mask])
        inv_alpha = 255 - alpha_3c
        a_enh = cv2.multiply(inv_restored, alpha_3c, scale=1.0 / 255.0)
        a_tgt = cv2.multiply(target_crop, inv_alpha, scale=1.0 / 255.0)
        frame[y1p:y2p, x1p:x2p] = cv2.add(a_enh, a_tgt)

        return frame

    # -------------------------------------------------------
    # Propriedades e helpers
    # -------------------------------------------------------
    @property
    def is_loaded(self) -> bool:
        return self._model_loaded

    def _ensure_loaded(self) -> None:
        if not self._model_loaded:
            raise RuntimeError(
                "GFPGAN não carregado. Chame enhancer.load_model() primeiro."
            )
