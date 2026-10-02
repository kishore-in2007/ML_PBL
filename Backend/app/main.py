import logging
import importlib.util
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, apply_sqlite_migrations, engine
from app.routers import auth as auth_router
from app.routers import classify as classify_router
from app.routers import doctors as doctors_router
from app.routers import patients as patients_router
from app.routers import segment as segment_router
from app.routers import triage as triage_router
from app.config import settings

print("DATABASE_URL =", settings.DATABASE_URL)

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="PS5 Post-Surgery Recovery Monitor — Backend",
    description="CV classification, segmentation, and clinical triage API",
    version="1.0.0",
)

# CORS for React frontend, mobile apps, and local network devices
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"^(https?|capacitor|ionic)://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    apply_sqlite_migrations()

    try:
        from app.storage import ensure_bucket
        ensure_bucket()

    except Exception as exc:
        logging.warning(f"S3 bucket check skipped: {exc}")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/health/runtime", tags=["health"])
def runtime_health():
    return {
        "status": "ok",
        "python_executable": sys.executable,
        "numpy_available": importlib.util.find_spec("numpy") is not None,
        "cv2_available": importlib.util.find_spec("cv2") is not None,
        "torch_available": importlib.util.find_spec("torch") is not None,
        "onnxruntime_available": importlib.util.find_spec("onnxruntime") is not None,
        "segment_anything_available": importlib.util.find_spec("segment_anything") is not None,
    }


app.include_router(auth_router.router)
app.include_router(patients_router.router)
app.include_router(doctors_router.router)
app.include_router(classify_router.router)
app.include_router(segment_router.router)
app.include_router(triage_router.router)
Path(settings.LOCAL_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.LOCAL_UPLOAD_DIR), name="media")
