from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth, audit, doctor_services, storage
from app.triage import compute_triage

router = APIRouter(tags=["triage"])


@router.post("/triage", response_model=schemas.TriageOut)
def triage(
    payload: schemas.TriageRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    patient = db.query(models.Patient).filter(models.Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    risk_class, confidence, needs_human_review = None, None, False
    if payload.image_id:
        classification = (
            db.query(models.Classification)
            .filter(models.Classification.image_id == payload.image_id)
            .first()
        )
        if classification:
            risk_class = classification.risk_class.value
            confidence = classification.confidence
            needs_human_review = bool(classification.needs_human_review)

    symptom_dict = payload.symptom_data.model_dump() if payload.symptom_data else None
    result = compute_triage(risk_class, confidence, needs_human_review, symptom_dict)

    case = models.TriageCase(
        patient_id=payload.patient_id,
        image_id=payload.image_id,
        risk_class=result["risk_class"],
        final_risk_score=result["final_risk_score"],
        status=result["status"],
        symptom_data=symptom_dict,
    )
    db.add(case)
    db.flush()
    if result["status"] in {
        models.TriageStatus.pending_review.value,
        models.TriageStatus.escalated.value,
    }:
        doctor_services.notify_assigned_doctors_for_triage(db, case)
    db.commit()
    db.refresh(case)

    audit.log_action(
        db, current_user.id, "TRIAGE_CASE_CREATED", "TriageCase", case.id,
        detail=f"status={result['status']} score={result['final_risk_score']}",
        request=request,
    )

    return schemas.TriageOut(
        id=case.id,
        patient_id=case.patient_id,
        risk_class=case.risk_class.value,
        final_risk_score=case.final_risk_score,
        status=case.status.value,
        created_at=case.created_at,
    )


@router.get("/triage/queue", response_model=list[schemas.TriageOut])
def get_queue(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("nurse", "doctor", "admin")),
):
    """Priority-sorted clinician case queue — Urgent first (spec section 6)."""
    priority = {"Urgent": 0, "Mild Concern": 1, "Normal": 2}
    cases = (
        db.query(models.TriageCase)
        .filter(models.TriageCase.status.in_(["pending_review", "escalated"]))
        .order_by(models.TriageCase.created_at.desc())
        .all()
    )
    cases.sort(key=lambda c: priority.get(c.risk_class.value, 3))

    audit.log_action(db, current_user.id, "VIEW_TRIAGE_QUEUE", request=request)

    return [
        schemas.TriageOut(
            id=c.id, patient_id=c.patient_id, risk_class=c.risk_class.value,
            final_risk_score=c.final_risk_score, status=c.status.value, created_at=c.created_at,
        )
        for c in cases
    ]


@router.get("/patient/{patient_id}/history", response_model=list[schemas.HistoryItem])
def patient_history(
    patient_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    images = (
        db.query(models.WoundImage)
        .filter(models.WoundImage.patient_id == patient_id)
        .order_by(models.WoundImage.uploaded_at.asc())
        .all()
    )

    audit.log_action(
        db, current_user.id, "VIEW_PATIENT_HISTORY", "Patient", patient_id, request=request,
    )

    history = []
    for img in images:
        c = img.classification
        s = img.segmentation
        daily_log = img.daily_log
        history.append(
            schemas.HistoryItem(
                image_id=img.id,
                uploaded_at=img.uploaded_at,
                risk_class=c.risk_class.value if c else None,
                confidence=c.confidence if c else None,
                wound_area_cm2=s.wound_area_cm2 if s else None,
                percent_change_from_previous=s.percent_change_from_previous if s else None,
                healing_rate=daily_log.healing_rate if daily_log else None,
                healing_trend=daily_log.healing_trend.value if daily_log and daily_log.healing_trend else None,
                image_url=storage.get_presigned_url(img.s3_key),
            )
        )
    return history
