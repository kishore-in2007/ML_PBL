# PS5 Backend - MVP

FastAPI backend for the Vithara post-surgery recovery monitor MVP.

The backend now runs locally with:

- SQLite database: `ps5.db`
- Uploaded wound photos: `uploads/`
- JWT auth and role checks
- Patient profile creation and lookup
- Wound classification, segmentation, triage, history, and audit logging
- ONNX classifier integration from `Ml_training/models/onnx/wound_classifier_phase1_final.onnx`
- MedSAM/SAM wound segmentation integration from `Ml_training/models/medsam/medsam_vit_b.pth`

## Quick Start

```powershell
cp .env.example .env
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

For a fresh environment:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/register` | none | Create user. Patient users also get a patient profile. |
| POST | `/auth/login` | none | Return JWT and user payload. |
| GET | `/patients/me` | patient JWT | Get or create current patient profile. |
| PUT | `/patients/me` | patient JWT | Update current patient profile. |
| GET | `/patients/{patient_id}` | JWT | Get patient profile with patient self-access checks. |
| POST | `/classify` | JWT | Upload wound photo and return risk class, confidence, raw scores, image URL. |
| POST | `/segment?image_id=...` | JWT | Estimate wound area and percent change from previous image. |
| POST | `/triage` | JWT | Fuse classification and symptoms into final risk score and routing. |
| GET | `/triage/queue` | nurse/doctor/admin | Priority-sorted clinician queue. |
| GET | `/patient/{id}/history` | JWT | Wound image, classification, and segmentation timeline. |
| GET | `/media/{path}` | none | Serve local uploaded images for MVP/demo use. |

## Model Behavior

`app/ml/classify.py` loads the exported Phase 1 ONNX classifier when `onnxruntime`
is installed. If the runtime or model file is unavailable, it logs the reason and
uses a deterministic fallback so the API remains demoable.

`app/ml/segment.py` loads the local MedSAM/SAM ViT-B checkpoint, generates an
automatic wound bounding box, predicts a binary mask, and calculates wound area.
If the MedSAM runtime or checkpoint fails, the API falls back to classical CV
segmentation and reports `model_used="classical_fallback"` in the response.

## Storage

Default storage is local:

```env
STORAGE_BACKEND=local
LOCAL_UPLOAD_DIR=uploads
```

To use MinIO/S3 later, set `STORAGE_BACKEND=s3` and configure the existing
`S3_*` variables.

## Safety Notes

The model output is decision support only. Low-confidence predictions and severe
symptom reports are routed for clinician review; the system should not present a
diagnosis directly to the patient.
