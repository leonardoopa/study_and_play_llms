"""
scripts/test_face_swap.py — Teste isolado do Face Swap Engine

Uso (dentro do container):
    python scripts/test_face_swap.py

Lê source.png e target.png da pasta scripts/test_images/,
faz o face swap (com e sem enhance) e salva os resultados.
"""

import logging
import os
import sys
import time

# Adiciona o diretório raiz ao path para importar o package app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2

from app.services.face_swap_engine import FaceSwapEngine

# -------------------------------------------------------
# Config
# -------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("test_face_swap")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_IMAGES_DIR = os.path.join(SCRIPT_DIR, "test_images")

SOURCE_PATH = os.path.join(TEST_IMAGES_DIR, "source.png")
TARGET_PATH = os.path.join(TEST_IMAGES_DIR, "target.png")
RESULT_PATH = os.path.join(TEST_IMAGES_DIR, "result.jpg")
RESULT_ENHANCED_PATH = os.path.join(TEST_IMAGES_DIR, "result_enhanced.jpg")


def main() -> None:
    print("=" * 50)
    print(" Face Swap Engine — Teste Estático")
    print("=" * 50)

    # --- 1. Verificar imagens ---
    for path, label in [(SOURCE_PATH, "Source"), (TARGET_PATH, "Target")]:
        if not os.path.isfile(path):
            logger.error("Imagem %s não encontrada: %s", label, path)
            sys.exit(1)
        logger.info("%s: %s", label, path)

    # --- 2. Carregar imagens ---
    source_img = cv2.imread(SOURCE_PATH)
    target_img = cv2.imread(TARGET_PATH)

    if source_img is None:
        logger.error("Falha ao ler imagem source: %s", SOURCE_PATH)
        sys.exit(1)
    if target_img is None:
        logger.error("Falha ao ler imagem target: %s", TARGET_PATH)
        sys.exit(1)

    logger.info(
        "Imagens carregadas — Source: %s, Target: %s",
        source_img.shape,
        target_img.shape,
    )

    # --- 3. Inicializar engine ---
    engine = FaceSwapEngine()

    t0 = time.perf_counter()
    engine.load_models()
    load_time = time.perf_counter() - t0

    # --- 4. Detectar rostos ---
    source_faces = engine.detect_faces(source_img)
    target_faces = engine.detect_faces(target_img)

    logger.info("Rostos detectados — Source: %d, Target: %d",
                len(source_faces), len(target_faces))

    if not source_faces:
        logger.error("Nenhum rosto detectado na imagem source!")
        sys.exit(1)
    if not target_faces:
        logger.error("Nenhum rosto detectado na imagem target!")
        sys.exit(1)

    # --- 5. Face Swap (sem enhance) ---
    t0 = time.perf_counter()
    result = engine.swap_face(source_img, target_img, enhance=False)
    swap_time = time.perf_counter() - t0

    if result is None:
        logger.error("Face swap retornou None!")
        sys.exit(1)

    cv2.imwrite(RESULT_PATH, result)
    logger.info("Resultado (sem enhance) salvo em: %s", RESULT_PATH)

    # --- 6. Face Swap (com enhance / GFPGAN) ---
    enhance_time = 0.0
    if engine.has_enhancer:
        t0 = time.perf_counter()
        result_enhanced = engine.swap_face(source_img, target_img, enhance=True)
        enhance_time = time.perf_counter() - t0

        if result_enhanced is not None:
            cv2.imwrite(RESULT_ENHANCED_PATH, result_enhanced)
            logger.info("Resultado (com GFPGAN) salvo em: %s", RESULT_ENHANCED_PATH)
        else:
            logger.warning("Face swap com enhance retornou None!")
    else:
        logger.warning("GFPGAN não disponível — pulando teste com enhance.")

    # --- 7. Métricas ---
    print()
    print("=" * 55)
    print(" RESULTADO")
    print("=" * 55)
    print(f"  Carregamento dos modelos:    {load_time:.2f}s")
    print(f"  Swap (sem enhance):          {swap_time:.3f}s")
    if engine.has_enhancer:
        print(f"  Swap + GFPGAN enhance:       {enhance_time:.3f}s")
    print(f"  Rostos na source:            {len(source_faces)}")
    print(f"  Rostos na target:            {len(target_faces)}")
    print(f"  GFPGAN disponível:           {'✅' if engine.has_enhancer else '❌'}")
    print(f"  Resultado salvo:             {RESULT_PATH}")
    if engine.has_enhancer:
        print(f"  Resultado enhanced salvo:    {RESULT_ENHANCED_PATH}")
    print("=" * 55)
    print(" ✅ Teste concluído com sucesso!")
    print("=" * 55)


if __name__ == "__main__":
    main()
