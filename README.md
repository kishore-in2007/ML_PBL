# Vithara - AI Wound Recovery Monitor

Vithara is a clinical decision-support and remote wound-recovery platform designed for post-operative patient monitoring. It combines a custom multi-task deep neural network trained completely from scratch, a temporal healing velocity engine, and a dual-role triage system for Patients and Doctors.

---

## 🚀 Key Features

- **Trained 100% From Scratch**: Custom multi-task architecture (`VitharaNet-Scratch`) with U-Net segmentation decoder, 3-tier severity classifier, and dedicated infection detection head (**Zero Pretrained Models Used**).
- **Patient 3-State Display**: Simplified and intuitive patient-facing triage view: `Normal` (Green), `Medium` (Yellow), and `Urgent` (Red).
- **Infection & Erythema Assessment**: Continuous tracking of perilesional redness, bacterial risk, and exudate.
- **Temporal Healing Velocity**: Real-time comparison against clinical linear-decay healing models ($A_{expected}(t) = A_0 \cdot [1 - k \cdot t]$).
- **Automated Doctor Escalation**: Automatically schedules priority doctor appointments and generates comprehensive clinical reports when abnormal healing delay or emergencies are detected.
- **Dual Portal & Dual Login**: Dedicated views and capabilities for Patients and Clinicians.
- **Mobile APK Ready**: Configured with Capacitor for cross-platform Android mobile packaging.
- **Interactive Terminal Diagnostic CLI**: Standalone command-line inference tool for live presentations and academic evaluations.

---

## 💻 Standalone Terminal CLI & Model Execution

You can run and test the ML model directly from your terminal:

### 1. Run Diagnostic CLI on Any Image

```powershell
# Run standalone inference on a sample image:
python Backend/Ml_training/run_model.py --image "Backend/Ml_training/data/sample.jpg" --prev_area 12.5 --days 3
```

### 2. Train Model From Scratch (PBL Review Ready)

```powershell
# Train VitharaNet from complete scratch with custom loss & metrics logging:
python Backend/Ml_training/train_scratch.py --epochs 60 --batch_size 16 --lr 0.0002
```

---

## 📁 Project & Dataset Structure

```text
Vithara/
├── Backend/
│   ├── app/                         # FastAPI Application Core
│   │   ├── ml/                      # Inference wrappers & bridge
│   │   ├── routers/                 # Patient, Doctor, Auth & Triage APIs
│   │   ├── doctor_services.py       # Auto-appointment scheduling & alerts
│   │   ├── recovery.py              # Daily evaluation & healing velocity
│   │   └── models.py                # Database schemas
│   ├── Ml_training/
│   │   ├── data/                    # Dataset directory
│   │   │   ├── raw/                 # Raw DFUC2022 & wound datasets
│   │   │   ├── processed/           # Processed train / val / test splits
│   │   │   └── DATASET_SPECIFICATION_AND_GUIDE.md
│   │   ├── src/
│   │   │   ├── vitharanet.py        # Custom Scratch Multi-Task CNN Architecture
│   │   │   ├── loss.py              # Multi-Class Focal Loss & Soft Dice Loss
│   │   │   ├── dataset.py           # Custom Dataset & Scratch Augmentations
│   │   │   └── healing_engine.py    # Temporal Healing Velocity & Appointment Logic
│   │   ├── outputs/
│   │   │   └── academic_review_log.md # Step-by-step layer design & parameter tuning log
│   │   ├── train_scratch.py         # Main scratch training pipeline
│   │   └── run_model.py             # Standalone Terminal Diagnostic CLI
│   └── requirements.txt
│
├── Frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── common/Login.jsx     # Dual-login Portal (Doctor / Patient switchable)
│   │   │   ├── patient/             # Patient Portal (Capture, 3-tier view: Normal/Medium/Urgent)
│   │   │   └── doctor/              # Doctor Portal (Triage Queue, Clinical Reports, Appointments)
│   │   └── App.jsx
│   ├── capacitor.config.json        # Mobile APK wrapper config
│   └── package.json
└── README.md
```

---

## 🛠️ Application Setup & Execution

### 1. Backend Setup

```powershell
cd Backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\run_backend.ps1
```

Backend will be active at: `http://127.0.0.1:8000` (API Docs: `http://127.0.0.1:8000/docs`).

### 2. Frontend Setup

```powershell
cd Frontend
npm install
npm run dev
```

Frontend will be active at: `http://127.0.0.1:5173`.

---

## 📱 Building Android APK

To generate the Android APK file using Capacitor:

```powershell
cd Frontend
npm run build
npx cap add android
npx cap copy
npx cap open android
```

In Android Studio, select **Build > Build Bundle(s) / APK(s) > Build APK(s)** to generate the installable `.apk` file.

