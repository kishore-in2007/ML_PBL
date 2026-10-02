# Phase 1 Status

Status: ready for hackathon MVP

## Project Understanding

The Phase 1 model layer supports the Post-Surgery Recovery Monitor MVP:

- wound risk/severity prediction from an uploaded wound image
- wound segmentation and wound-area tracking
- healing trend estimation across multiple dated images
- human review routing when model confidence is low

## Prepared Data

Classification MVP data:

- Path: `data/processed/classification`
- Classes: `normal`, `mild_concern`, `urgent`
- Images: 841 total
- Source note: weak-label public wound/accident severity data, suitable for MVP demonstration but not clinical validation

Segmentation data:

- Path: `data/processed/segmentation/dfuc2022/manifest.csv`
- Source: DFUC2022 train release from `archive (3).zip`
- Paired image/mask samples: 2000
- Sample size verified: 640 x 480 images and masks

Reference/project PDFs and archives are kept in the repository root for traceability.

## Final Model Artifacts

Classifier checkpoint:

- `models/checkpoints/phase1_final/best.pt`
- Classes stored in checkpoint: `mild_concern`, `normal`, `urgent`
- Validation loss: 1.4201
- Validation accuracy: 0.4716

ONNX classifier:

- `models/onnx/wound_classifier_phase1_final.onnx`
- External data: `models/onnx/wound_classifier_phase1_final.onnx.data`
- Input: `image`
- Output: `risk_logits`

Segmentation model:

- `models/medsam/medsam_vit_b.pth`
- Also available: `models/medsam/lite_medsam.pth`

## MVP Behavior

Single image:

- predicts severity/risk as `normal`, `mild_concern`, or `urgent`
- routes low-confidence predictions to `needs_clinician_review`
- can segment wound region and estimate wound area from the mask

Multiple dated images:

- compares wound area over time
- estimates healing trend by percentage area change
- supports improving / worsening / needs review dashboard logic

## Important Limitation

The current classifier is an MVP bootstrap model, not a clinically validated infection/ischaemia model. For a stronger research-grade classifier, the full DFUC2021 classification training images and labels are still needed.

Recommended hackathon wording:

> The MVP uses real DFUC2022 wound segmentation data and a bootstrap wound-risk classifier. With access to the full DFUC2021 classification labels, the classifier can be further fine-tuned for infection and ischaemia prediction.

## Verification Command

```powershell
python -m recovery_ai.phase1_verify --checkpoint models/checkpoints/phase1_final/best.pt --onnx models/onnx/wound_classifier_phase1_final.onnx
```

Expected final line:

```text
phase1_status=ready_for_hackathon_mvp
```
