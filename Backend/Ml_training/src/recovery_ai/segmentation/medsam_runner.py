from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from recovery_ai.segmentation.area import mask_area_pixels, percent_area_change, pixels_to_cm2


@dataclass(frozen=True)
class SegmentationResult:
    mask: np.ndarray
    wound_area_pixels: int
    wound_area_cm2: float | None = None
    area_change_percent: float | None = None


class MedSAMSegmenter:
    """Thin adapter for MedSAM.

    The actual MedSAM checkpoint is intentionally not bundled. Once the checkpoint is
    downloaded and license-reviewed, wire the model object into `predict_mask`.
    """

    def __init__(self, checkpoint_path: str | Path | None = None) -> None:
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        self.model = None

    def load(self) -> None:
        raise NotImplementedError(
            "Install and load bowang-lab/MedSAM here after the checkpoint is available."
        )

    def predict_mask(
        self,
        image_bgr: np.ndarray,
        box_xyxy: tuple[int, int, int, int] | None = None,
        point_xy: tuple[int, int] | None = None,
    ) -> np.ndarray:
        if self.model is None:
            return classical_fallback_mask(image_bgr, box_xyxy=box_xyxy, point_xy=point_xy)
        raise NotImplementedError("Connect MedSAM model inference here.")

    def segment(
        self,
        image_bgr: np.ndarray,
        box_xyxy: tuple[int, int, int, int] | None = None,
        point_xy: tuple[int, int] | None = None,
        marker_area_pixels: int | None = None,
        marker_area_cm2: float | None = None,
        previous_area_cm2: float | None = None,
    ) -> SegmentationResult:
        mask = self.predict_mask(image_bgr, box_xyxy=box_xyxy, point_xy=point_xy)
        area_px = mask_area_pixels(mask)

        area_cm2 = None
        change = None
        if marker_area_pixels is not None and marker_area_cm2 is not None:
            area_cm2 = pixels_to_cm2(area_px, marker_area_pixels, marker_area_cm2)
            if previous_area_cm2 is not None:
                change = percent_area_change(previous_area_cm2, area_cm2)

        return SegmentationResult(
            mask=mask,
            wound_area_pixels=area_px,
            wound_area_cm2=area_cm2,
            area_change_percent=change,
        )


def classical_fallback_mask(
    image_bgr: np.ndarray,
    box_xyxy: tuple[int, int, int, int] | None = None,
    point_xy: tuple[int, int] | None = None,
) -> np.ndarray:
    """Non-clinical fallback for pipeline testing before MedSAM is wired in."""
    image = image_bgr.copy()
    if box_xyxy is not None:
        x1, y1, x2, y2 = box_xyxy
        roi = image[y1:y2, x1:x2]
    else:
        x1, y1 = 0, 0
        roi = image

    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
    a_channel = lab[:, :, 1]
    _, local_mask = cv2.threshold(a_channel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((5, 5), dtype=np.uint8)
    local_mask = cv2.morphologyEx(local_mask, cv2.MORPH_OPEN, kernel)
    local_mask = cv2.morphologyEx(local_mask, cv2.MORPH_CLOSE, kernel)

    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    h, w = local_mask.shape
    mask[y1 : y1 + h, x1 : x1 + w] = local_mask

    if point_xy is not None and mask[point_xy[1], point_xy[0]] == 0:
        mask = cv2.bitwise_not(mask)
    return mask > 0
