from __future__ import annotations

import timm
import torch.nn as nn


def build_classifier(
    model_name: str,
    num_classes: int,
    pretrained: bool = True,
    dropout: float = 0.2,
) -> nn.Module:
    return timm.create_model(
        model_name,
        pretrained=pretrained,
        num_classes=num_classes,
        drop_rate=dropout,
    )
