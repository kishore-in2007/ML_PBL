"""
Wound classification inference wrapper.

Production model: EfficientNetV2-S / DINOv2 fine-tuned on wound datasets,
exported to ONNX (see PS5 spec section 15). This module exposes a stable
`classify_image(image_bytes)` function so the FastAPI layer never has to
change when the real model is dropped in — only `_run_model` changes.
"""
import io
import hashlib
import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict

from PIL import Image

from app.config import settings

LABEL_MAP = {
    "normal": "Normal",
    "mild_concern": "Mild Concern",
    "urgent": "Urgent",
}


def _class_names() -> list[str]:
    return [item.strip() for item in settings.CLASSIFIER_CLASS_NAMES.split(",") if item.strip()]


@lru_cache(maxsize=1)
def _get_onnx_session():
    try:
        import onnxruntime as ort
    except Exception as exc:
        logging.info("ONNX classifier disabled: onnxruntime is unavailable (%s)", exc)
        return None

    model_path = Path(settings.CLASSIFIER_ONNX_PATH)
    if not model_path.is_absolute():
        model_path = Path.cwd() / model_path
    if not model_path.is_file():
        logging.warning("ONNX classifier not found at %s", model_path)
        return None

    try:
        return ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )
    except Exception as exc:
        logging.exception(
            "ONNX classifier could not be loaded from %s; using deterministic fallback: %s",
            model_path,
            exc,
        )
        return None


def _softmax(values):
    import numpy as np

    values = values.astype("float32")
    values = values - np.max(values, axis=1, keepdims=True)
    exp = np.exp(values)
    return exp / np.sum(exp, axis=1, keepdims=True)


def _preprocess_for_onnx(image: Image.Image):
    import numpy as np

    image = image.resize((settings.CLASSIFIER_INPUT_SIZE, settings.CLASSIFIER_INPUT_SIZE))
    array = np.asarray(image).astype("float32") / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype="float32")
    std = np.array([0.229, 0.224, 0.225], dtype="float32")
    array = (array - mean) / std
    array = np.transpose(array, (2, 0, 1))
    return array[None, ...].astype("float32")


def _run_onnx_model(image: Image.Image) -> Dict[str, float] | None:
    session = _get_onnx_session()
    if session is None:
        return None

    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    logits = session.run([output_name], {input_name: _preprocess_for_onnx(image)})[0]
    probabilities = _softmax(logits)[0]

    scores = {}
    for class_name, probability in zip(_class_names(), probabilities.tolist()):
        scores[LABEL_MAP.get(class_name, class_name)] = round(float(probability), 4)
    return scores


def _run_model(image: Image.Image) -> Dict[str, float]:
    """
    Uses the exported Phase 1 ONNX classifier when available. The fallback keeps
    the API testable in lightweight local environments without ML runtimes.
    """
    onnx_scores = _run_onnx_model(image)
    if onnx_scores is not None:
        return onnx_scores

    digest = hashlib.md5(image.tobytes()[:4096]).hexdigest()
    seed = int(digest[:8], 16) / 0xFFFFFFFF  # 0..1

    if seed < 0.6:
        probs = {"Normal": 0.75 + seed * 0.2, "Mild Concern": 0.15, "Urgent": 0.05}
    elif seed < 0.85:
        probs = {"Normal": 0.15, "Mild Concern": 0.65 + seed * 0.1, "Urgent": 0.15}
    else:
        probs = {"Normal": 0.05, "Mild Concern": 0.2, "Urgent": 0.7 + seed * 0.1}

    total = sum(probs.values())
    return {k: round(v / total, 4) for k, v in probs.items()}


def classify_image(image_bytes: bytes) -> dict:
    from app.ml.vitharanet_engine import run_vitharanet_multitask
    vithara_res = run_vitharanet_multitask(image_bytes)
    if vithara_res is not None:
        return {
            "risk_class": vithara_res["risk_class"],
            "confidence": vithara_res["confidence"],
            "needs_human_review": vithara_res["needs_human_review"],
            "raw_scores": vithara_res["raw_scores"],
            "infection_risk": vithara_res["infection_risk"],
        }

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    raw_scores = _run_model(image)

    risk_class = max(raw_scores, key=raw_scores.get)
    confidence = raw_scores[risk_class]
    needs_human_review = confidence < settings.CONFIDENCE_THRESHOLD

    return {
        "risk_class": risk_class,
        "confidence": confidence,
        "needs_human_review": needs_human_review,
        "raw_scores": raw_scores,
    }
