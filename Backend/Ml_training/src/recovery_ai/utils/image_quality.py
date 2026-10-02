from __future__ import annotations

import cv2
import numpy as np


def blur_score(image_bgr: np.ndarray) -> float:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def brightness_score(image_bgr: np.ndarray) -> float:
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    return float(np.mean(hsv[:, :, 2]))


def passes_quality_checks(
    image_bgr: np.ndarray,
    min_blur_score: float = 80.0,
    min_brightness: float = 45.0,
) -> tuple[bool, dict[str, float]]:
    scores = {
        "blur": blur_score(image_bgr),
        "brightness": brightness_score(image_bgr),
    }
    passed = scores["blur"] >= min_blur_score and scores["brightness"] >= min_brightness
    return passed, scores
