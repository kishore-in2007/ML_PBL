from __future__ import annotations

import argparse
from pathlib import Path

import onnxruntime as ort
import pandas as pd
import torch
from PIL import Image


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing required file: {path}")


def _require_dir(path: Path) -> None:
    if not path.is_dir():
        raise FileNotFoundError(f"Missing required directory: {path}")


def verify_phase1(
    checkpoint_path: Path,
    onnx_path: Path,
    classification_root: Path,
    segmentation_manifest: Path,
    medsam_path: Path,
) -> None:
    _require_file(checkpoint_path)
    _require_file(onnx_path)
    _require_dir(classification_root)
    _require_file(segmentation_manifest)
    _require_file(medsam_path)

    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    class_names = checkpoint["class_names"]
    print(f"classifier_checkpoint={checkpoint_path}")
    print(f"classifier_classes={class_names}")
    print(f"val_loss={checkpoint.get('val_loss'):.4f}")
    print(f"val_accuracy={checkpoint.get('val_accuracy'):.4f}")

    class_counts = {
        class_dir.name: len(list(class_dir.glob("*.*")))
        for class_dir in sorted(classification_root.iterdir())
        if class_dir.is_dir()
    }
    print(f"classification_images={class_counts}")

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    print(f"onnx_inputs={[input_.name for input_ in session.get_inputs()]}")
    print(f"onnx_outputs={[output.name for output in session.get_outputs()]}")

    segmentation = pd.read_csv(segmentation_manifest)
    if segmentation.empty:
        raise ValueError("Segmentation manifest is empty")
    first = segmentation.iloc[0]
    with Image.open(first["image"]) as image, Image.open(first["mask"]) as mask:
        print(f"segmentation_pairs={len(segmentation)}")
        print(f"sample_image_size={image.size}")
        print(f"sample_mask_size={mask.size}")

    print(f"medsam_checkpoint={medsam_path}")
    print("phase1_status=ready_for_hackathon_mvp")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default="models/checkpoints/mvp/best.pt")
    parser.add_argument("--onnx", default="models/onnx/wound_classifier_mvp.onnx")
    parser.add_argument("--classification-root", default="data/processed/classification")
    parser.add_argument("--segmentation-manifest", default="data/processed/segmentation/dfuc2022/manifest.csv")
    parser.add_argument("--medsam", default="models/medsam/medsam_vit_b.pth")
    args = parser.parse_args()

    verify_phase1(
        checkpoint_path=Path(args.checkpoint),
        onnx_path=Path(args.onnx),
        classification_root=Path(args.classification_root),
        segmentation_manifest=Path(args.segmentation_manifest),
        medsam_path=Path(args.medsam),
    )


if __name__ == "__main__":
    main()
