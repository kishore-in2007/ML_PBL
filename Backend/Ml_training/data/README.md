# Data Layout

Place curated and de-identified wound images under `data/processed/classification`.

Expected classification layout:

```text
data/processed/classification/
  normal/
    image_001.jpg
  mild_concern/
    image_002.jpg
  urgent/
    image_003.jpg
```

Recommended source datasets from the project brief:

- AZH wound dataset
- Medetec wound image dataset
- FUSeg
- DFUC

Before training:

- Remove all personally identifying content.
- Normalize labels into `normal`, `mild_concern`, and `urgent`.
- Keep a source manifest with dataset name, license, patient de-identification status, and label mapping.
- Split by patient when patient IDs are available, not randomly by image, to avoid leakage.

Do not commit raw patient images.
