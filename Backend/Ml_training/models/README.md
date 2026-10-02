# Model Artifacts

This directory is for generated artifacts only.

Suggested layout:

```text
models/
  checkpoints/
    best.pt
  onnx/
    wound_classifier.onnx
  reports/
    metrics.json
    confusion_matrix.png
```

Do not commit large checkpoints unless the team explicitly decides to version them.
