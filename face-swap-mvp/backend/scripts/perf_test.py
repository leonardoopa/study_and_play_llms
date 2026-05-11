import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cv2
import time
from app.services.face_swap_engine import FaceSwapEngine


def main():
    engine = FaceSwapEngine()
    engine.load_models()

    src = cv2.imread("scripts/test_images/source.png")
    tgt = cv2.imread("scripts/test_images/target.png")

    # Warmup
    print("Warmup Swap...")
    engine.swap_face(src, tgt, enhance=False)
    print("Warmup Enhance...")
    engine.swap_face(src, tgt, enhance=True)

    print("Test Swap:")
    t0 = time.perf_counter()
    for _ in range(10):
        engine.swap_face(src, tgt, enhance=False)
    t1 = time.perf_counter()
    print(f"Swap only: {(t1-t0)/10:.4f}s per frame")

    print("Test Enhance:")
    t0 = time.perf_counter()
    for _ in range(10):
        engine.swap_face(src, tgt, enhance=True)
    t1 = time.perf_counter()
    print(f"Swap + Enhance: {(t1-t0)/10:.4f}s per frame")


if __name__ == "__main__":
    main()
