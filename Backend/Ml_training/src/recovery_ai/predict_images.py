from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from PIL import Image

from recovery_ai.classification.data import build_transforms
from recovery_ai.classification.inference import predict_risk
from recovery_ai.classification.model import build_classifier
from recovery_ai.segmentation.area import mask_area_pixels

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def load_checkpoint(checkpoint_path: Path):
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    config = checkpoint["config"]
    class_names = checkpoint["class_names"]
    model = build_classifier(
        model_name=config["model"]["name"],
        num_classes=len(class_names),
        pretrained=False,
        dropout=float(config["model"]["dropout"]),
    )
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model, config, class_names


def simple_red_mask(image: Image.Image) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB")).astype(np.int16)
    r = rgb[:, :, 0]
    g = rgb[:, :, 1]
    b = rgb[:, :, 2]
    return (r > 120) & (r > g * 1.18) & (r > b * 1.18)


def predict_images(
    image_paths: list[Path],
    checkpoint_path: Path,
    onnx_path: Path,
    output_path: Path,
) -> list[dict[str, object]]:
    model, config, class_names = load_checkpoint(checkpoint_path)
    transform = build_transforms(int(config["data"]["image_size"]), training=False)
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    threshold = float(config["inference"]["confidence_threshold"])
    review_label = str(config["inference"]["human_review_label"])

    rows: list[dict[str, object]] = []
    for image_path in image_paths:
        image = Image.open(image_path).convert("RGB")
        tensor = transform(image).unsqueeze(0)
        with torch.no_grad():
            logits = model(tensor)
        probabilities = torch.softmax(logits, dim=1).squeeze(0).tolist()
        onnx_logits = session.run(None, {"image": tensor.numpy()})[0]
        max_onnx_diff = float(np.max(np.abs(logits.numpy() - onnx_logits)))
        prediction = predict_risk(
            logits,
            class_names=class_names,
            confidence_threshold=threshold,
            human_review_label=review_label,
        )[0]

        mask = simple_red_mask(image)
        wound_pixels = mask_area_pixels(mask)
        total_pixels = int(mask.shape[0] * mask.shape[1])
        rows.append(
            {
                "image": str(image_path),
                "image_size": list(image.size),
                "final_label": prediction.label,
                "raw_label": prediction.raw_label,
                "confidence": round(prediction.confidence, 4),
                "routed_to_human": prediction.routed_to_human,
                "class_probabilities": {
                    class_name: round(float(probability), 4)
                    for class_name, probability in zip(class_names, probabilities)
                },
                "simple_red_area_pixels": wound_pixels,
                "simple_red_area_ratio": round(wound_pixels / total_pixels, 4),
                "onnx_max_abs_logit_diff": round(max_onnx_diff, 8),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+", help="Image files or directories containing images.")
    parser.add_argument("--checkpoint", default="models/checkpoints/phase1_final/best.pt")
    parser.add_argument("--onnx", default="models/onnx/wound_classifier_phase1_final.onnx")
    parser.add_argument("--output", default="outputs/user_image_predictions/predictions.json")
    args = parser.parse_args()

    image_paths: list[Path] = []
    for raw_path in args.images:
        path = Path(raw_path)
        if path.is_dir():
            image_paths.extend(
                sorted(
                    child
                    for child in path.rglob("*")
                    if child.is_file() and child.suffix.lower() in IMAGE_EXTENSIONS
                )
            )
        else:
            image_paths.append(path)

    rows = predict_images(
        image_paths=image_paths,
        checkpoint_path=Path(args.checkpoint),
        onnx_path=Path(args.onnx),
        output_path=Path(args.output),
    )
    print(json.dumps(rows, indent=2))
    print(f"report_path={args.output}")


if __name__ == "__main__":
    main()
