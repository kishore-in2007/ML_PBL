# Post-Surgery Recovery Monitor

Phase 1 focuses on preparing the AI model foundation for wound recovery monitoring.

The model layer is organized around four responsibilities:

- Wound image classification into `normal`, `mild_concern`, and `urgent`
- Human-review routing when model confidence is low
- Wound segmentation and area tracking
- Explainability overlays for clinician and patient review

This repository currently contains the Phase 1 scaffolding. Dataset downloads and pretrained weight downloads are intentionally left as explicit setup steps because the source datasets and model licenses must be reviewed before use.

## Phase 1 Structure

```text
configs/
  classification.yaml
data/
  README.md
models/
  README.md
src/
  recovery_ai/
    classification/
    explainability/
    segmentation/
    utils/
```

## Quick Start

Create a Python environment, install dependencies from `requirements.txt`, prepare data using the layout in `data/README.md`, then run:

```bash
python -m recovery_ai.classification.train --config configs/classification.yaml
```

After training, export ONNX:

```bash
python -m recovery_ai.classification.export_onnx --checkpoint models/checkpoints/best.pt --output models/onnx/wound_classifier.onnx
```

## Safety Boundary

The model output is decision support only. Low-confidence predictions and urgent/severe symptom cases must be routed to a clinician for review. The system should never present a diagnosis directly to the patient.
