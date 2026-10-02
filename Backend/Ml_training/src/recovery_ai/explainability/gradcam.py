from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import torch
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget


def create_gradcam_overlay(
    model: torch.nn.Module,
    input_tensor: torch.Tensor,
    original_rgb_float: np.ndarray,
    target_class: int,
    target_layers: list[torch.nn.Module],
    output_path: str | Path | None = None,
) -> np.ndarray:
    """Return a Grad-CAM overlay for one normalized input image.

    `original_rgb_float` must be RGB float data in the [0, 1] range.
    """
    model.eval()
    with GradCAM(model=model, target_layers=target_layers) as cam:
        grayscale_cam = cam(
            input_tensor=input_tensor,
            targets=[ClassifierOutputTarget(target_class)],
        )[0]

    overlay = show_cam_on_image(original_rgb_float, grayscale_cam, use_rgb=True)
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
    return overlay
