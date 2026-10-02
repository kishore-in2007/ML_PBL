from __future__ import annotations

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class ClassificationMetrics:
    loss: float
    accuracy: float


def accuracy_from_logits(logits: torch.Tensor, targets: torch.Tensor) -> float:
    predictions = torch.argmax(logits, dim=1)
    return (predictions == targets).float().mean().item()
