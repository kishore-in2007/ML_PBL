from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import audit, auth, doctor_services, models, schemas, storage
from app.database import get_db

router = APIRouter(prefix="/doctor", tags=["doctor"])


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


def _require_doctor_user(current_user: models.User = Depends(auth.require_roles("doctor", "admin"))):
    return current_user


def _appointment_out(item: models.Appointment) -> schemas.AppointmentOut:
    return schemas.AppointmentOut(
        id=item.id,
        patient_id=item.patient_id,
        doctor_id=item.doctor_id,
        scheduled_start=item.scheduled_start,
        scheduled_end=item.scheduled_end,
        appointment_type=_enum_value(item.appointment_type),
        status=_enum_value(item.status),
        reason=item.reason,
        meeting_url=item.meeting_url,
        created_at=item.created_at,
    )


def _notification_out(item: models.DoctorNotification) -> schemas.DoctorNotificationOut:
    return schemas.DoctorNotificationOut(
        id=item.id,
        doctor_id=item.doctor_id,
        patient_id=item.patient_id,
        triage_case_id=item.triage_case_id,
        appointment_id=item.appointment_id,
        notification_type=_enum_value(item.notification_type),
        title=item.title,
        message=item.message,
        priority=item.priority,
        is_read=bool(item.is_read),
        created_at=item.created_at,
    )


def _session_out(item: models.ConsultationSession) -> schemas.ConsultationSessionOut:
    return schemas.ConsultationSessionOut(
        id=item.id,
        appointment_id=item.appointment_id,
        patient_id=item.patient_id,
        doctor_id=item.doctor_id,
        session_status=_enum_value(item.session_status),
        connection_url=item.connection_url,
        started_at=item.started_at,
        ended_at=item.ended_at,
        summary=item.summary,
        created_at=item.created_at,
    )


def _patient_summary(db: Session, patient: models.Patient) -> schemas.DoctorPatientSummary:
    latest_image = (
        db.query(models.WoundImage)
        .filter(models.WoundImage.patient_id == patient.id)
        .order_by(models.WoundImage.uploaded_at.desc())
        .first()
    )
    classification = latest_image.classification if latest_image else None
    segmentation = latest_image.segmentation if latest_image else None
    open_cases = (
        db.query(models.TriageCase)
        .filter(
            models.TriageCase.patient_id == patient.id,
            models.TriageCase.status.in_([models.TriageStatus.pending_review, models.TriageStatus.escalated]),
        )
        .count()
    )
    next_appointment = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.patient_id == patient.id,
            models.Appointment.scheduled_start >= datetime.utcnow(),
            models.Appointment.status.in_([models.AppointmentStatus.requested, models.AppointmentStatus.confirmed]),
        )
        .order_by(models.Appointment.scheduled_start.asc())
        .first()
    )
    return schemas.DoctorPatientSummary(
        patient=patient,
        latest_risk_class=classification.risk_class.value if classification else None,
        latest_confidence=classification.confidence if classification else None,
        latest_wound_area_cm2=segmentation.wound_area_cm2 if segmentation else None,
        healing_rate=patient.current_healing_rate,
        healing_trend=patient.current_healing_trend,
        latest_image_id=latest_image.id if latest_image else None,
        latest_image_url=storage.get_presigned_url(latest_image.s3_key) if latest_image else None,
        open_triage_cases=open_cases,
        next_appointment=_appointment_out(next_appointment) if next_appointment else None,
    )


@router.get("/me", response_model=schemas.DoctorProfileOut)
def get_my_doctor_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    profile = doctor_services.ensure_doctor_profile(db, current_user)
    audit.log_action(db, current_user.id, "VIEW_OWN_DOCTOR_PROFILE", "DoctorProfile", profile.id, request=request)
    return profile


@router.put("/me", response_model=schemas.DoctorProfileOut)
def update_my_doctor_profile(
    payload: schemas.DoctorProfileCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    profile = doctor_services.ensure_doctor_profile(db, current_user)
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    audit.log_action(db, current_user.id, "UPDATE_OWN_DOCTOR_PROFILE", "DoctorProfile", profile.id, request=request)
    return profile


@router.post("/patients/assign", response_model=schemas.DoctorPatientSummary)
def assign_patient_to_me(
    payload: schemas.AssignPatientRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    patient = db.query(models.Patient).filter(models.Patient.id == payload.patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    link = (
        db.query(models.PatientDoctor)
        .filter(
            models.PatientDoctor.patient_id == payload.patient_id,
            models.PatientDoctor.doctor_id == current_user.id,
        )
        .first()
    )
    if link is None:
        link = models.PatientDoctor(patient_id=payload.patient_id, doctor_id=current_user.id, notes=payload.notes)
        db.add(link)
    else:
        link.relationship_status = "active"
        link.notes = payload.notes
    if patient.primary_doctor_id is None:
        patient.primary_doctor_id = current_user.id

    db.commit()
    audit.log_action(db, current_user.id, "ASSIGN_PATIENT_TO_DOCTOR", "Patient", patient.id, request=request)
    return _patient_summary(db, patient)


@router.get("/patients", response_model=list[schemas.DoctorPatientSummary])
def list_my_patients(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    patients = (
        db.query(models.Patient)
        .join(models.PatientDoctor, models.PatientDoctor.patient_id == models.Patient.id)
        .filter(
            models.PatientDoctor.doctor_id == current_user.id,
            models.PatientDoctor.relationship_status == "active",
        )
        .order_by(models.Patient.created_at.desc())
        .all()
    )
    audit.log_action(db, current_user.id, "VIEW_ASSIGNED_PATIENTS", request=request)
    return [_patient_summary(db, patient) for patient in patients]


@router.get("/patients/{patient_id}/summary", response_model=schemas.DoctorPatientSummary)
def get_patient_summary(
    patient_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not doctor_services.is_patient_assigned_to_doctor(db, patient_id, current_user.id):
        raise HTTPException(status_code=403, detail="Patient is not assigned to this doctor")
    audit.log_action(db, current_user.id, "VIEW_DOCTOR_PATIENT_SUMMARY", "Patient", patient.id, request=request)
    return _patient_summary(db, patient)


@router.get("/dashboard", response_model=schemas.DoctorDashboardOut)
def doctor_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    patient_ids = doctor_services.assigned_doctor_ids(db, "__none__")
    assigned_links = (
        db.query(models.PatientDoctor)
        .filter(models.PatientDoctor.doctor_id == current_user.id, models.PatientDoctor.relationship_status == "active")
        .all()
    )
    patient_ids = [link.patient_id for link in assigned_links]
    today_start, today_end = doctor_services.day_bounds(datetime.utcnow())

    total_patients = len(patient_ids)
    active_recovery_cases = (
        db.query(models.TriageCase)
        .filter(models.TriageCase.patient_id.in_(patient_ids))
        .count()
        if patient_ids else 0
    )
    todays_appointments = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.doctor_id == current_user.id,
            models.Appointment.scheduled_start >= today_start,
            models.Appointment.scheduled_start <= today_end,
        )
        .count()
    )
    urgent_alerts = (
        db.query(models.DoctorNotification)
        .filter(
            models.DoctorNotification.doctor_id == current_user.id,
            models.DoctorNotification.priority == "urgent",
            models.DoctorNotification.is_read == 0,
        )
        .count()
    )
    pending_reviews = (
        db.query(models.TriageCase)
        .filter(
            models.TriageCase.patient_id.in_(patient_ids),
            models.TriageCase.status.in_([models.TriageStatus.pending_review, models.TriageStatus.escalated]),
        )
        .count()
        if patient_ids else 0
    )
    appointments = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.doctor_id == current_user.id,
            models.Appointment.scheduled_start >= datetime.utcnow(),
        )
        .order_by(models.Appointment.scheduled_start.asc())
        .limit(5)
        .all()
    )
    priority_cases = (
        db.query(models.TriageCase)
        .filter(
            models.TriageCase.patient_id.in_(patient_ids),
            models.TriageCase.status.in_([models.TriageStatus.pending_review, models.TriageStatus.escalated]),
        )
        .order_by(models.TriageCase.created_at.desc())
        .limit(5)
        .all()
        if patient_ids else []
    )
    notifications = (
        db.query(models.DoctorNotification)
        .filter(models.DoctorNotification.doctor_id == current_user.id)
        .order_by(models.DoctorNotification.created_at.desc())
        .limit(5)
        .all()
    )
    audit.log_action(db, current_user.id, "VIEW_DOCTOR_DASHBOARD", request=request)
    return schemas.DoctorDashboardOut(
        total_patients=total_patients,
        active_recovery_cases=active_recovery_cases,
        todays_appointments=todays_appointments,
        urgent_alerts=urgent_alerts,
        pending_reviews=pending_reviews,
        upcoming_appointments=[_appointment_out(item) for item in appointments],
        priority_cases=[
            schemas.TriageOut(
                id=item.id,
                patient_id=item.patient_id,
                risk_class=item.risk_class.value,
                final_risk_score=item.final_risk_score,
                status=item.status.value,
                created_at=item.created_at,
            )
            for item in priority_cases
        ],
        notifications=[_notification_out(item) for item in notifications],
    )


@router.get("/appointments", response_model=list[schemas.AppointmentOut])
def list_appointments(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    items = (
        db.query(models.Appointment)
        .filter(models.Appointment.doctor_id == current_user.id)
        .order_by(models.Appointment.scheduled_start.asc())
        .all()
    )
    audit.log_action(db, current_user.id, "VIEW_DOCTOR_APPOINTMENTS", request=request)
    return [_appointment_out(item) for item in items]


@router.post("/appointments", response_model=schemas.AppointmentOut)
def create_appointment(
    payload: schemas.AppointmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    doctor_id = payload.doctor_id or current_user.id
    if doctor_id != current_user.id and current_user.role != models.UserRole.admin:
        raise HTTPException(status_code=403, detail="Doctors can only create appointments for themselves")
    patient = db.query(models.Patient).filter(models.Patient.id == payload.patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    conflict = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.doctor_id == doctor_id,
            models.Appointment.status.in_([models.AppointmentStatus.requested, models.AppointmentStatus.confirmed]),
            models.Appointment.scheduled_start < payload.scheduled_end,
            models.Appointment.scheduled_end > payload.scheduled_start,
        )
        .first()
    )
    if conflict is not None:
        raise HTTPException(status_code=409, detail="Doctor already has an appointment in this time window")
    if not doctor_services.is_patient_assigned_to_doctor(db, patient.id, doctor_id):
        db.add(models.PatientDoctor(patient_id=patient.id, doctor_id=doctor_id, notes="Auto-assigned from appointment"))
    if patient.primary_doctor_id is None:
        patient.primary_doctor_id = doctor_id
    patient.next_appointment_date = payload.scheduled_start
    if payload.appointment_type == models.AppointmentType.video.value:
        patient.doctor_consultancy_date = payload.scheduled_start

    item = models.Appointment(
        patient_id=patient.id,
        doctor_id=doctor_id,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        appointment_type=payload.appointment_type,
        status=models.AppointmentStatus.confirmed.value,
        reason=payload.reason,
        meeting_url=payload.meeting_url,
        created_by_user_id=current_user.id,
    )
    db.add(item)
    db.flush()
    doctor_services.create_doctor_notification(
        db,
        doctor_id=doctor_id,
        notification_type=models.NotificationType.appointment.value,
        title="Appointment scheduled",
        message=payload.reason,
        patient_id=patient.id,
        appointment_id=item.id,
        priority="normal",
    )
    db.commit()
    db.refresh(item)
    audit.log_action(db, current_user.id, "CREATE_APPOINTMENT", "Appointment", item.id, request=request)
    return _appointment_out(item)


@router.patch("/appointments/{appointment_id}", response_model=schemas.AppointmentOut)
def update_appointment(
    appointment_id: str,
    payload: schemas.AppointmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    item = (
        db.query(models.Appointment)
        .filter(models.Appointment.id == appointment_id, models.Appointment.doctor_id == current_user.id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Appointment not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    audit.log_action(db, current_user.id, "UPDATE_APPOINTMENT", "Appointment", item.id, request=request)
    return _appointment_out(item)


@router.get("/notifications", response_model=list[schemas.DoctorNotificationOut])
def list_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    items = (
        db.query(models.DoctorNotification)
        .filter(models.DoctorNotification.doctor_id == current_user.id)
        .order_by(models.DoctorNotification.created_at.desc())
        .all()
    )
    audit.log_action(db, current_user.id, "VIEW_DOCTOR_NOTIFICATIONS", request=request)
    return [_notification_out(item) for item in items]


@router.patch("/notifications/{notification_id}/read", response_model=schemas.DoctorNotificationOut)
def mark_notification_read(
    notification_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    item = (
        db.query(models.DoctorNotification)
        .filter(models.DoctorNotification.id == notification_id, models.DoctorNotification.doctor_id == current_user.id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    item.is_read = 1
    db.commit()
    db.refresh(item)
    audit.log_action(db, current_user.id, "MARK_NOTIFICATION_READ", "DoctorNotification", item.id, request=request)
    return _notification_out(item)


@router.post("/sessions", response_model=schemas.ConsultationSessionOut)
def create_session(
    payload: schemas.ConsultationSessionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    if not doctor_services.is_patient_assigned_to_doctor(db, payload.patient_id, current_user.id):
        raise HTTPException(status_code=403, detail="Patient is not assigned to this doctor")
    item = models.ConsultationSession(
        appointment_id=payload.appointment_id,
        patient_id=payload.patient_id,
        doctor_id=current_user.id,
        connection_url=payload.connection_url,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    audit.log_action(db, current_user.id, "CREATE_CONSULTATION_SESSION", "ConsultationSession", item.id, request=request)
    return _session_out(item)


@router.get("/sessions", response_model=list[schemas.ConsultationSessionOut])
def list_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    items = (
        db.query(models.ConsultationSession)
        .filter(models.ConsultationSession.doctor_id == current_user.id)
        .order_by(models.ConsultationSession.created_at.desc())
        .all()
    )
    audit.log_action(db, current_user.id, "VIEW_CONSULTATION_SESSIONS", request=request)
    return [_session_out(item) for item in items]


@router.patch("/sessions/{session_id}", response_model=schemas.ConsultationSessionOut)
def update_session(
    session_id: str,
    payload: schemas.ConsultationSessionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    item = (
        db.query(models.ConsultationSession)
        .filter(models.ConsultationSession.id == session_id, models.ConsultationSession.doctor_id == current_user.id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Session not found")
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("session_status") == models.SessionStatus.live.value and item.started_at is None:
        item.started_at = datetime.utcnow()
    if updates.get("session_status") == models.SessionStatus.completed.value and item.ended_at is None:
        item.ended_at = datetime.utcnow()
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    audit.log_action(db, current_user.id, "UPDATE_CONSULTATION_SESSION", "ConsultationSession", item.id, request=request)
    return _session_out(item)


@router.get("/wound-images/{image_id}", response_model=schemas.WoundImageDetailOut)
def wound_image_detail(
    image_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    image = db.query(models.WoundImage).filter(models.WoundImage.id == image_id).first()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")
    if not doctor_services.is_patient_assigned_to_doctor(db, image.patient_id, current_user.id):
        raise HTTPException(status_code=403, detail="Patient is not assigned to this doctor")
    classification = image.classification
    segmentation = image.segmentation
    audit.log_action(db, current_user.id, "VIEW_WOUND_IMAGE_DETAIL", "WoundImage", image.id, request=request)
    return schemas.WoundImageDetailOut(
        image_id=image.id,
        patient_id=image.patient_id,
        uploaded_at=image.uploaded_at,
        image_url=storage.get_presigned_url(image.s3_key),
        risk_class=classification.risk_class.value if classification else None,
        confidence=classification.confidence if classification else None,
        needs_human_review=bool(classification.needs_human_review) if classification else None,
        raw_scores=classification.raw_scores if classification else None,
        wound_area_px=segmentation.wound_area_px if segmentation else None,
        wound_area_cm2=segmentation.wound_area_cm2 if segmentation else None,
        percent_change_from_previous=segmentation.percent_change_from_previous if segmentation else None,
        segmentation_model_used=segmentation.model_used if segmentation else None,
        segmentation_model_confidence=segmentation.model_confidence if segmentation else None,
        segmentation_prompt_box=segmentation.prompt_box if segmentation else None,
        mask_overlay_url=storage.get_presigned_url(image.mask_overlay_key) if image.mask_overlay_key else None,
    )


@router.post("/clinical-notes", response_model=schemas.ClinicalNoteOut)
def add_clinical_note(
    payload: schemas.ClinicalNoteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    if not doctor_services.is_patient_assigned_to_doctor(db, payload.patient_id, current_user.id):
        raise HTTPException(status_code=403, detail="Patient is not assigned to this doctor")
    note = models.ClinicalNote(
        patient_id=payload.patient_id,
        doctor_id=current_user.id,
        image_id=payload.image_id,
        triage_case_id=payload.triage_case_id,
        note=payload.note,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    audit.log_action(db, current_user.id, "ADD_CLINICAL_NOTE", "ClinicalNote", note.id, request=request)
    return schemas.ClinicalNoteOut(
        id=note.id,
        patient_id=note.patient_id,
        doctor_id=note.doctor_id,
        image_id=note.image_id,
        triage_case_id=note.triage_case_id,
        note=note.note,
        created_at=note.created_at,
    )


@router.patch("/daily-wound-logs/{daily_log_id}/review", response_model=schemas.DailyWoundReviewOut)
def review_daily_wound_log(
    daily_log_id: str,
    payload: schemas.DailyWoundReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    allowed_statuses = {"pending", "reviewed", "escalated", "resolved", "needs_patient_retake"}
    if payload.doctor_review_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid doctor review status")

    log = db.query(models.DailyWoundLog).filter(models.DailyWoundLog.id == daily_log_id).first()
    if log is None:
        raise HTTPException(status_code=404, detail="Daily wound log not found")
    if not doctor_services.is_patient_assigned_to_doctor(db, log.patient_id, current_user.id):
        raise HTTPException(status_code=403, detail="Patient is not assigned to this doctor")

    log.doctor_review_status = payload.doctor_review_status
    log.reviewed_by_doctor_id = current_user.id
    log.doctor_review_note = payload.doctor_review_note
    log.doctor_reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(log)
    audit.log_action(db, current_user.id, "REVIEW_DAILY_WOUND_LOG", "DailyWoundLog", log.id, request=request)
    return schemas.DailyWoundReviewOut(
        id=log.id,
        doctor_review_status=log.doctor_review_status,
        reviewed_by_doctor_id=log.reviewed_by_doctor_id,
        doctor_review_note=log.doctor_review_note,
        doctor_reviewed_at=log.doctor_reviewed_at,
    )


@router.post("/triage/{case_id}/review", response_model=schemas.TriageOut)
def review_triage_case(
    case_id: str,
    status_value: str = "reviewed",
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_doctor_user),
):
    case = db.query(models.TriageCase).filter(models.TriageCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Triage case not found")
    if not doctor_services.is_patient_assigned_to_doctor(db, case.patient_id, current_user.id):
        raise HTTPException(status_code=403, detail="Patient is not assigned to this doctor")
    if status_value not in {item.value for item in models.TriageStatus}:
        raise HTTPException(status_code=400, detail="Invalid triage status")
    case.status = status_value
    case.assigned_clinician_id = current_user.id
    if status_value == models.TriageStatus.reviewed.value:
        case.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(case)
    audit.log_action(db, current_user.id, "REVIEW_TRIAGE_CASE", "TriageCase", case.id, request=request)
    return schemas.TriageOut(
        id=case.id,
        patient_id=case.patient_id,
        risk_class=case.risk_class.value,
        final_risk_score=case.final_risk_score,
        status=case.status.value,
        created_at=case.created_at,
    )
