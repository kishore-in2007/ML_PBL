from __future__ import annotations

import argparse
from pathlib import Path

import torch

from recovery_ai.classification.model import build_classifier


def export_onnx(checkpoint_path: str | Path, output_path: str | Path) -> Path:
    checkpoint_path = Path(checkpoint_path)
    output_path = Path(output_path)
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

    image_size = int(config["data"]["image_size"])
    dummy = torch.randn(1, 3, image_size, image_size)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        dummy,
        output_path,
        input_names=["image"],
        output_names=["risk_logits"],
        dynamic_axes={"image": {0: "batch"}, "risk_logits": {0: "batch"}},
        opset_version=18,
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", default="models/onnx/wound_classifier.onnx")
    args = parser.parse_args()
    output_path = export_onnx(args.checkpoint, args.output)
    print(f"Exported ONNX model to {output_path}")


if __name__ == "__main__":
    main()
