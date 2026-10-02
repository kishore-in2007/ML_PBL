"""
Wound segmentation / area-measurement wrapper.

The primary path uses the local MedSAM/SAM ViT-B checkpoint. A small automatic
prompt generator proposes a wound bounding box from color/contrast cues, then
MedSAM refines that box into a binary mask. A classical CV fallback remains so
the API does not crash if the model runtime is unavailable.
"""
import io
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from PIL import Image

from app.config import settings


def _image_to_rgb_array(image: Image.Image):
    import numpy as np

    return np.asarray(image.convert("RGB"))


def _auto_wound_box(image_rgb) -> tuple[int, int, int, int]:
    import cv2
    import numpy as np

    h, w = image_rgb.shape[:2]
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

    rgb_float = image_rgb.astype("float32")
    median_rgb = np.median(rgb_float.reshape(-1, 3), axis=0)
    color_distance = np.linalg.norm(rgb_float - median_rgb, axis=2)
    saturation = hsv[:, :, 1].astype("float32")
    value = hsv[:, :, 2].astype("float32")
    median_value = float(np.median(value))
    red_excess = image_rgb[:, :, 0].astype("int16") - image_rgb[:, :, 1].astype("int16")

    mask = (
        (color_distance > max(22.0, float(np.std(color_distance)) * 1.2))
        & (saturation > max(25.0, float(np.median(saturation)) + 8.0))
        & ((red_excess > 10) | (value < median_value - 12.0))
    ).astype("uint8") * 255

    kernel_size = max(3, min(h, w) // 80)
    if kernel_size % 2 == 0:
        kernel_size += 1
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    min_area = max(32, h * w * 0.001)
    candidates = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_area]
    if not candidates:
        pad_w, pad_h = int(w * 0.2), int(h * 0.2)
        return pad_w, pad_h, w - pad_w, h - pad_h

    contour = max(candidates, key=cv2.contourArea)
    x, y, bw, bh = cv2.boundingRect(contour)
    pad = max(8, int(max(bw, bh) * 0.25))
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(w - 1, x + bw + pad)
    y2 = min(h - 1, y + bh + pad)
    if x2 <= x1 or y2 <= y1:
        return 0, 0, w - 1, h - 1
    return x1, y1, x2, y2


def _classical_mask(image_rgb, box_xyxy: tuple[int, int, int, int]):
    import cv2
    import numpy as np

    h, w = image_rgb.shape[:2]
    x1, y1, x2, y2 = box_xyxy
    roi = image_rgb[y1:y2, x1:x2]
    if roi.size == 0:
        return np.zeros((h, w), dtype=bool)

    roi_bgr = cv2.cvtColor(roi, cv2.COLOR_RGB2BGR)
    lab = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2LAB)
    a_channel = lab[:, :, 1]
    _, local_mask = cv2.threshold(a_channel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((5, 5), dtype=np.uint8)
    local_mask = cv2.morphologyEx(local_mask, cv2.MORPH_OPEN, kernel)
    local_mask = cv2.morphologyEx(local_mask, cv2.MORPH_CLOSE, kernel)

    mask = np.zeros((h, w), dtype=np.uint8)
    mask[y1:y2, x1:x2] = local_mask[: y2 - y1, : x2 - x1]
    return mask > 0


def _fallback_without_cv2(image: Image.Image, previous_area_cm2: Optional[float] = None) -> dict:
    import numpy as np

    image_rgb = _image_to_rgb_array(image)
    h, w = image_rgb.shape[:2]
    rgb_float = image_rgb.astype("float32")
    median_rgb = np.median(rgb_float.reshape(-1, 3), axis=0)
    color_distance = np.linalg.norm(rgb_float - median_rgb, axis=2)
    threshold = max(20.0, float(np.percentile(color_distance, 78)))
    mask = color_distance > threshold

    if int(np.count_nonzero(mask)) < max(32, int(h * w * 0.001)):
        y1, y2 = int(h * 0.25), int(h * 0.75)
        x1, x2 = int(w * 0.25), int(w * 0.75)
        mask = np.zeros((h, w), dtype=bool)
        mask[y1:y2, x1:x2] = True
    else:
        ys, xs = np.where(mask)
        x1, x2 = int(xs.min()), int(xs.max())
        y1, y2 = int(ys.min()), int(ys.max())

    area_px = float(np.count_nonzero(mask))
    px_per_cm = float(settings.SEGMENTATION_PX_PER_CM)
    area_cm2 = round(area_px / (px_per_cm ** 2), 3)
    percent_change = None
    if previous_area_cm2 and previous_area_cm2 > 0:
        percent_change = round(((area_cm2 - previous_area_cm2) / previous_area_cm2) * 100, 2)

    overlay = image_rgb.copy()
    red = np.zeros_like(overlay)
    red[:, :, 0] = 255
    overlay = np.where(mask[:, :, None], (overlay * 0.55 + red * 0.45).astype("uint8"), overlay)
    overlay_image = Image.fromarray(overlay)
    out = io.BytesIO()
    overlay_image.save(out, format="PNG")

    return {
        "wound_area_px": round(area_px, 2),
        "wound_area_cm2": area_cm2,
        "percent_change_from_previous": percent_change,
        "model_used": "pil_numpy_fallback",
        "model_confidence": None,
        "prompt_box_xyxy": [x1, y1, x2, y2],
        "mask_overlay_png": out.getvalue(),
    }


@lru_cache(maxsize=1)
def _get_medsam_predictor():
    if settings.SEGMENTATION_BACKEND.lower() != "medsam":
        return None

    try:
        import torch
        from segment_anything import SamPredictor, sam_model_registry
    except Exception as exc:
        logging.warning("MedSAM disabled because runtime import failed: %s", exc)
        return None

    checkpoint_path = Path(settings.MEDSAM_CHECKPOINT_PATH)
    if not checkpoint_path.is_absolute():
        checkpoint_path = Path.cwd() / checkpoint_path
    if not checkpoint_path.is_file():
        logging.warning("MedSAM checkpoint not found at %s", checkpoint_path)
        return None

    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        sam = sam_model_registry["vit_b"](checkpoint=None)
        state_dict = torch.load(str(checkpoint_path), map_location=device)
        if isinstance(state_dict, dict) and "model" in state_dict:
            state_dict = state_dict["model"]
        elif isinstance(state_dict, dict) and "state_dict" in state_dict:
            state_dict = state_dict["state_dict"]
        sam.load_state_dict(state_dict, strict=True)
        sam.to(device=device)
        sam.eval()
        logging.info("MedSAM loaded from %s on %s", checkpoint_path, device)
        return SamPredictor(sam)
    except Exception as exc:
        logging.exception("MedSAM checkpoint load failed: %s", exc)
        return None


def _run_medsam(image_rgb, box_xyxy: tuple[int, int, int, int]):
    import numpy as np

    predictor = _get_medsam_predictor()
    if predictor is None:
        return None

    predictor.set_image(image_rgb)
    masks, scores, _ = predictor.predict(
        box=np.array(box_xyxy, dtype=np.float32),
        multimask_output=True,
    )
    if masks is None or len(masks) == 0:
        return None
    best_index = int(np.argmax(scores))
    return masks[best_index].astype(bool), float(scores[best_index])


def segment_image(
    image_bytes: bytes,
    reference_marker_cm: float = 2.0,
    previous_area_cm2: Optional[float] = None,
) -> dict:
    from app.ml.vitharanet_engine import run_vitharanet_multitask
    vithara_res = run_vitharanet_multitask(image_bytes, previous_area_cm2=previous_area_cm2)
    if vithara_res is not None and vithara_res.get("mask_overlay_png"):
        return {
            "wound_area_px": vithara_res["wound_area_px"],
            "wound_area_cm2": vithara_res["wound_area_cm2"],
            "percent_change_from_previous": vithara_res["percent_change_from_previous"],
            "model_used": vithara_res["model_used"],
            "model_confidence": vithara_res["model_confidence"],
            "prompt_box_xyxy": [10, 10, 240, 240],
            "mask_overlay_png": vithara_res["mask_overlay_png"],
        }

    import numpy as np

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    try:
        import cv2
    except ModuleNotFoundError as exc:
        logging.warning("OpenCV unavailable; using PIL/NumPy segmentation fallback: %s", exc)
        return _fallback_without_cv2(image, previous_area_cm2=previous_area_cm2)

    image_rgb = _image_to_rgb_array(image)
    box_xyxy = _auto_wound_box(image_rgb)

    model_used = "medsam"
    confidence = None
    medsam_result = _run_medsam(image_rgb, box_xyxy)
    if medsam_result is None:
        model_used = "classical_fallback"
        mask = _classical_mask(image_rgb, box_xyxy)
    else:
        mask, confidence = medsam_result

    area_px = float(np.count_nonzero(mask))

    # MVP calibration: marker detection is a separate CV step; until it is added,
    # use a configurable pixel/cm ratio while preserving the reference-marker API.
    px_per_cm = float(settings.SEGMENTATION_PX_PER_CM)
    area_cm2 = round(area_px / (px_per_cm ** 2), 3)

    percent_change = None
    if previous_area_cm2 and previous_area_cm2 > 0:
        percent_change = round(((area_cm2 - previous_area_cm2) / previous_area_cm2) * 100, 2)

    overlay = image_rgb.copy()
    red = np.zeros_like(overlay)
    red[:, :, 0] = 255
    overlay = np.where(mask[:, :, None], (overlay * 0.55 + red * 0.45).astype("uint8"), overlay)
    x1, y1, x2, y2 = box_xyxy
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (255, 255, 255), 2)
    ok, encoded_overlay = cv2.imencode(".png", cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
    overlay_png = encoded_overlay.tobytes() if ok else None

    return {
        "wound_area_px": round(area_px, 2),
        "wound_area_cm2": area_cm2,
        "percent_change_from_previous": percent_change,
        "model_used": model_used,
        "model_confidence": confidence,
        "prompt_box_xyxy": list(box_xyxy),
        "mask_overlay_png": overlay_png,
    }
