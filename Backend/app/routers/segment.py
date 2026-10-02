from fastapi import APIRouter, Depends, HTTPException, Request

from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth, audit, storage
from app.ml.segment import segment_image

router = APIRouter(tags=["segment"])


@router.post("/segment", response_model=schemas.SegmentationOut)
def segment(
    request: Request,
    image_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    wound_image = db.query(models.WoundImage).filter(models.WoundImage.id == image_id).first()
    if not wound_image:
        raise HTTPException(status_code=404, detail="Image not found")

    patient = db.query(models.Patient).filter(models.Patient.id == wound_image.patient_id).first()

    # Find the most recent previous segmentation for this patient to compute % change
    previous = (
        db.query(models.Segmentation)
        .join(models.WoundImage, models.Segmentation.image_id == models.WoundImage.id)
        .filter(
            models.WoundImage.patient_id == wound_image.patient_id,
            models.WoundImage.id != image_id,
        )
        .order_by(models.Segmentation.created_at.desc())
        .first()
    )
    previous_area_cm2 = previous.wound_area_cm2 if previous else None

    image_bytes = storage.download_image_bytes(wound_image.s3_key)
    result = segment_image(
        image_bytes,
        reference_marker_cm=patient.reference_marker_cm if patient else 2.0,
        previous_area_cm2=previous_area_cm2,
    )

    segmentation = models.Segmentation(
        image_id=image_id,
        wound_area_px=result["wound_area_px"],
        wound_area_cm2=result["wound_area_cm2"],
        percent_change_from_previous=result["percent_change_from_previous"],
        model_used=result.get("model_used"),
        model_confidence=result.get("model_confidence"),
        prompt_box=result.get("prompt_box_xyxy"),
    )
    db.add(segmentation)
    db.commit()
    db.refresh(segmentation)

    audit.log_action(
        db, current_user.id, "SEGMENT_IMAGE", "WoundImage", image_id,
        detail=f"area_cm2={result['wound_area_cm2']}", request=request,
    )

    return schemas.SegmentationOut(
        image_id=image_id,
        wound_area_px=segmentation.wound_area_px,
        wound_area_cm2=segmentation.wound_area_cm2,
        percent_change_from_previous=segmentation.percent_change_from_previous,
        model_used=segmentation.model_used,
        model_confidence=segmentation.model_confidence,
        prompt_box=segmentation.prompt_box,
    )
