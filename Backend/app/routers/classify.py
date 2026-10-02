from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth, audit, doctor_services, storage
from app.ml.classify import classify_image

router = APIRouter(tags=["classify"])


@router.post("/classify", response_model=schemas.ClassificationOut)
def classify(
    request: Request,
    patient_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    image_bytes = file.file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image upload")

    from app.config import settings as cfg

    s3_key = storage.upload_image_bytes(image_bytes, patient_id, file.content_type or "image/jpeg")

    wound_image = models.WoundImage(
        patient_id=patient_id,
        s3_key=s3_key,
        s3_bucket=cfg.S3_BUCKET_NAME,
    )
    db.add(wound_image)
    db.commit()
    db.refresh(wound_image)

    result = classify_image(image_bytes)

    classification = models.Classification(
        image_id=wound_image.id,
        risk_class=result["risk_class"],
        confidence=result["confidence"],
        needs_human_review=1 if result["needs_human_review"] else 0,
        raw_scores=result["raw_scores"],
    )
    db.add(classification)
    for doctor_id in doctor_services.assigned_doctor_ids(db, patient_id):
        doctor_services.create_doctor_notification(
            db,
            doctor_id=doctor_id,
            notification_type=models.NotificationType.new_wound_image.value,
            title="New wound image submitted",
            message=f"Risk class: {result['risk_class']}; confidence: {result['confidence']}",
            patient_id=patient_id,
            priority="urgent" if result["risk_class"] == models.RiskClass.urgent.value else "normal",
        )
    db.commit()
    db.refresh(classification)

    audit.log_action(
        db, current_user.id, "CLASSIFY_IMAGE", "WoundImage", wound_image.id,
        detail=f"risk_class={result['risk_class']} confidence={result['confidence']}",
        request=request,
    )

    return schemas.ClassificationOut(
        image_id=wound_image.id,
        risk_class=classification.risk_class.value,
        confidence=classification.confidence,
        needs_human_review=bool(classification.needs_human_review),
        raw_scores=classification.raw_scores,
        image_url=storage.get_presigned_url(wound_image.s3_key),
    )
