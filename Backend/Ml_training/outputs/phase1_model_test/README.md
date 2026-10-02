# Phase 1 Model Test Report

Generated on: 2026-07-10

## Tested Artifacts

- Classifier checkpoint: `models/checkpoints/phase1_final/best.pt`
- ONNX classifier: `models/onnx/wound_classifier_phase1_final.onnx`
- Segmentation manifest: `data/processed/segmentation/dfuc2022/manifest.csv`
- Generated test images: `outputs/phase1_model_test/generated_images`
- Full JSON report: `outputs/phase1_model_test/phase1_model_test_report.json`

## Classifier Specs

- Classes: `mild_concern`, `normal`, `urgent`
- Input tensor: `1 x 3 x 224 x 224`
- Output: `risk_logits`
- Inference routing: low-confidence predictions can be routed to clinician review

## Validation Metrics

Validation split size: 169 images

| Metric | Value |
| --- | ---: |
| Accuracy | 49.11% |
| Loss | 1.3917 |
| Macro F1 | 35.48% |
| Weighted F1 | 44.03% |

Per-class metrics:

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| `mild_concern` | 55.37% | 79.76% | 65.37% | 84 |
| `normal` | 40.00% | 27.45% | 32.56% | 51 |
| `urgent` | 15.38% | 5.88% | 8.51% | 34 |

Confusion matrix rows are true labels and columns are predicted labels in this order:

`mild_concern`, `normal`, `urgent`

```text
[[67, 12,  5],
 [31, 14,  6],
 [23,  9,  2]]
```

## Generated Synthetic Image Test

- Generated synthetic images: 9
- Raw-label agreement: 33.33%
- Result: the model predicted all generated images as `mild_concern`

This is useful as a pipeline smoke test, but it is not proof of medical accuracy. The synthetic images are simple generated shapes and are outside the real wound-image training distribution.

## ONNX Consistency

Maximum absolute logit difference between PyTorch and ONNX on generated images:

```text
0.00000525
```

This means the ONNX export is numerically consistent with the PyTorch checkpoint for demo inference.

## Segmentation Specs

- DFUC2022 paired image/mask samples: 2000
- Sampled masks for area stats: 25
- Mean wound mask area ratio: 4.13%
- Minimum wound mask area ratio: 0.20%
- Maximum wound mask area ratio: 35.04%

## Honest MVP Interpretation

The segmentation and ONNX export are in good shape for the MVP. The classifier works as a bootstrap risk estimator, but the validation results show it is biased toward `mild_concern` and weak on `urgent`. For the hackathon, present it as a prototype severity triage model with clinician-review routing, not as a clinically validated diagnosis model.
