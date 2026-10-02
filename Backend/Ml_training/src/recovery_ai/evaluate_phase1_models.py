from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image, ImageDraw, ImageFilter
from sklearn.metrics import classification_report, confusion_matrix

from recovery_ai.classification.data import build_dataloaders, build_transforms
from recovery_ai.classification.inference import predict_risk
from recovery_ai.classification.model import build_classifier
from recovery_ai.config import load_config
from recovery_ai.segmentation.area import mask_area_pixels


def generate_synthetic_images(output_dir: Path) -> list[dict[str, str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        ("normal_01.png", "normal", "#d7a185", "#b97162", 28, 0.65),
        ("normal_02.png", "normal", "#c98f76", "#aa5e55", 34, 0.55),
        ("normal_03.png", "normal", "#e0ad8f", "#bf7162", 25, 0.5),
        ("medium_01.png", "mild_concern", "#d7a185", "#a9433b", 54, 0.75),
        ("medium_02.png", "mild_concern", "#c99277", "#92332f", 64, 0.65),
        ("medium_03.png", "mild_concern", "#e1b191", "#9f4038", 58, 0.85),
        ("urgent_01.png", "urgent", "#d4a084", "#6d1f27", 86, 1.0),
        ("urgent_02.png", "urgent", "#c98e72", "#5f1923", 94, 1.0),
        ("urgent_03.png", "urgent", "#dfae90", "#711c22", 82, 0.95),
    ]

    rows: list[dict[str, str]] = []
    for filename, expected, skin, wound, radius, redness in specs:
        image = Image.new("RGB", (384, 384), skin)
        draw = ImageDraw.Draw(image)

        # Soft surrounding redness.
        red_alpha = int(60 + redness * 90)
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        cx, cy = 192, 196
        odraw.ellipse(
            (cx - radius * 1.7, cy - radius * 1.25, cx + radius * 1.7, cy + radius * 1.25),
            fill=(178, 46, 38, red_alpha),
        )
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=14))
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(image)

        # Main wound body plus a darker center. This is synthetic and intentionally non-graphic.
        draw.ellipse(
            (cx - radius, cy - int(radius * 0.62), cx + radius, cy + int(radius * 0.62)),
            fill=wound,
        )
        draw.ellipse(
            (
                cx - int(radius * 0.42),
                cy - int(radius * 0.25),
                cx + int(radius * 0.45),
                cy + int(radius * 0.28),
            ),
            fill="#4e2024" if expected == "urgent" else "#7a3d38",
        )
        draw.arc(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            start=20,
            end=160,
            fill="#f0c2a1",
            width=3,
        )

        output_path = output_dir / filename
        image.save(output_path)
        rows.append({"image": str(output_path), "expected_label": expected})
    return rows


def load_checkpoint(checkpoint_path: Path) -> tuple[nn.Module, dict[str, object], list[str]]:
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


def evaluate_validation(checkpoint_path: Path) -> dict[str, float]:
    model, config, class_names = load_checkpoint(checkpoint_path)
    _, val_loader, _ = build_dataloaders(
        data_root=config["data"]["root"],
        image_size=int(config["data"]["image_size"]),
        batch_size=int(config["data"]["batch_size"]),
        num_workers=0,
        val_split=float(config["data"]["val_split"]),
        seed=int(config["seed"]),
    )
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    correct = 0
    total = 0
    all_targets: list[int] = []
    all_predictions: list[int] = []
    with torch.no_grad():
        for images, targets in val_loader:
            logits = model(images)
            loss = criterion(logits, targets)
            predictions = logits.argmax(dim=1)
            total_loss += float(loss.item()) * int(targets.numel())
            correct += int((predictions == targets).sum().item())
            total += int(targets.numel())
            all_targets.extend(targets.tolist())
            all_predictions.extend(predictions.tolist())
    report = classification_report(
        all_targets,
        all_predictions,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(all_targets, all_predictions, labels=list(range(len(class_names))))
    return {
        "validation_loss": total_loss / total,
        "validation_accuracy": correct / total,
        "validation_samples": float(total),
        "macro_f1": report["macro avg"]["f1-score"],
        "weighted_f1": report["weighted avg"]["f1-score"],
        "per_class": {
            class_name: {
                "precision": report[class_name]["precision"],
                "recall": report[class_name]["recall"],
                "f1": report[class_name]["f1-score"],
                "support": report[class_name]["support"],
            }
            for class_name in class_names
        },
        "confusion_matrix": matrix.tolist(),
    }


def predict_generated(
    checkpoint_path: Path,
    onnx_path: Path,
    generated_rows: list[dict[str, str]],
) -> tuple[list[dict[str, object]], float]:
    model, config, class_names = load_checkpoint(checkpoint_path)
    transform = build_transforms(int(config["data"]["image_size"]), training=False)
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])

    rows: list[dict[str, object]] = []
    max_onnx_diff = 0.0
    for row in generated_rows:
        image = Image.open(row["image"]).convert("RGB")
        tensor = transform(image).unsqueeze(0)
        with torch.no_grad():
            logits = model(tensor)
        ort_logits = session.run(None, {"image": tensor.numpy()})[0]
        max_onnx_diff = max(max_onnx_diff, float(np.max(np.abs(logits.numpy() - ort_logits))))

        prediction = predict_risk(
            logits,
            class_names=class_names,
            confidence_threshold=float(config["inference"]["confidence_threshold"]),
            human_review_label=str(config["inference"]["human_review_label"]),
        )[0]
        rows.append(
            {
                "image": row["image"],
                "expected_label": row["expected_label"],
                "predicted_label": prediction.label,
                "raw_label": prediction.raw_label,
                "confidence": round(prediction.confidence, 4),
                "routed_to_human": prediction.routed_to_human,
                "expected_match_raw": prediction.raw_label == row["expected_label"],
            }
        )
    return rows, max_onnx_diff


def segmentation_specs(manifest_path: Path, sample_count: int = 25) -> dict[str, object]:
    manifest = pd.read_csv(manifest_path)
    subset = manifest.head(sample_count)
    area_ratios: list[float] = []
    for _, row in subset.iterrows():
        with Image.open(row["mask"]) as mask_image:
            mask = np.array(mask_image)
        area = mask_area_pixels(mask)
        area_ratios.append(area / float(mask.shape[0] * mask.shape[1]))

    return {
        "segmentation_pairs": int(len(manifest)),
        "sampled_masks": int(len(area_ratios)),
        "mean_mask_area_ratio": round(float(np.mean(area_ratios)), 4),
        "min_mask_area_ratio": round(float(np.min(area_ratios)), 4),
        "max_mask_area_ratio": round(float(np.max(area_ratios)), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default="models/checkpoints/phase1_final/best.pt")
    parser.add_argument("--onnx", default="models/onnx/wound_classifier_phase1_final.onnx")
    parser.add_argument("--segmentation-manifest", default="data/processed/segmentation/dfuc2022/manifest.csv")
    parser.add_argument("--output-dir", default="outputs/phase1_model_test")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    generated_rows = generate_synthetic_images(output_dir / "generated_images")
    validation = evaluate_validation(Path(args.checkpoint))
    generated_predictions, max_onnx_diff = predict_generated(
        Path(args.checkpoint),
        Path(args.onnx),
        generated_rows,
    )
    synthetic_matches = sum(1 for row in generated_predictions if row["expected_match_raw"])
    segmentation = segmentation_specs(Path(args.segmentation_manifest))

    report = {
        "model": {
            "checkpoint": args.checkpoint,
            "onnx": args.onnx,
            "classes": ["mild_concern", "normal", "urgent"],
            "input_size": "1x3x224x224",
            "output": "risk_logits",
        },
        "validation": validation,
        "synthetic_generated_test": {
            "images": len(generated_predictions),
            "raw_label_agreement": synthetic_matches / len(generated_predictions),
            "note": "Synthetic images are pipeline tests, not medical accuracy evidence.",
            "predictions": generated_predictions,
        },
        "onnx_consistency": {
            "max_abs_logit_difference_vs_pytorch": round(max_onnx_diff, 8),
        },
        "segmentation": segmentation,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "phase1_model_test_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"report_path={report_path}")


if __name__ == "__main__":
    main()
