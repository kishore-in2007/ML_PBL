from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from PIL import Image


def prepare_manifest(raw_dir: Path, output_dir: Path) -> Path:
    image_dir = raw_dir / "DFUC2022_train_images"
    mask_dir = raw_dir / "DFUC2022_train_masks"
    if not image_dir.exists():
        raise FileNotFoundError(f"Missing image directory: {image_dir}")
    if not mask_dir.exists():
        raise FileNotFoundError(f"Missing mask directory: {mask_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for image_path in sorted(image_dir.glob("*.jpg")):
        mask_path = mask_dir / f"{image_path.stem}.png"
        if not mask_path.exists():
            continue
        with Image.open(image_path) as image, Image.open(mask_path) as mask:
            rows.append(
                {
                    "image": str(image_path),
                    "mask": str(mask_path),
                    "image_width": image.width,
                    "image_height": image.height,
                    "mask_width": mask.width,
                    "mask_height": mask.height,
                    "source": "DFUC2022_train_release",
                }
            )

    manifest_path = output_dir / "manifest.csv"
    pd.DataFrame(rows).to_csv(manifest_path, index=False)
    print(f"Paired {len(rows)} image/mask examples")
    print(f"Manifest: {manifest_path}")
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir",
        default="data/raw/DFUC2022_train_release",
        help="Folder containing DFUC2022_train_images and DFUC2022_train_masks.",
    )
    parser.add_argument("--output-dir", default="data/processed/segmentation/dfuc2022")
    args = parser.parse_args()
    prepare_manifest(Path(args.raw_dir), Path(args.output_dir))


if __name__ == "__main__":
    main()
