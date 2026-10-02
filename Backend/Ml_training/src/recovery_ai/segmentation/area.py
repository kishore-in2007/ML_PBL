from __future__ import annotations

import numpy as np


def mask_area_pixels(mask: np.ndarray) -> int:
    return int(np.count_nonzero(mask))


def pixels_to_cm2(area_pixels: int, marker_area_pixels: int, marker_area_cm2: float) -> float:
    if marker_area_pixels <= 0:
        raise ValueError("marker_area_pixels must be greater than zero")
    pixels_per_cm2 = marker_area_pixels / marker_area_cm2
    return float(area_pixels / pixels_per_cm2)


def percent_area_change(previous_area_cm2: float, current_area_cm2: float) -> float:
    if previous_area_cm2 <= 0:
        raise ValueError("previous_area_cm2 must be greater than zero")
    return float(((current_area_cm2 - previous_area_cm2) / previous_area_cm2) * 100.0)
