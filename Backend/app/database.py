from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=not settings.DATABASE_URL.startswith("sqlite"),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def apply_sqlite_migrations():
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    additions = {
        "patients": {
            "surgery_date": "DATETIME",
            "primary_doctor_id": "VARCHAR",
            "next_appointment_date": "DATETIME",
            "doctor_consultancy_date": "DATETIME",
            "final_doctor_meet_date": "DATETIME",
            "recovery_goal": "TEXT",
            "current_healing_rate": "FLOAT",
            "current_healing_trend": "VARCHAR",
            "last_daily_upload_at": "DATETIME",
        },
        "wound_images": {
            "capture_date": "DATE",
            "content_type": "VARCHAR",
            "image_quality_score": "FLOAT",
            "ai_evaluated": "INTEGER",
            "mask_overlay_key": "VARCHAR",
        },
        "segmentations": {
            "model_used": "VARCHAR",
            "model_confidence": "FLOAT",
            "prompt_box": "JSON",
        },
        "daily_wound_logs": {
            "reviewed_by_doctor_id": "VARCHAR",
            "doctor_review_note": "TEXT",
            "doctor_reviewed_at": "DATETIME",
            "is_primary_daily_image": "INTEGER",
        },
        "healing_metrics": {
            "comparison_source": "VARCHAR",
        },
        "patient_reminders": {
            "schedule_label": "VARCHAR",
            "notes": "TEXT",
            "updated_at": "DATETIME",
        },
        "shared_recovery_reports": {
            "payload": "JSON",
        },
        "voice_assistant_logs": {
            "triage_case_id": "VARCHAR",
        },
    }
    with engine.begin() as conn:
        for table, columns in additions.items():
            existing = {
                row[1]
                for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            }
            for column, column_type in columns.items():
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
