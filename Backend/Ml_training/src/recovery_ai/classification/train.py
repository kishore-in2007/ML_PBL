from __future__ import annotations

import argparse
from pathlib import Path

import torch
import torch.nn as nn
from torch.optim import AdamW
from tqdm import tqdm

from recovery_ai.classification.data import build_dataloaders
from recovery_ai.classification.model import build_classifier
from recovery_ai.config import load_config
from recovery_ai.utils.metrics import ClassificationMetrics, accuracy_from_logits
from recovery_ai.utils.seed import seed_everything


def run_epoch(
    model: nn.Module,
    loader: torch.utils.data.DataLoader,
    criterion: nn.Module,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None = None,
    use_amp: bool = False,
) -> ClassificationMetrics:
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    total_acc = 0.0
    batches = 0
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp and device.type == "cuda")

    for images, targets in tqdm(loader, leave=False):
        images = images.to(device)
        targets = targets.to(device)

        with torch.set_grad_enabled(training):
            with torch.amp.autocast("cuda", enabled=use_amp and device.type == "cuda"):
                logits = model(images)
                loss = criterion(logits, targets)

            if training:
                optimizer.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()

        total_loss += loss.item()
        total_acc += accuracy_from_logits(logits.detach(), targets)
        batches += 1

    return ClassificationMetrics(loss=total_loss / batches, accuracy=total_acc / batches)


def train(config_path: str) -> Path:
    config = load_config(config_path)
    raw = config.raw
    seed_everything(int(raw["seed"]))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader, val_loader, class_names = build_dataloaders(
        data_root=raw["data"]["root"],
        image_size=int(raw["data"]["image_size"]),
        batch_size=int(raw["data"]["batch_size"]),
        num_workers=int(raw["data"]["num_workers"]),
        val_split=float(raw["data"]["val_split"]),
        seed=int(raw["seed"]),
    )

    expected_classes = raw["data"]["classes"]
    if set(class_names) != set(expected_classes):
        raise ValueError(f"Dataset classes {class_names} do not match config classes {expected_classes}")
    if class_names != expected_classes:
        print(f"Using ImageFolder class order: {class_names}")

    model = build_classifier(
        model_name=raw["model"]["name"],
        num_classes=len(class_names),
        pretrained=bool(raw["model"]["pretrained"]),
        dropout=float(raw["model"]["dropout"]),
    ).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = AdamW(
        model.parameters(),
        lr=float(raw["training"]["learning_rate"]),
        weight_decay=float(raw["training"]["weight_decay"]),
    )

    output_dir = Path(raw["training"]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    best_path = output_dir / "best.pt"
    best_val_loss = float("inf")
    patience = int(raw["training"]["patience"])
    stale_epochs = 0

    for epoch in range(1, int(raw["training"]["epochs"]) + 1):
        print(f"Epoch {epoch}")
        train_metrics = run_epoch(
            model,
            train_loader,
            criterion,
            device,
            optimizer=optimizer,
            use_amp=bool(raw["training"]["mixed_precision"]),
        )
        val_metrics = run_epoch(model, val_loader, criterion, device)
        print(
            f"train_loss={train_metrics.loss:.4f} train_acc={train_metrics.accuracy:.4f} "
            f"val_loss={val_metrics.loss:.4f} val_acc={val_metrics.accuracy:.4f}"
        )

        if val_metrics.loss < best_val_loss:
            best_val_loss = val_metrics.loss
            stale_epochs = 0
            torch.save(
                {
                    "model_state": model.state_dict(),
                    "class_names": class_names,
                    "config": raw,
                    "val_loss": val_metrics.loss,
                    "val_accuracy": val_metrics.accuracy,
                },
                best_path,
            )
        else:
            stale_epochs += 1
            if stale_epochs >= patience:
                print("Early stopping triggered.")
                break

    return best_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/classification.yaml")
    args = parser.parse_args()
    best_path = train(args.config)
    print(f"Best checkpoint saved to {best_path}")


if __name__ == "__main__":
    main()
