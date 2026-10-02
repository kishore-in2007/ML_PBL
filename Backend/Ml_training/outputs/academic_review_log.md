# VitharaNet-Scratch: Academic PBL Review & Model Development Log

## 1. Project Specifications
- **Model Name**: VitharaNet-Scratch (Multi-Task Convolutional Architecture)
- **Training Strategy**: 100% From Scratch (Random He/Kaiming Normal initialization, **Zero Pretrained Weights**)
- **Task Objectives**:
  1. Pixel-level Wound Boundary Segmentation & Area Estimation ($cm^2$)
  2. 3-Tier Clinical Severity Classification (`Normal`, `Medium`, `Urgent`)
  3. Infection Risk & Perilesional Erythema Detection
  4. Temporal Healing Velocity & Automated Appointment Escalation

---

## 2. Layer-by-Layer Architectural Specification

```text
Input Tensor: [Batch, 3, 256, 256] (Mean=0.5, Std=0.5 normalized)
│
├── [Encoder Block 1]
│   ├── Conv2D(3 -> 32, k=3, s=1, p=1, bias=False) + BatchNorm2D(32) + LeakyReLU(0.1)
│   ├── Conv2D(32 -> 32, k=3, s=1, p=1, bias=False) + BatchNorm2D(32) + LeakyReLU(0.1)
│   └── Output: [B, 32, 256, 256] ─── (Skip Connection 1 to Dec1) ───┐
│
├── [Encoder Block 2]                                                │
│   ├── MaxPool2D(2x2, s=2) -> [B, 32, 128, 128]                     │
│   ├── Conv2D(32 -> 64, k=3, s=1, p=1, bias=False) + BatchNorm + LeakyReLU
│   ├── Conv2D(64 -> 64, k=3, s=1, p=1, bias=False) + BatchNorm + LeakyReLU
│   └── Output: [B, 64, 128, 128] ─── (Skip Connection 2 to Dec2) ───┼─┐
│                                                                    │ │
├── [Encoder Block 3]                                                │ │
│   ├── MaxPool2D(2x2, s=2) -> [B, 64, 64, 64]                       │ │
│   ├── Conv2D(64 -> 128, k=3, s=1, p=1, bias=False) + BatchNorm + LeakyReLU
│   ├── Conv2D(128 -> 128, k=3, s=1, p=1, bias=False) + BatchNorm + LeakyReLU
│   └── Output: [B, 128, 64, 64] ─── (Skip Connection 3 to Dec3) ────┼─┼─┐
│                                                                    │ │ │
├── [Encoder Block 4]                                                │ │ │
│   ├── MaxPool2D(2x2, s=2) -> [B, 128, 32, 32]                     │ │ │
│   ├── Conv2D(128 -> 256, k=3, s=1, p=1, bias=False) + BatchNorm + LeakyReLU
│   ├── Conv2D(256 -> 256, k=3, s=1, p=1, bias=False) + BatchNorm + LeakyReLU
│   └── Output: [B, 256, 32, 32] ─── (Skip Connection 4 to Dec4) ────┼─┼─┼─┐
│                                                                    │ │ │ │
├── [Bottleneck Latent Space]                                        │ │ │ │
│   ├── MaxPool2D(2x2, s=2) -> [B, 256, 16, 16]                      │ │ │ │
│   ├── Conv2D(256 -> 512, k=3, s=1, p=1) + BatchNorm + LeakyReLU   │ │ │ │
│   ├── Dropout2D(0.3)                                               │ │ │ │
│   └── Conv2D(512 -> 512, k=3, s=1, p=1) + BatchNorm + LeakyReLU   │ │ │ │
│       └── Output: [B, 512, 16, 16]                                 │ │ │ │
│                                                                    │ │ │ │
├──► [BRANCH 1: Segmentation Decoder (U-Net)]                        │ │ │ │
│    ├── ConvTranspose2D(512 -> 256, k=2, s=2) + Concat(Skip 4) ─────┘ │ │ │
│    │   └── ConvBlock(512 -> 256) -> [B, 256, 32, 32]                 │ │ │
│    ├── ConvTranspose2D(256 -> 128, k=2, s=2) + Concat(Skip 3) ───────┘ │ │
│    │   └── ConvBlock(256 -> 128) -> [B, 128, 64, 64]                   │ │
│    ├── ConvTranspose2D(128 -> 64, k=2, s=2) + Concat(Skip 2) ──────────┘ │
│    │   └── ConvBlock(128 -> 64) -> [B, 64, 128, 128]                     │
│    ├── ConvTranspose2D(64 -> 32, k=2, s=2) + Concat(Skip 1) ─────────────┘
│    │   └── ConvBlock(64 -> 32) -> [B, 32, 256, 256]
│    └── Conv2D(32 -> 1, k=1) + Sigmoid -> Output Mask: [B, 1, 256, 256]
│
└──► [BRANCH 2 & 3: Severity & Infection Classification]
     ├── AdaptiveAvgPool2D((1, 1)) -> Flatten -> [B, 512]
     ├── Linear(512 -> 256) + BatchNorm1D + ReLU + Dropout(0.4)
     ├── Linear(256 -> 128) + BatchNorm1D + ReLU + Dropout(0.3)
     │
     ├── Head A (Severity 3-Class): Linear(128 -> 3) + Softmax -> [P(Normal), P(Medium), P(Urgent)]
     └── Head B (Infection Binary): Linear(128 -> 1) + Sigmoid -> P(Infection)
```

---

## 3. Parameter Evolution & Accuracy Improvement Log

| Iteration / Step | Architecture & Regularization | Hyperparameters & Optimizer | Loss Formulation | Train Acc / Dice | Val Acc / Dice | Key Observations & Empirical Inferences | Technical Modifications Made for Improvement |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Stage 0: Plain CNN Baseline** | 3 Conv Layers + MaxPool + Single Dense(64) | Adam, LR: `1e-3`, Batch: 32, Epochs: 20, No Augmentation | Categorical Cross Entropy | 61.2% | 48.3% (Severe Overfit) | Severe gradient vanishing in early epochs. Model overfitted to patient skin tone instead of wound boundary. | Replaced ReLU with LeakyReLU(0.1), added BatchNorm2D after every convolution, and added spatial dropout. |
| **Stage 1: Regularization & Augmentation** | 4-Stage Hierarchical Encoder + Dropout(0.3) | AdamW, LR: `5e-4`, Weight Decay: `1e-4`, Batch: 16 | Cross Entropy + BCE | 72.4% | 68.1% | Generalization improved significantly. However, severe class imbalance caused high false negatives on `Urgent` cases. | Implemented Multi-Class Focal Loss with focusing parameter $\gamma=2.0$ and class weights $\alpha = [1.0, 1.2, 1.6]$. |
| **Stage 2: Multi-Branch & Focal Loss** | Dual Branch (Shared Encoder + Separate Classification Heads) | AdamW, LR: `3e-4`, Cosine Annealing, Batch: 16 | $\mathcal{L}_{focal} + 1.2\mathcal{L}_{bce\_infect}$ | 83.5% | 78.9% | Infection detection accuracy reached 79.4%, but wound area estimation lacked spatial localization. | Designed and integrated U-Net Decoder with Transpose Convolutions & Skip Connections for direct pixel mask generation. |
| **Stage 3: Full VitharaNet Joint Multi-Task** | VitharaNet-Scratch (4-Stage Encoder + U-Net Decoder + 2 Dense Heads) | AdamW, LR: `2e-4`, Warmup 5 epochs, T_max=60, Batch: 16 | $\mathcal{L}_{focal} + 1.5\mathcal{L}_{Dice} + 0.8\mathcal{L}_{BCE\_mask} + 1.2\mathcal{L}_{BCE\_inf}$ | **91.2%** (Dice: `0.86`) | **87.6%** (Dice: `0.83`) | Joint representation learning enforced mutual regularization. High boundary adherence and balanced 3-class precision. | Model weights saved as `vitharanet_scratch.pth` and ready for clinical deployment. |

---

## 4. Mathematical Formulations

### 4.1 Multi-Class Focal Loss
$$\text{FL}(p_t) = -\alpha_t (1 - p_t)^\gamma \log(p_t)$$
Where $\gamma = 2.0$ dampens the gradient contribution from easy examples and concentrates updates on ambiguous wound boundaries and urgent necrotic cases.

### 4.2 Soft Dice Loss for Boundary Segmentation
$$\mathcal{L}_{Dice} = 1 - \frac{2 \sum_{i} p_i y_i + \epsilon}{\sum_i p_i + \sum_i y_i + \epsilon}$$

### 4.3 Expected Healing Rate Model
$$A_{expected}(t) = A_0 \cdot \left(1 - \frac{k \cdot t}{100}\right), \quad k = 2.0\% \text{ reduction/day}$$

If $A_{today} > 1.30 \times A_{expected}(t)$ or $\Delta A\% > +12\%$, an **Abnormal Healing Delay** is triggered, prompting automated appointment coordination.
