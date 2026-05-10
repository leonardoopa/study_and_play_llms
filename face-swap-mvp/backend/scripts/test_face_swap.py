"""
scripts/test_face_swap.py — Teste isolado do Face Swap Engine

Uso (dentro do container):
    python scripts/test_face_swap.py

Lê source.png e target.png da pasta scripts/test_images/,
faz o face swap e salva o resultado em scripts/test_images/result.jpg.
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

    # --- 5. Face Swap ---
    t0 = time.perf_counter()
    result = engine.swap_face(source_img, target_img)
    swap_time = time.perf_counter() - t0

    if result is None:
        logger.error("Face swap retornou None!")
        sys.exit(1)

    # --- 6. Salvar resultado ---
    cv2.imwrite(RESULT_PATH, result)
    logger.info("Resultado salvo em: %s", RESULT_PATH)

    # --- 7. Métricas ---
    print()
    print("=" * 50)
    print(" RESULTADO")
    print("=" * 50)
    print(f"  Tempo de carregamento dos modelos: {load_time:.2f}s")
    print(f"  Tempo de inferência (swap):        {swap_time:.3f}s")
    print(f"  Rostos na source:                  {len(source_faces)}")
    print(f"  Rostos na target:                  {len(target_faces)}")
    print(f"  Resultado salvo:                   {RESULT_PATH}")
    print(f"  Dimensões do resultado:            {result.shape}")
    print("=" * 50)
    print(" ✅ Teste concluído com sucesso!")
    print("=" * 50)


if __name__ == "__main__":
    main()
