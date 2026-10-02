# Vithara Dataset Organization & Preparation Guide

This guide describes the dataset requirements and directory structure for training **VitharaNet-Scratch** from scratch without pretrained models.

## 1. Directory Structure

```text
Backend/Ml_training/data/
├── raw/
│   ├── dfuc2022/                     # Paired wound segmentation data
│   │   ├── images/                   # .jpg/.png wound photos
│   │   └── masks/                    # .png binary ground truth masks (255=wound, 0=skin)
│   ├── infection_wounds/             # Labeled infection images (erythema, pus, cellulitis)
│   └── wound_severity_dataset/       # Categorized into Normal, Medium, Urgent
├── processed/
│   ├── train/                        # 70% Training split
│   │   ├── images/
│   │   ├── masks/
│   │   └── labels.csv                # [filename, severity (0/1/2), infection (0/1), area_cm2]
│   ├── val/                          # 15% Validation split
│   │   ├── images/
│   │   ├── masks/
│   │   └── labels.csv
│   └── test/                         # 15% Test evaluation split
│       ├── images/
│       ├── masks/
│       └── labels.csv
└── manifest.json                     # Dataset verification & class balance report
```

---

## 2. Target Classes & Annotation Standards

### 2.1 Severity Classification (3 Classes)
1. **Class 0: Normal**
   - Clean, healing surgical incision or closing wound.
   - Minimal to no perilesional redness ($< 0.5\text{cm}$).
   - Healthy pink granulation tissue, no purulent exudate.
2. **Class 1: Medium (Mild Concern)**
   - Moderate erythema ($0.5\text{cm} - 2.0\text{cm}$) or mild swelling.
   - Serous exudate, slightly delayed contraction, requires observation.
3. **Class 2: Urgent (Critical)**
   - Severe cellulitis / spreading redness ($> 2.0\text{cm}$).
   - Purulent yellow/green pus, foul odor, tissue necrosis (black eschar), or surgical dehiscence (wound reopening).

### 2.2 Infection Flag (Binary)
- `0`: Clean wound bed, no active bacterial infection signs.
- `1`: Active bacterial complication, erythema halo, exudate, or heat/fever symptoms.

### 2.3 Segmentation Ground Truth
- Binary 1-channel mask ($256 \times 256$) with values:
  - `0`: Background healthy skin / surrounding tissue.
  - `255`: Active wound area / ulcer crater.

---

## 3. Dataset Preprocessing & Ingestion Command

To generate processed train/val/test splits or run the training pipeline:

```powershell
# Run training directly on the prepared dataset:
python Backend/Ml_training/train_scratch.py --data_dir Backend/Ml_training/data/processed --epochs 60 --batch_size 16 --lr 0.0002
```
