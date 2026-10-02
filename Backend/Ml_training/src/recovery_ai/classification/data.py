from __future__ import annotations

from pathlib import Path

import torch
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms


def build_transforms(image_size: int, training: bool) -> transforms.Compose:
    if training:
        return transforms.Compose(
            [
                transforms.Resize((image_size, image_size)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(12),
                transforms.ColorJitter(brightness=0.18, contrast=0.15, saturation=0.1),
                transforms.ToTensor(),
                transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            ]
        )

    return transforms.Compose(
        [
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )


def build_dataloaders(
    data_root: str | Path,
    image_size: int,
    batch_size: int,
    num_workers: int,
    val_split: float,
    seed: int,
) -> tuple[DataLoader, DataLoader, list[str]]:
    data_root = Path(data_root)
    train_dataset = datasets.ImageFolder(data_root, transform=build_transforms(image_size, training=True))
    val_dataset = datasets.ImageFolder(data_root, transform=build_transforms(image_size, training=False))

    indices = list(range(len(train_dataset)))
    labels = [sample[1] for sample in train_dataset.samples]
    train_idx, val_idx = train_test_split(
        indices,
        test_size=val_split,
        random_state=seed,
        stratify=labels,
    )

    train_loader = DataLoader(
        Subset(train_dataset, train_idx),
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    val_loader = DataLoader(
        Subset(val_dataset, val_idx),
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    return train_loader, val_loader, train_dataset.classes
