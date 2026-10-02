"""
Unified Multi-Task ONNX Inference Engine for VitharaNet.
Executes Scratch-Trained VitharaNet ONNX model for:
  1. Wound Segmentation & Area (cm²)
  2. 3-Tier Severity Classification (Normal, Mild Concern, Urgent)
  3. Infection Risk Assessment (0 - 100%)
"""
import io
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_ONNX_SESSION = None

def get_vitharanet_session():
    global _ONNX_SESSION
    if _ONNX_SESSION is not None:
        return _ONNX_SESSION

    try:
        import onnxruntime as ort
    except ImportError:
        logger.warning("onnxruntime not installed; VitharaNet ONNX unavailable")
        return None

    # Candidate paths for the ONNX file
    candidate_paths = [
        Path("app/ml/vitharanet_scratch.onnx"),
        Path("vitharanet_scratch.onnx"),
        Path("../vitharanet_scratch.onnx"),
        Path("Ml_training/models/onnx/vitharanet_scratch.onnx"),
        Path(__file__).parent / "vitharanet_scratch.onnx",
        Path(__file__).parent.parent.parent / "vitharanet_scratch.onnx",
    ]

    model_path = None
    for p in candidate_paths:
        if p.is_file():
            model_path = p.resolve()
            break

    if model_path is None:
        logger.warning("vitharanet_scratch.onnx model not found in candidate paths")
        return None

    try:
        _ONNX_SESSION = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        logger.info("Loaded VitharaNet ONNX model from %s", model_path)
        return _ONNX_SESSION
    except Exception as exc:
        logger.exception("Failed to initialize VitharaNet ONNX session: %s", exc)
        return None


def preprocess_image(image: Image.Image, size: int = 256) -> np.ndarray:
    resized = image.convert("RGB").resize((size, size))
    arr = np.asarray(resized, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std
    arr = np.transpose(arr, (2, 0, 1))
    return np.expand_dims(arr, axis=0).astype(np.float32)


def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - np.max(x))
    return e / np.sum(e)


def sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


def run_vitharanet_multitask(image_bytes: bytes, previous_area_cm2: Optional[float] = None) -> Optional[Dict[str, Any]]:
    session = get_vitharanet_session()
    if session is None:
        return None

    try:
        orig_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        orig_w, orig_h = orig_image.size

        input_name = session.get_inputs()[0].name
        x = preprocess_image(orig_image, size=256)

        # Execute ONNX graph
        outs = session.run(None, {input_name: x})
        mask_logits = outs[0][0, 0]        # [256, 256]
        severity_logits = outs[1][0]       # [3]
        infection_logits = outs[2][0, 0]   # [1]

        # 1. Severity Probabilities
        probs = softmax(severity_logits)
        class_names = ["Normal", "Mild Concern", "Urgent"]
        raw_scores = {
            "Normal": round(float(probs[0]), 4),
            "Mild Concern": round(float(probs[1]), 4),
            "Urgent": round(float(probs[2]), 4),
        }
        best_idx = int(np.argmax(probs))
        risk_class = class_names[best_idx]
        confidence = round(float(probs[best_idx]), 4)

        # 2. Infection Risk
        infection_risk = round(sigmoid(float(infection_logits)) * 100.0, 1)

        # 3. Mask & Area Extraction
        mask_binary_256 = mask_logits > 0.0
        # Resize mask to original image dimensions using PIL Nearest
        mask_pil = Image.fromarray((mask_binary_256 * 255).astype(np.uint8)).resize((orig_w, orig_h), Image.NEAREST)
        mask_full = np.asarray(mask_pil) > 127

        wound_px = int(np.count_nonzero(mask_full))
        # Standard clinical scale: 40 px/cm
        px_per_cm = 40.0
        wound_area_cm2 = round(wound_px / (px_per_cm ** 2), 2)

        # Area percent change vs previous scan
        percent_change = None
        if previous_area_cm2 and previous_area_cm2 > 0:
            percent_change = round(((wound_area_cm2 - previous_area_cm2) / previous_area_cm2) * 100.0, 1)

        # Generate overlay PNG with red highlight on wound area
        orig_arr = np.asarray(orig_image).copy()
        overlay = orig_arr.copy()
        overlay[mask_full] = (
            overlay[mask_full] * 0.45 + np.array([240, 50, 50]) * 0.55
        ).astype(np.uint8)

        # Save overlay to bytes
        overlay_img = Image.fromarray(overlay)
        buf = io.BytesIO()
        overlay_img.save(buf, format="PNG")
        overlay_png = buf.getvalue()

        return {
            "risk_class": risk_class,
            "confidence": confidence,
            "needs_human_review": confidence < 0.60 or risk_class == "Urgent",
            "raw_scores": raw_scores,
            "infection_risk": infection_risk,
            "wound_area_px": wound_px,
            "wound_area_cm2": wound_area_cm2,
            "percent_change_from_previous": percent_change,
            "model_used": "VitharaNet-Scratch ONNX (SOTA Multi-Task)",
            "model_confidence": confidence,
            "mask_overlay_png": overlay_png,
        }
    except Exception as exc:
        logger.exception("VitharaNet inference execution failed: %s", exc)
        return None
