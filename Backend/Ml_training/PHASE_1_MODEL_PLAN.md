# Phase 1 Model Foundation Plan

This phase prepares the model layer for the Post-Surgery Recovery Monitor.

## Goal

Build a clinically cautious AI foundation that can:

- Classify wound images into `normal`, `mild_concern`, and `urgent`
- Route low-confidence predictions to clinician review
- Segment wounds and estimate area change over time
- Produce Grad-CAM overlays for explainability
- Export the classifier to ONNX for backend or edge inference

## Current Implementation

Completed scaffolding:

- `configs/classification.yaml` for training parameters
- `src/recovery_ai/classification/train.py` for EfficientNetV2-based training
- `src/recovery_ai/classification/inference.py` for thresholded risk prediction
- `src/recovery_ai/classification/export_onnx.py` for ONNX export
- `src/recovery_ai/segmentation/medsam_runner.py` for MedSAM integration and fallback masks
- `src/recovery_ai/segmentation/area.py` for pixel and cm2 area calculations
- `src/recovery_ai/explainability/gradcam.py` for heatmap overlays
- `src/recovery_ai/utils/image_quality.py` for blur and brightness checks

## Dataset Preparation

Use the layout in `data/README.md`.

Minimum first dataset target:

- 3 folders: `normal`, `mild_concern`, `urgent`
- Balanced labels where possible
- Patient-level split if patient identifiers are available
- De-identified images only
- Written label mapping from original dataset labels to project labels

## Training Command

```bash
pip install -r requirements.txt
pip install -e .
python -m recovery_ai.classification.train --config configs/classification.yaml
```

## Export Command

```bash
python -m recovery_ai.classification.export_onnx --checkpoint models/checkpoints/best.pt --output models/onnx/wound_classifier.onnx
```

## Model Safety Rules

- Any prediction below `0.7` confidence becomes `needs_clinician_review`.
- The model must not diagnose infection directly to the patient.
- Severe symptom phrases must trigger urgent escalation, even if image risk is lower.
- Clinician corrections should be stored for later retraining.

## Next Phase 1 Tasks

1. Download or collect approved wound datasets.
2. Build the dataset manifest and label mapping.
3. Run a small smoke training pass.
4. Evaluate confusion matrix and per-class recall.
5. Wire a real MedSAM checkpoint into `MedSAMSegmenter.load`.
6. Generate Grad-CAM overlays for sample predictions.
