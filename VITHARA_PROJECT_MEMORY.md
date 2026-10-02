# Vithara Project Memory

This file is the consolidated project memory for Vithara. It records the original goal, the implementation currently present in the repository, the machine-learning methodology, the datasets, the application workflow, work completed during setup, verified behavior, and known limitations. It is intended to be reusable as project documentation, a report source, a presentation script, or context for future development.

## 1. Project identity

Project name: **Vithara - AI Wound Recovery Monitor**

Vithara is an AI-assisted remote wound-recovery monitoring platform. It is designed for patients who leave a hospital after surgery or wound treatment and need continued observation at home. The patient uploads a wound photograph periodically, records symptoms, and receives a recovery summary. Doctors can inspect the wound history, review urgent cases, write clinical notes, and manage consultations and appointments.

The current software is a clinical decision-support MVP. It is not an autonomous diagnostic system and should not be presented as a clinically validated infection detector.

## 2. Original problem and goal

After discharge, a doctor cannot continuously see what is happening to a patient's surgical wound. A patient may not know whether a wound is healing normally or whether redness, swelling, discharge, pain, fever, or increasing wound size requires medical attention. Missed deterioration can delay treatment.

The goal of Vithara is to provide a structured remote-monitoring workflow:

1. The patient uploads a wound image.
2. The application analyses the image and evaluates reported symptoms.
3. A computer-vision pipeline estimates the wound boundary and area.
4. Today's result is compared with a previous wound image, preferably yesterday's primary image.
5. The system reports an area change and a recovery trend.
6. A wound-risk classifier produces Normal, Mild Concern, or Urgent output.
7. Low-confidence or concerning cases are routed to a doctor.
8. Doctors review the evidence and decide the clinical action.

The intended benefit is earlier visibility of wound deterioration while keeping a clinician in the decision loop.

## 3. Complete user workflow

### Patient workflow

1. Register with email, password, name, and patient role.
2. Log in using JWT authentication.
3. View or update the patient profile, including an optional physical reference-marker size.
4. Upload a daily wound image.
5. Submit symptoms such as pain level, fever, medication adherence, notes, and emergency voice keywords.
6. Receive a result containing the risk class, confidence, wound area, area change, healing score, healing trend, triage status, and segmentation overlay.
7. View historical daily wound logs and recovery charts.
8. Use reminders, care-team information, voice assistance, and recovery-report sharing.

### Doctor workflow

1. Register or log in as a doctor.
2. Maintain a doctor profile.
3. Assign patients to the doctor.
4. View patient summaries and recovery history.
5. See the priority triage queue and urgent notifications.
6. Open wound images and segmentation overlays.
7. Add clinical notes and review daily wound logs.
8. Create consultation sessions and appointments.

Urgent cases currently create notifications and escalated/pending triage records. The application does not yet automatically select a doctor's free slot and book an appointment without doctor action.

## 4. Technology architecture

### Frontend

- React
- Vite
- React Router
- Axios API client
- Tailwind CSS
- Recharts for recovery trends
- Lucide React icons

Frontend location:

```text
Frontend/
```

Important patient pages include:

```text
Frontend/src/pages/patient/PatientDashboard.jsx
Frontend/src/pages/patient/CaptureWoundPhoto.jsx
Frontend/src/pages/patient/AIAnalysisResult.jsx
Frontend/src/pages/patient/RecoveryTrends.jsx
Frontend/src/pages/patient/Reminders.jsx
Frontend/src/pages/patient/VoiceAssistant.jsx
Frontend/src/pages/patient/CareTeam.jsx
Frontend/src/pages/patient/PatientProfile.jsx
```

Important doctor pages include:

```text
Frontend/src/pages/doctor/DoctorDashboard.jsx
Frontend/src/pages/doctor/PatientRecords.jsx
Frontend/src/pages/doctor/PatientSummary.jsx
Frontend/src/pages/doctor/WoundReview.jsx
Frontend/src/pages/doctor/Appointments.jsx
Frontend/src/pages/doctor/UrgentAlerts.jsx
Frontend/src/pages/doctor/ConsultationSession.jsx
Frontend/src/pages/doctor/DoctorNotifications.jsx
Frontend/src/pages/doctor/DoctorProfile.jsx
```

### Backend

- FastAPI
- SQLAlchemy
- SQLite by default
- PostgreSQL-compatible database configuration
- JWT authentication
- Local file storage by default
- Optional S3/MinIO storage
- ONNX Runtime for classifier inference
- PyTorch/MedSAM support when the checkpoint is available
- OpenCV and PIL/NumPy fallback processing

Backend location:

```text
Backend/app/
```

Main backend modules:

```text
app/main.py             Application startup, CORS, health routes, router registration
app/models.py           Database entities and enums
app/schemas.py          Request and response schemas
app/database.py         SQLAlchemy engine, session, SQLite migrations
app/auth.py             Password hashing, JWT creation and role checks
app/storage.py          Local/S3 image storage
app/recovery.py         Daily image evaluation and healing calculations
app/triage.py           Symptom and risk-based triage rules
app/doctor_services.py  Doctor assignment, notifications and helper services
app/ml/classify.py      ONNX classifier and deterministic fallback
app/ml/segment.py       MedSAM/classical wound segmentation
```

### Main API groups

```text
POST /auth/register
POST /auth/login
GET  /patients/me
PUT  /patients/me
POST /patients/me/daily-wound-photo
GET  /patients/me/daily-wound-logs
GET  /patients/me/recovery-overview
GET  /patients/me/reminders
POST /patients/me/reminders
GET  /doctor/dashboard
GET  /doctor/patients
POST /doctor/patients/assign
GET  /doctor/appointments
POST /doctor/appointments
GET  /doctor/notifications
GET  /triage/queue
GET  /media/{path}
GET  /health
GET  /health/runtime
```

## 5. Machine-learning methodology

The ML pipeline has two main model tasks and two analytical rule systems.

### 5.1 Wound-risk classification

This is a supervised multi-class image-classification task. The target classes are:

```text
Normal
Mild Concern
Urgent
```

The intended model family is an EfficientNetV2-S/DINOv2-style transfer-learning image classifier. The Phase 1 classifier is exported to ONNX and loaded by ONNX Runtime.

Model artifact:

```text
Backend/Ml_training/models/onnx/wound_classifier_phase1_final.onnx
```

Inference steps:

1. Read the uploaded image.
2. Convert it to RGB.
3. Resize it to 224 x 224 pixels.
4. Scale pixel values to floating-point values.
5. Apply ImageNet mean and standard-deviation normalization.
6. Convert the image to channel-first tensor format.
7. Run the ONNX model.
8. Apply softmax to the output logits.
9. Select the class with the highest probability.
10. Compare confidence with the configured threshold.

The classifier output is a probability distribution. A low-confidence result is routed for human review rather than being treated as a final diagnosis.

The documented Phase 1 validation results are:

```text
Validation accuracy: 47.16%
Validation loss:     1.4201
```

These results indicate an MVP/bootstrap model and not a clinically validated production model.

### 5.2 Wound segmentation

This is a pixel-level semantic-segmentation task. The output is a binary mask that identifies wound pixels and separates them from surrounding skin.

The intended primary model is MedSAM using a ViT-B checkpoint:

```text
Backend/Ml_training/models/medsam/medsam_vit_b.pth
```

The segmentation workflow is:

1. Generate an approximate wound bounding box.
2. Use the box as a MedSAM prompt.
3. Generate a binary mask.
4. Count wound pixels.
5. Convert pixels to an approximate physical area.
6. Generate a red mask overlay for patient and doctor review.

The MedSAM checkpoint is not currently present in the repository. The application therefore uses a classical OpenCV fallback. The fallback uses colour and redness features, RGB/HSV/LAB transformations, thresholding, morphology, contour detection, and connected-region cleanup. This keeps the software operational but is not equivalent to trained MedSAM inference.

### 5.3 Area measurement

The mask area is calculated as:

```text
wound_area_px = number of pixels classified as wound
```

The approximate physical area is:

```text
area_cm2 = wound_area_px / (pixels_per_cm ^ 2)
```

The default configuration uses 40 pixels per centimetre. This is an approximation because automatic reference-marker detection and camera-scale correction are not yet implemented.

### 5.4 Temporal wound comparison

The system first looks for the previous day's primary wound log. If it is not available, it uses the most recent previous segmentation.

The percentage area change is:

```text
area_change_percent = ((today_area - previous_area) / previous_area) * 100
```

Negative values mean the measured area decreased. Positive values mean the measured area increased.

### 5.5 Healing trend and recovery score

There is no trained regression model in the current project. Healing is calculated using rules applied to the segmented area change.

Current rules:

```text
area change <= -10%       Improving, score approximately 90-100
-10% < change <= 5%       Stable, score 70
5% < change <= 15%        Needs Review, score 50
change > 15%              Worsening, score 25
```

For a first image with no comparison image, the initial score is based on risk class:

```text
Normal        80
Mild Concern  65
Urgent        35
```

The displayed healing rate is therefore a heuristic recovery score, not a medically validated percentage and not the prediction of a regression model.

### 5.6 Triage engine

Triage is also rule-based. It combines:

- Classification risk class
- Model confidence
- Pain level
- Fever
- Medication adherence
- Emergency voice keywords

The result is one of:

```text
auto_cleared
pending_review
escalated
reviewed
```

Urgent predictions, severe symptoms, emergency keywords, and low-confidence predictions are routed to clinicians. The triage output is decision support and does not replace medical judgement.

## 6. Dataset inventory

The repository contains both actual prepared data and reference documentation. They must not be described as the same thing.

### 6.1 DFUC 2022 - actually prepared segmentation data

Locations:

```text
Backend/Ml_training/data/raw/DFUC2022_train_release/
Backend/Ml_training/data/processed/segmentation/dfuc2022/manifest.csv
```

The prepared project data contains approximately 2,000 paired wound images and pixel masks, with images and masks around 640 x 480 resolution. It is used as the segmentation foundation for wound-boundary and area measurement.

### 6.2 Public wound classification data - actually prepared

Locations:

```text
Backend/Ml_training/data/raw/hf_wound_classification_detection/
Backend/Ml_training/data/processed/classification/
```

The prepared classification data contains approximately 841 images converted into the application classes Normal, Mild Concern, and Urgent. The labels are weak labels derived from public wound/accident severity information, not a new clinically verified annotation campaign.

### 6.3 Accident and wound fine-tuning data

Location:

```text
Backend/Ml_training/data/raw/hf_accidents_wounds_finetune/
```

This provides additional public wound and accident examples for the bootstrap classification preparation.

### 6.4 DFUC 2021 - reference/planned infection and ischaemia data

Reference PDFs:

```text
Backend/Ml_training/DFUC2021.pdf
Backend/Ml_training/dfuc2021n.pdf
```

The DFUC 2021 research material describes infection, ischaemia, combined infection/ischaemia, and control categories. The complete image dataset and labels are not integrated into the current project training pipeline. Therefore, the current classifier must not be described as a validated infection/ischaemia model.

### 6.5 FUSeg - reference PDF only

Reference:

```text
Backend/Ml_training/FUSeg.pdf
```

The paper describes 1,210 foot-ulcer images, 1,010 training images, 200 testing images, and pixel-level expert annotations. The actual FUSeg image and mask files are not present in this repository; only the PDF is present. FUSeg should therefore be described as a referenced or proposed dataset, not as data actually used by the current implementation.

### 6.6 Dataset wording for reports

Correct wording:

> The implemented MVP uses prepared DFUC 2022 image-mask pairs for segmentation and prepared public wound/accident data for weakly labelled three-class risk classification. DFUC 2021 and FUSeg are included as research references and possible future data sources; their complete datasets are not currently integrated.

## 7. Database and stored entities

The database stores users, roles, patient profiles, doctor profiles, patient-doctor assignments, wound images, classifications, segmentations, daily wound logs, healing metrics, triage cases, clinical notes, reminders, notifications, consultation sessions, appointments, shared recovery reports, and audit events.

Each daily wound evaluation links:

```text
Patient
  -> DailyWoundLog
      -> WoundImage
          -> Classification
          -> Segmentation
      -> Healing values
      -> TriageCase
```

Images are stored locally by default in `Backend/uploads/`. S3/MinIO configuration is available for deployment scenarios that need object storage.

## 8. Safety and privacy behavior

- JWT authentication protects API operations.
- Patient and doctor roles are checked on protected routes.
- Passwords are hashed.
- Selected personal fields support encryption.
- Audit events record important access and modification actions.
- Low-confidence results are routed for clinician review.
- Severe symptoms and emergency voice terms can escalate triage.

The current `/media` route is intended for local MVP/demo use and should be secured with authorization or signed URLs before production deployment.

## 9. Work completed to make the application runnable

The following implementation and environment fixes were completed:

1. Python requirements were updated for a modern Python 3.13 environment instead of relying on unavailable old binary wheels.
2. `email-validator` was added because authentication schemas use Pydantic `EmailStr`.
3. `bcrypt` was constrained to a Passlib-compatible 4.x release so registration and login work correctly.
4. The backend now creates the local upload directory before mounting it as static media, so a clean checkout can start.
5. ONNX session creation is protected with an exception boundary. If the ONNX artifact is malformed or unavailable, the application uses its deterministic demonstration fallback instead of returning HTTP 500.
6. Backend startup scripts were aligned to port 8000, matching the frontend API default.
7. The patient result page now treats `pending_review` and `escalated` as review-required statuses.
8. A root README was added with installation, startup, model-fallback, and verification instructions.
9. A PPT-ready system architecture image was generated at:

```text
output/imagegen/vithara-system-architecture.png
```

10. A PPT-ready ML methodology image was generated at:

```text
output/imagegen/vithara-ml-methodology.png
```

## 10. Verification already performed

The following checks passed in the project environment:

```text
Backend Python imports: passed
Backend route registration: passed
pip check: passed with no broken requirements
Python compileall app: passed
Frontend npm install: passed
Frontend npm run build: passed
Patient registration: passed
Patient login: passed
Patient profile access: passed
Daily wound upload: passed
Classification fallback: passed
Segmentation fallback: passed
Recovery overview: passed
Daily wound log listing: passed
Previous-day area comparison: passed
Doctor registration/login: passed
Patient assignment: passed
Doctor dashboard: passed
Doctor appointment creation: passed
Doctor appointment listing: passed
```

The end-to-end test confirmed that a patient upload produced a risk class, wound area, healing trend, triage result, and segmentation model label. A second dated image produced a previous-day area comparison. A doctor was able to assign the patient, access the dashboard, and create an appointment.

## 11. How to run the project

Requirements:

```text
Python 3.13 or compatible Python
Node.js 20 or newer
npm
```

Backend setup:

```powershell
cd Backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Frontend setup:

```powershell
cd Frontend
npm.cmd install
```

Run the backend in one terminal:

```powershell
cd Backend
.\run_backend.ps1
```

Run the frontend in another terminal:

```powershell
cd Frontend
npm.cmd run dev
```

Default addresses:

```text
Frontend: http://127.0.0.1:5173
Backend:  http://127.0.0.1:8000
API docs: http://127.0.0.1:8000/docs
Health:   http://127.0.0.1:8000/health
```

## 12. Known limitations

1. The classification model is a bootstrap model with low reported validation accuracy and must not be presented as clinical diagnosis.
2. The included ONNX model currently has an external-data path problem; the safe deterministic fallback runs instead.
3. The MedSAM checkpoint is absent, so the current runtime uses classical OpenCV segmentation.
4. The classifier predicts broad severity classes and does not independently diagnose infection, rash, cellulitis, pus, ischaemia, necrosis, or dehiscence.
5. The cm² measurement uses a fixed pixels-per-centimetre approximation.
6. Camera distance, lighting, zoom, angle, and image quality can affect area comparisons.
7. Automatic image registration and reference-marker detection are not implemented.
8. Healing rate is a heuristic score based on area change, not a trained regression model.
9. Automatic doctor-slot selection and automatic appointment booking are not implemented; doctors create appointments manually.
10. The public media endpoint is acceptable for an MVP demo but needs authorization or signed URLs for production.
11. The project needs clinical validation, expert annotation, prospective testing, and regulatory review before medical deployment.

## 13. Recommended next development steps

1. Add a valid, self-contained ONNX classifier or retrain and export the model correctly.
2. Supply and verify the MedSAM checkpoint or train a wound-specific segmentation model.
3. Add image-quality rejection and patient guidance for blur, poor lighting, and incorrect framing.
4. Add a reference marker in every photo and implement automatic scale calibration.
5. Register/alignment-correct images before comparing wound areas across days.
6. Train multi-label wound findings for infection signs, redness/rash, discharge, swelling, tissue condition, and dehiscence using clinically annotated data.
7. Replace the heuristic healing score with a clinically defined metric and validate it prospectively.
8. Implement doctor availability, conflict checking, patient confirmation, and automatic urgent appointment scheduling.
9. Secure image serving and strengthen production secrets/configuration.
10. Add automated backend, ML, API, and browser tests.

## 14. Ready-to-use project abstract

> Vithara is an AI-assisted remote wound-recovery monitoring platform for patients after hospital discharge. The patient submits periodic wound photographs and symptom information through a web application. The system applies a three-class wound-risk classifier and a wound-segmentation pipeline to identify the wound region, estimate its area, and compare the current image with a previous image. A rule-based recovery and triage engine converts the model output, area change, confidence, and symptoms into improving, stable, worsening, clinician-review, or urgent-escalation states. Doctors receive a prioritized review queue, wound history, segmentation overlays, clinical-note tools, and appointment management. The MVP uses prepared DFUC 2022 image-mask pairs for segmentation and public weakly labelled wound data for classification. Because the current models and measurements are not clinically validated, Vithara is intended as clinician decision support rather than autonomous diagnosis.

## 15. One-minute presentation explanation

> Vithara solves the gap between hospital discharge and continuous wound observation. A patient uploads a daily wound photo and records symptoms. The image classifier predicts Normal, Mild Concern, or Urgent. The segmentation pipeline identifies the wound boundary and estimates its area. The application compares today’s area with the previous day to calculate percentage change and a recovery trend. Confidence and symptoms are combined by a triage engine. Normal cases can be cleared, while low-confidence, worsening, or symptom-heavy cases are sent to a doctor. The doctor can review the image, mask overlay, historical trend, notes, notifications, and appointments. The system currently uses DFUC 2022 for prepared segmentation data and public wound datasets for bootstrap classification, with MedSAM and ONNX support plus safe classical/deterministic fallbacks.

## 16. Important terminology rule

When describing the project, use these accurate terms:

```text
Use: AI-assisted wound-risk screening
Use: wound segmentation and area estimation
Use: rule-based healing trend
Use: clinician decision support
Avoid: fully autonomous diagnosis
Avoid: clinically validated infection detector
Avoid: trained healing-rate regression model
Avoid: FUSeg training data, unless the actual FUSeg files are later added
```
