from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def label_color(label: str) -> tuple[int, int, int]:
    if label == "urgent":
        return (180, 30, 35)
    if label == "needs_clinician_review":
        return (205, 130, 20)
    if label == "normal":
        return (35, 130, 80)
    return (45, 90, 180)


def render_prediction_images(report_path: Path, output_dir: Path) -> list[Path]:
    rows = json.loads(report_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    font_title = _load_font(22)
    font_body = _load_font(17)
    saved: list[Path] = []

    for row in rows:
        image_path = Path(row["image"])
        image = Image.open(image_path).convert("RGB")
        canvas = Image.new("RGB", (image.width, image.height + 118), (245, 247, 250))
        canvas.paste(image, (0, 0))
        draw = ImageDraw.Draw(canvas)

        final_label = str(row["final_label"])
        raw_label = str(row["raw_label"])
        confidence = float(row["confidence"])
        urgent_prob = float(row["class_probabilities"]["urgent"])
        area_ratio = float(row["simple_red_area_ratio"])

        color = label_color(final_label)
        y0 = image.height
        draw.rectangle((0, y0, image.width, image.height + 118), fill=(245, 247, 250))
        draw.rectangle((0, y0, image.width, y0 + 8), fill=color)
        draw.text((16, y0 + 18), f"Prediction: {final_label}", fill=color, font=font_title)
        draw.text(
            (16, y0 + 50),
            f"Raw: {raw_label} | Confidence: {confidence:.2%} | Urgent prob: {urgent_prob:.2%}",
            fill=(30, 36, 44),
            font=font_body,
        )
        draw.text(
            (16, y0 + 78),
            f"Simple red-area ratio: {area_ratio:.2%} | MVP triage output, not clinical diagnosis",
            fill=(70, 76, 84),
            font=font_body,
        )

        output_path = output_dir / f"{image_path.stem}_prediction.jpg"
        canvas.save(output_path, quality=92)
        saved.append(output_path)
    return saved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="outputs/user_image_predictions/downloaded_images_predictions.json")
    parser.add_argument("--output-dir", default="outputs/user_image_predictions/annotated_images")
    args = parser.parse_args()

    saved = render_prediction_images(Path(args.report), Path(args.output_dir))
    print(f"saved_count={len(saved)}")
    print(f"output_dir={args.output_dir}")
    for path in saved:
        print(path)


if __name__ == "__main__":
    main()
