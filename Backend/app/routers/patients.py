import json
import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app import audit, auth, models, recovery, schemas
from app.database import get_db
import voice as voice_service

router = APIRouter(prefix="/patients", tags=["patients"])
logger = logging.getLogger(__name__)


def _role_value(user: models.User) -> str:
    return user.role.value if hasattr(user.role, "value") else str(user.role)


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


def _appointment_out(item: models.Appointment) -> schemas.AppointmentOut:
    return schemas.AppointmentOut(
        id=item.id,
        patient_id=item.patient_id,
        doctor_id=item.doctor_id,
        scheduled_start=item.scheduled_start,
        scheduled_end=item.scheduled_end,
        appointment_type=item.appointment_type.value if hasattr(item.appointment_type, "value") else item.appointment_type,
        status=item.status.value if hasattr(item.status, "value") else item.status,
        reason=item.reason,
        meeting_url=item.meeting_url,
        created_at=item.created_at,
    )


def _metric_out(item: models.HealingMetric) -> schemas.HealingMetricOut:
    return schemas.HealingMetricOut(
        id=item.id,
        patient_id=item.patient_id,
        image_id=item.image_id,
        daily_log_id=item.daily_log_id,
        measured_at=item.measured_at,
        wound_area_cm2=item.wound_area_cm2,
        previous_wound_area_cm2=item.previous_wound_area_cm2,
        comparison_source=item.comparison_source,
        percent_change_from_previous=item.percent_change_from_previous,
        healing_rate=item.healing_rate,
        healing_trend=item.healing_trend.value if hasattr(item.healing_trend, "value") else item.healing_trend,
        model_summary=item.model_summary,
    )


def _get_or_create_patient(db: Session, current_user: models.User) -> models.Patient:
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if patient is None:
        patient = models.Patient(user_id=current_user.id)
        db.add(patient)
        db.commit()
        db.refresh(patient)
    return patient


def _reminder_out(item: models.PatientReminder) -> schemas.PatientReminderOut:
    return schemas.PatientReminderOut(
        id=item.id,
        patient_id=item.patient_id,
        title=item.title,
        reminder_type=item.reminder_type,
        schedule_time=item.schedule_time,
        schedule_label=item.schedule_label,
        notes=item.notes,
        is_enabled=bool(item.is_enabled),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _report_out(item: models.SharedRecoveryReport) -> schemas.SharedRecoveryReportOut:
    return schemas.SharedRecoveryReportOut(
        id=item.id,
        patient_id=item.patient_id,
        doctor_id=item.doctor_id,
        title=item.title,
        report_type=item.report_type,
        summary=item.summary,
        payload=item.payload,
        created_at=item.created_at,
    )


def _voice_out(item: models.VoiceAssistantLog) -> schemas.VoiceAssistantOut:
    return schemas.VoiceAssistantOut(
        id=item.id,
        patient_id=item.patient_id,
        user_message=item.user_message,
        assistant_response=item.assistant_response,
        intent=item.intent,
        urgency=item.urgency,
        triage_case_id=item.triage_case_id,
        created_at=item.created_at,
    )


def _doctor_member_out(db: Session, doctor_id: str, relationship_status: str | None = None, assigned_at: datetime | None = None) -> schemas.CareTeamMemberOut:
    user = db.query(models.User).filter(models.User.id == doctor_id).first()
    profile = db.query(models.DoctorProfile).filter(models.DoctorProfile.user_id == doctor_id).first()
    return schemas.CareTeamMemberOut(
        doctor_id=doctor_id,
        name=user.full_name if user else None,
        email=user.email if user else None,
        specialization=profile.specialization if profile else None,
        hospital_name=profile.hospital_name if profile else None,
        phone_number=profile.phone_number if profile else None,
        bio=profile.bio if profile else None,
        relationship_status=relationship_status,
        assigned_at=assigned_at,
    )


def _seed_default_reminders(db: Session, patient: models.Patient):
    existing_count = db.query(models.PatientReminder).filter(models.PatientReminder.patient_id == patient.id).count()
    if existing_count:
        return
    defaults = [
        ("Medicine Reminder", "medication", "08:00", "Daily at 8:00 AM", "Take prescribed medication on time."),
        ("Dressing Change", "dressing", "14:00", "Daily at 2:00 PM", "Change dressing using sterile care instructions."),
        ("Wound Photo", "wound_photo", "19:00", "Daily at 7:00 PM", "Upload today's wound photo for AI review."),
    ]
    for title, reminder_type, schedule_time, schedule_label, notes in defaults:
        db.add(
            models.PatientReminder(
                patient_id=patient.id,
                title=title,
                reminder_type=reminder_type,
                schedule_time=schedule_time,
                schedule_label=schedule_label,
                notes=notes,
                is_enabled=1,
            )
        )
    db.commit()


def _latest_daily_context(db: Session, patient_id: str) -> models.DailyWoundLog | None:
    return (
        db.query(models.DailyWoundLog)
        .filter(models.DailyWoundLog.patient_id == patient_id)
        .order_by(models.DailyWoundLog.created_at.desc())
        .first()
    )


def _voice_response(db: Session, patient: models.Patient, message: str) -> tuple[str, str, str]:
    text = message.lower()
    latest = _latest_daily_context(db, patient.id)
    urgent_terms = ["bleeding", "fever", "pus", "severe pain", "emergency", "redness spreading", "smell", "swelling"]
    if any(term in text for term in urgent_terms):
        return (
            "emergency_guidance",
            "urgent",
            "Your message includes symptoms that need clinical attention. I have alerted your care team. If symptoms are severe or rapidly worsening, contact emergency care immediately.",
        )
    if "wound" in text or "healing" in text or "status" in text:
        if latest:
            return (
                "wound_status",
                "normal",
                f"Your latest upload is classified as {latest.risk_class.value if hasattr(latest.risk_class, 'value') else latest.risk_class or 'not classified'} with a healing trend of {latest.healing_trend.value if hasattr(latest.healing_trend, 'value') else latest.healing_trend or 'not available'}. Healing rate is {latest.healing_rate:.0f}%." if latest.healing_rate is not None else "Your latest wound upload is available, but healing rate is not available yet.",
            )
        return ("wound_status", "normal", "No daily wound image has been uploaded yet. Please upload today's photo so the AI model can evaluate progress.")
    if "medicine" in text or "medication" in text:
        return ("medication", "normal", "Your medication reminder can be managed from the Reminders page. Keep medication adherence enabled when you upload symptoms.")
    if "doctor" in text or "contact" in text:
        return ("contact_doctor", "normal", "Open Care Team to call your clinic, share a recovery report, or book a follow-up appointment.")
    if "pain" in text:
        return ("pain", "normal", "Track pain during your daily wound upload. If pain is severe, increasing, or paired with fever, contact your care team.")
    return ("general", "normal", "I can help with wound status, reminders, pain tracking, medication, or contacting your doctor.")


def _create_urgent_voice_triage(db: Session, patient: models.Patient, message: str) -> str:
    latest = _latest_daily_context(db, patient.id)
    triage_case = models.TriageCase(
        patient_id=patient.id,
        image_id=latest.image_id if latest else None,
        risk_class=models.RiskClass.urgent,
        final_risk_score=95.0,
        status=models.TriageStatus.escalated,
        symptom_data={"voice_transcript": message, "emergency_keywords_detected": True},
        assigned_clinician_id=patient.primary_doctor_id,
    )
    db.add(triage_case)
    db.flush()
    doctor_ids = {patient.primary_doctor_id} if patient.primary_doctor_id else set()
    doctor_ids.update(
        row.doctor_id
        for row in db.query(models.PatientDoctor)
        .filter(models.PatientDoctor.patient_id == patient.id, models.PatientDoctor.relationship_status == "active")
        .all()
    )
    for doctor_id in doctor_ids:
        if doctor_id:
            db.add(
                models.DoctorNotification(
                    doctor_id=doctor_id,
                    patient_id=patient.id,
                    triage_case_id=triage_case.id,
                    notification_type=models.NotificationType.urgent_triage,
                    title="Emergency voice command alert",
                    message=message,
                    priority="urgent",
                )
            )
    return triage_case.id


def _execute_voice_command(db: Session, patient: models.Patient, command: voice_service.VoiceCommand, transcript: str) -> tuple[str, str, dict | None, str | None]:
    action = command.action
    triage_case_id = None

    if action == "escalate_triage":
        triage_case_id = _create_urgent_voice_triage(db, patient, transcript)
        return (
            "urgent",
            "I created an urgent care alert from your voice message. If symptoms are severe or rapidly worsening, seek emergency care immediately.",
            {"triage_case_id": triage_case_id, "route": command.route},
            triage_case_id,
        )

    if action == "read_wound_status":
        latest = _latest_daily_context(db, patient.id)
        if latest is None:
            return (
                "normal",
                "No daily wound image has been uploaded yet. I opened the capture page so you can upload today's photo.",
                {"route": "/patient/capture"},
                None,
            )
        risk = _enum_value(latest.risk_class) or "not classified"
        trend = _enum_value(latest.healing_trend) or "not available"
        rate_text = f" Healing rate is {latest.healing_rate:.0f}%." if latest.healing_rate is not None else ""
        return (
            "normal",
            f"Your latest wound status is {risk}. Healing trend is {trend}.{rate_text}",
            {"latest_daily_log": recovery.daily_log_to_schema(latest), "route": command.route},
            None,
        )

    if action == "read_recovery_overview":
        latest = _latest_daily_context(db, patient.id)
        metrics_count = db.query(models.HealingMetric).filter(models.HealingMetric.patient_id == patient.id).count()
        trend = _enum_value(latest.healing_trend) if latest else patient.current_healing_trend
        response = f"Your recovery overview is ready. Current healing trend is {trend or 'not available'}, with {metrics_count} healing measurements recorded."
        return ("normal", response, {"metrics_count": metrics_count, "route": command.route}, None)

    if action == "read_reminders":
        _seed_default_reminders(db, patient)
        reminders = (
            db.query(models.PatientReminder)
            .filter(models.PatientReminder.patient_id == patient.id, models.PatientReminder.is_enabled == 1)
            .order_by(models.PatientReminder.schedule_time.asc())
            .limit(5)
            .all()
        )
        if not reminders:
            return ("normal", "You do not have active reminders yet. I opened the reminders page.", {"reminders": [], "route": command.route}, None)
        spoken = "; ".join(f"{item.title} at {item.schedule_label or item.schedule_time}" for item in reminders)
        return ("normal", f"Your active reminders are: {spoken}.", {"reminders": [_reminder_out(item).model_dump(mode="json") for item in reminders], "route": command.route}, None)

    if action == "create_reminder":
        params = command.params
        reminder = models.PatientReminder(
            patient_id=patient.id,
            title=params.get("title") or "Voice Reminder",
            reminder_type=params.get("reminder_type") or "care",
            schedule_time=params.get("schedule_time") or "08:00",
            schedule_label=params.get("schedule_label"),
            notes=params.get("notes"),
            is_enabled=1,
        )
        db.add(reminder)
        db.flush()
        response = f"I created {reminder.title} for {reminder.schedule_label or reminder.schedule_time}."
        return ("normal", response, {"reminder": _reminder_out(reminder).model_dump(mode="json"), "route": command.route}, None)

    if action == "read_care_team":
        links_count = db.query(models.PatientDoctor).filter(models.PatientDoctor.patient_id == patient.id, models.PatientDoctor.relationship_status == "active").count()
        response = "I opened your care team page. "
        response += f"You have {links_count} active clinician contact listed." if links_count == 1 else f"You have {links_count} active clinician contacts listed."
        return ("normal", response, {"active_care_team_members": links_count, "route": command.route}, None)

    if action == "share_report":
        latest = _latest_daily_context(db, patient.id)
        summary = (
            f"Latest risk: {_enum_value(latest.risk_class)}; healing trend: {_enum_value(latest.healing_trend)}"
            if latest
            else "Recovery report generated before a daily upload."
        )
        report = models.SharedRecoveryReport(
            patient_id=patient.id,
            doctor_id=patient.primary_doctor_id,
            title=command.params.get("title") or "Voice Requested Recovery Report",
            report_type="recovery_progress",
            summary=summary,
            payload={"source": "voice_command", "latest_daily_log_id": latest.id if latest else None},
        )
        db.add(report)
        if patient.primary_doctor_id:
            db.add(
                models.DoctorNotification(
                    doctor_id=patient.primary_doctor_id,
                    patient_id=patient.id,
                    notification_type=models.NotificationType.system,
                    title="Recovery report shared by voice",
                    message=summary,
                    priority="normal",
                )
            )
        db.flush()
        return ("normal", "I shared your latest recovery report with your care team.", {"report": _report_out(report).model_dump(mode="json"), "route": command.route}, None)

    if action == "read_profile":
        return (
            "normal",
            f"I opened your profile. Surgery type is {patient.surgery_type or 'not set'} and recovery goal is {patient.recovery_goal or 'not set'}.",
            {"patient": schemas.PatientOut.model_validate(patient).model_dump(mode="json"), "route": command.route},
            None,
        )

    if action == "navigate":
        if command.intent == "upload_wound_photo":
            return ("normal", "I opened daily wound photo capture. Choose or capture an image, then upload and analyze.", {"route": command.route, "requires_file": True}, None)
        return ("normal", f"Opening {command.label}.", {"route": command.route}, None)

    return (
        "normal",
        "I can open wound capture, read wound status, show recovery trends, manage reminders, contact your doctor, share reports, or escalate urgent symptoms.",
        {"capabilities": voice_service.COMMAND_CAPABILITIES, "route": command.route},
        None,
    )


def _audio_url_for_path(path: str | None) -> str | None:
    if not path:
        return None
    normalized = path.replace("\\", "/")
    marker = "uploads/"
    if marker in normalized:
        return "/media/" + normalized.split(marker, 1)[1]
    return None


def _handle_voice_command(
    transcript: str,
    speak: bool,
    request: Request,
    db: Session,
    current_user: models.User,
) -> schemas.VoiceCommandOut:
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users can use voice commands")
    patient = _get_or_create_patient(db, current_user)
    transcript = voice_service.normalize_text(transcript)
    if not transcript:
        raise HTTPException(status_code=400, detail="No voice command transcript was detected")

    command = voice_service.parse_patient_command(transcript)
    urgency, response, result, triage_case_id = _execute_voice_command(db, patient, command, transcript)

    log = models.VoiceAssistantLog(
        patient_id=patient.id,
        user_message=transcript,
        assistant_response=response,
        intent=command.intent,
        urgency=urgency,
        triage_case_id=triage_case_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    audio_url = None
    if speak:
        audio_url = _audio_url_for_path(voice_service.synthesize_speech(response))

    audit.log_action(
        db,
        current_user.id,
        "VOICE_COMMAND_EXECUTED",
        "VoiceAssistantLog",
        log.id,
        detail=f"intent={command.intent} action={command.action} urgency={urgency}",
        request=request,
    )
    return schemas.VoiceCommandOut(
        transcript=transcript,
        assistant_response=response,
        intent=command.intent,
        urgency=urgency,
        command=command.to_dict(),
        result=result,
        audio_url=audio_url,
        message_log=_voice_out(log),
    )


@router.get("/me", response_model=schemas.PatientOut)
def get_my_patient_profile(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users have a patient profile")

    patient = (
        db.query(models.Patient)
        .filter(models.Patient.user_id == current_user.id)
        .first()
    )
    if patient is None:
        patient = models.Patient(user_id=current_user.id)
        db.add(patient)
        db.commit()
        db.refresh(patient)

    audit.log_action(db, current_user.id, "VIEW_OWN_PATIENT_PROFILE", "Patient", patient.id, request=request)
    return patient


@router.put("/me", response_model=schemas.PatientOut)
def update_my_patient_profile(
    payload: schemas.PatientCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users have a patient profile")

    patient = (
        db.query(models.Patient)
        .filter(models.Patient.user_id == current_user.id)
        .first()
    )
    if patient is None:
        patient = models.Patient(user_id=current_user.id)
        db.add(patient)

    for field, value in payload.model_dump().items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    audit.log_action(db, current_user.id, "UPDATE_OWN_PATIENT_PROFILE", "Patient", patient.id, request=request)
    return patient


@router.get("/me/reminders", response_model=list[schemas.PatientReminderOut])
def list_my_reminders(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users can view reminders")
    patient = _get_or_create_patient(db, current_user)
    _seed_default_reminders(db, patient)
    reminders = (
        db.query(models.PatientReminder)
        .filter(models.PatientReminder.patient_id == patient.id)
        .order_by(models.PatientReminder.schedule_time.asc(), models.PatientReminder.created_at.asc())
        .all()
    )
    audit.log_action(db, current_user.id, "VIEW_REMINDERS", "Patient", patient.id, request=request)
    return [_reminder_out(item) for item in reminders]


@router.post("/me/reminders", response_model=schemas.PatientReminderOut)
def create_my_reminder(
    payload: schemas.PatientReminderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users can create reminders")
    patient = _get_or_create_patient(db, current_user)
    reminder = models.PatientReminder(
        patient_id=patient.id,
        title=payload.title,
        reminder_type=payload.reminder_type,
        schedule_time=payload.schedule_time,
        schedule_label=payload.schedule_label,
        notes=payload.notes,
        is_enabled=1 if payload.is_enabled else 0,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    audit.log_action(db, current_user.id, "CREATE_REMINDER", "PatientReminder", reminder.id, request=request)
    return _reminder_out(reminder)


@router.patch("/me/reminders/{reminder_id}", response_model=schemas.PatientReminderOut)
def update_my_reminder(
    reminder_id: str,
    payload: schemas.PatientReminderUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users can update reminders")
    patient = _get_or_create_patient(db, current_user)
    reminder = (
        db.query(models.PatientReminder)
        .filter(models.PatientReminder.id == reminder_id, models.PatientReminder.patient_id == patient.id)
        .first()
    )
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "is_enabled":
            setattr(reminder, field, 1 if value else 0)
        else:
            setattr(reminder, field, value)
    reminder.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(reminder)
    audit.log_action(db, current_user.id, "UPDATE_REMINDER", "PatientReminder", reminder.id, request=request)
    return _reminder_out(reminder)


@router.get("/me/care-team", response_model=schemas.CareTeamOverviewOut)
def get_my_care_team(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users can view care team")
    patient = _get_or_create_patient(db, current_user)
    links = (
        db.query(models.PatientDoctor)
        .filter(models.PatientDoctor.patient_id == patient.id, models.PatientDoctor.relationship_status == "active")
        .order_by(models.PatientDoctor.assigned_at.desc())
        .all()
    )
    care_team = [_doctor_member_out(db, link.doctor_id, link.relationship_status, link.assigned_at) for link in links]
    primary = _doctor_member_out(db, patient.primary_doctor_id) if patient.primary_doctor_id else (care_team[0] if care_team else None)
    appointments = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.patient_id == patient.id,
            models.Appointment.scheduled_start >= datetime.utcnow(),
            models.Appointment.status.in_([models.AppointmentStatus.requested, models.AppointmentStatus.confirmed]),
        )
        .order_by(models.Appointment.scheduled_start.asc())
        .limit(5)
        .all()
    )
    reports = (
        db.query(models.SharedRecoveryReport)
        .filter(models.SharedRecoveryReport.patient_id == patient.id)
        .order_by(models.SharedRecoveryReport.created_at.desc())
        .limit(5)
        .all()
    )
    audit.log_action(db, current_user.id, "VIEW_CARE_TEAM", "Patient", patient.id, request=request)
    return schemas.CareTeamOverviewOut(
        patient=patient,
        primary_doctor=primary,
        care_team=care_team,
        upcoming_appointments=[_appointment_out(item) for item in appointments],
        recent_reports=[_report_out(item) for item in reports],
        emergency_guidance="For severe pain, bleeding, fever, spreading redness, or urgent infection symptoms, contact your care team immediately or seek emergency care.",
    )


@router.get("/doctors", response_model=list[schemas.CareTeamMemberOut])
def list_available_doctors(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    doctors = db.query(models.User).filter(models.User.role == models.UserRole.doctor).all()
    return [_doctor_member_out(db, doc.id) for doc in doctors]


@router.post("/me/appointments", response_model=schemas.AppointmentOut)
def create_patient_appointment(
    payload: schemas.AppointmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users can book appointments")
    patient = _get_or_create_patient(db, current_user)
    doctor_id = payload.doctor_id or patient.primary_doctor_id
    if not doctor_id:
        doc = db.query(models.User).filter(models.User.role == models.UserRole.doctor).first()
        if doc:
            doctor_id = doc.id
    if not doctor_id:
        raise HTTPException(status_code=400, detail="No doctor available to assign appointment")

    patient.primary_doctor_id = doctor_id
    if payload.appointment_type in ["video", "consultation"]:
        patient.doctor_consultancy_date = payload.scheduled_start
    elif payload.appointment_type in ["in_person", "final_meet"]:
        patient.final_doctor_meet_date = payload.scheduled_start

    link = db.query(models.PatientDoctor).filter(
        models.PatientDoctor.patient_id == patient.id,
        models.PatientDoctor.doctor_id == doctor_id
    ).first()
    if not link:
        db.add(models.PatientDoctor(patient_id=patient.id, doctor_id=doctor_id, relationship_status="active"))
    else:
        link.relationship_status = "active"

    item = models.Appointment(
        patient_id=patient.id,
        doctor_id=doctor_id,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        appointment_type=payload.appointment_type,
        status="confirmed",
        reason=payload.reason or "Patient requested consultation",
        meeting_url=payload.meeting_url or f"https://meet.jit.si/vithara-recovery-{patient.id[:8]}",
        created_by_user_id=current_user.id,
    )
    db.add(item)
    db.flush()

    db.add(
        models.DoctorNotification(
            doctor_id=doctor_id,
            patient_id=patient.id,
            appointment_id=item.id,
            notification_type=models.NotificationType.appointment,
            title="New Patient Consultation Booked",
            message=payload.reason or "Patient booked a consultation",
            priority="normal",
        )
    )
    db.commit()
    db.refresh(item)
    audit.log_action(db, current_user.id, "PATIENT_BOOKED_APPOINTMENT", "Appointment", item.id, request=request)
    return _appointment_out(item)


@router.post("/me/share-report", response_model=schemas.SharedRecoveryReportOut)
def share_my_recovery_report(
    payload: schemas.SharedRecoveryReportCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users can share reports")
    patient = _get_or_create_patient(db, current_user)
    latest = _latest_daily_context(db, patient.id)
    metrics = (
        db.query(models.HealingMetric)
        .filter(models.HealingMetric.patient_id == patient.id)
        .order_by(models.HealingMetric.measured_at.desc())
        .limit(7)
        .all()
    )
    doctor_id = payload.doctor_id or patient.primary_doctor_id
    summary = payload.summary or (
        f"Latest risk: {latest.risk_class.value if latest and hasattr(latest.risk_class, 'value') else latest.risk_class if latest else 'No upload yet'}; "
        f"healing rate: {latest.healing_rate:.0f}%" if latest and latest.healing_rate is not None else "Recovery report generated before a daily upload."
    )
    report = models.SharedRecoveryReport(
        patient_id=patient.id,
        doctor_id=doctor_id,
        title=payload.title,
        report_type=payload.report_type,
        summary=summary,
        payload={
            "patient_id": patient.id,
            "current_healing_rate": patient.current_healing_rate,
            "current_healing_trend": patient.current_healing_trend,
            "latest_daily_log_id": latest.id if latest else None,
            "metric_count": len(metrics),
        },
    )
    db.add(report)
    if doctor_id:
        db.add(
            models.DoctorNotification(
                doctor_id=doctor_id,
                patient_id=patient.id,
                notification_type=models.NotificationType.system,
                title="Recovery report shared",
                message=summary,
                priority="normal",
            )
        )
    db.commit()
    db.refresh(report)
    audit.log_action(db, current_user.id, "SHARE_RECOVERY_REPORT", "SharedRecoveryReport", report.id, request=request)
    return _report_out(report)


@router.get("/me/voice-assistant/messages", response_model=schemas.VoiceAssistantHistoryOut)
def list_voice_assistant_messages(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users can view voice assistant messages")
    patient = _get_or_create_patient(db, current_user)
    messages = (
        db.query(models.VoiceAssistantLog)
        .filter(models.VoiceAssistantLog.patient_id == patient.id)
        .order_by(models.VoiceAssistantLog.created_at.asc())
        .limit(50)
        .all()
    )
    audit.log_action(db, current_user.id, "VIEW_VOICE_ASSISTANT_HISTORY", "Patient", patient.id, request=request)
    return schemas.VoiceAssistantHistoryOut(messages=[_voice_out(item) for item in messages])


@router.post("/me/voice-assistant/messages", response_model=schemas.VoiceAssistantOut)
def create_voice_assistant_message(
    payload: schemas.VoiceAssistantRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users can use voice assistant")
    patient = _get_or_create_patient(db, current_user)
    intent, urgency, response = _voice_response(db, patient, payload.message)
    triage_case_id = None
    if urgency == "urgent":
        latest = _latest_daily_context(db, patient.id)
        triage_case = models.TriageCase(
            patient_id=patient.id,
            image_id=latest.image_id if latest else None,
            risk_class=models.RiskClass.urgent,
            final_risk_score=95.0,
            status=models.TriageStatus.escalated,
            symptom_data={"voice_transcript": payload.message, "emergency_keywords_detected": True},
            assigned_clinician_id=patient.primary_doctor_id,
        )
        db.add(triage_case)
        db.flush()
        triage_case_id = triage_case.id
        doctor_ids = {patient.primary_doctor_id} if patient.primary_doctor_id else set()
        doctor_ids.update(
            row.doctor_id
            for row in db.query(models.PatientDoctor).filter(models.PatientDoctor.patient_id == patient.id, models.PatientDoctor.relationship_status == "active").all()
        )
        for doctor_id in doctor_ids:
            if doctor_id:
                db.add(
                    models.DoctorNotification(
                        doctor_id=doctor_id,
                        patient_id=patient.id,
                        triage_case_id=triage_case.id,
                        notification_type=models.NotificationType.urgent_triage,
                        title="Emergency voice assistant alert",
                        message=payload.message,
                        priority="urgent",
                    )
                )
    log = models.VoiceAssistantLog(
        patient_id=patient.id,
        user_message=payload.message,
        assistant_response=response,
        intent=intent,
        urgency=urgency,
        triage_case_id=triage_case_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    audit.log_action(db, current_user.id, "VOICE_ASSISTANT_MESSAGE", "VoiceAssistantLog", log.id, detail=f"intent={intent} urgency={urgency}", request=request)
    return _voice_out(log)


@router.get("/me/voice-command/capabilities", response_model=schemas.VoiceCommandCapabilitiesOut)
def list_voice_command_capabilities(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users can view voice command capabilities")
    patient = _get_or_create_patient(db, current_user)
    audit.log_action(db, current_user.id, "VIEW_VOICE_COMMAND_CAPABILITIES", "Patient", patient.id, request=request)
    return schemas.VoiceCommandCapabilitiesOut(commands=voice_service.COMMAND_CAPABILITIES)


@router.post("/me/voice-command/text", response_model=schemas.VoiceCommandOut)
def execute_voice_command_text(
    payload: schemas.VoiceCommandTextRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return _handle_voice_command(
        transcript=payload.message,
        speak=payload.speak,
        request=request,
        db=db,
        current_user=current_user,
    )


@router.post("/me/voice-command/audio", response_model=schemas.VoiceCommandOut)
def execute_voice_command_audio(
    request: Request,
    file: UploadFile = File(...),
    speak: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    audio_bytes = file.file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio upload")
    suffix = ".webm"
    if file.filename and "." in file.filename:
        suffix = "." + file.filename.rsplit(".", 1)[-1].lower()
    try:
        transcript = voice_service.transcribe_audio(audio_bytes, suffix=suffix)
    except Exception as exc:
        logger.exception("Voice transcription failed")
        raise HTTPException(
            status_code=503,
            detail=(
                "Backend speech-to-text is not ready because the Whisper model is not available locally. "
                "Use browser voice recognition or configure/download the Whisper model."
            ),
        )
    return _handle_voice_command(
        transcript=transcript,
        speak=speak,
        request=request,
        db=db,
        current_user=current_user,
    )


@router.get("/{patient_id}", response_model=schemas.PatientOut)
def get_patient_profile(
    patient_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    role = _role_value(current_user)
    if role == models.UserRole.patient.value and patient.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only access your own profile")

    audit.log_action(db, current_user.id, "VIEW_PATIENT_PROFILE", "Patient", patient.id, request=request)
    return patient


@router.post("/me/daily-wound-photo", response_model=schemas.DailyWoundUploadOut)
def upload_daily_wound_photo(
    request: Request,
    file: UploadFile = File(...),
    pain_level: int | None = Form(None),
    fever: bool | None = Form(None),
    medication_adherence: bool | None = Form(None),
    emergency_keywords_detected: bool | None = Form(False),
    notes: str | None = Form(None),
    capture_date: date | None = Form(None),
    symptom_data_json: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users can upload daily wound photos")

    patient = (
        db.query(models.Patient)
        .filter(models.Patient.user_id == current_user.id)
        .first()
    )
    if patient is None:
        patient = models.Patient(user_id=current_user.id)
        db.add(patient)
        db.commit()
        db.refresh(patient)

    image_bytes = file.file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image upload")

    symptom_data = {
        "pain_level": pain_level,
        "fever": fever,
        "medication_adherence": medication_adherence,
        "emergency_keywords_detected": emergency_keywords_detected,
    }
    symptom_data = {key: value for key, value in symptom_data.items() if value is not None}
    if symptom_data_json:
        try:
            symptom_data.update(json.loads(symptom_data_json))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid symptom_data_json")

    try:
        result = recovery.create_daily_wound_evaluation(
            db=db,
            patient=patient,
            image_bytes=image_bytes,
            content_type=file.content_type or "image/jpeg",
            symptom_data=symptom_data,
            notes=notes,
            current_user_id=current_user.id,
            log_date=capture_date,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Daily wound upload failed for patient_id=%s", patient.id)
        raise HTTPException(
            status_code=500,
            detail=f"Daily wound analysis failed: {exc.__class__.__name__}: {exc}",
        )

    image = result["image"]
    classification = result["classification"]
    segmentation = result["segmentation"]
    triage_case = result["triage_case"]
    daily_log = result["daily_log"]
    audit.log_action(
        db,
        current_user.id,
        "UPLOAD_DAILY_WOUND_PHOTO",
        "DailyWoundLog",
        daily_log.id,
        detail=f"risk={_enum_value(classification.risk_class)} trend={_enum_value(daily_log.healing_trend)}",
        request=request,
    )

    return schemas.DailyWoundUploadOut(
        daily_log_id=daily_log.id,
        image_id=image.id,
        image_url=recovery.storage.get_presigned_url(image.s3_key),
        risk_class=_enum_value(classification.risk_class),
        confidence=classification.confidence,
        needs_human_review=bool(classification.needs_human_review),
        wound_area_cm2=segmentation.wound_area_cm2,
        percent_change_from_previous=segmentation.percent_change_from_previous,
        healing_rate=daily_log.healing_rate,
        healing_trend=_enum_value(daily_log.healing_trend),
        triage_case_id=triage_case.id,
        triage_status=_enum_value(triage_case.status),
        segmentation_model_used=segmentation.model_used,
        segmentation_model_confidence=segmentation.model_confidence,
        mask_overlay_url=recovery.storage.get_presigned_url(image.mask_overlay_key) if image.mask_overlay_key else None,
        comparison_source=result["comparison_source"],
        created_at=daily_log.created_at,
    )


@router.get("/me/daily-wound-logs", response_model=list[schemas.DailyWoundLogOut])
def list_my_daily_wound_logs(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users can view their daily wound logs")

    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    logs = (
        db.query(models.DailyWoundLog)
        .filter(models.DailyWoundLog.patient_id == patient.id)
        .order_by(models.DailyWoundLog.created_at.desc())
        .all()
    )
    audit.log_action(db, current_user.id, "VIEW_OWN_DAILY_WOUND_LOGS", "Patient", patient.id, request=request)
    return [schemas.DailyWoundLogOut(**recovery.daily_log_to_schema(log)) for log in logs]


@router.get("/me/recovery-overview", response_model=schemas.PatientRecoveryOverviewOut)
def get_my_recovery_overview(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if _role_value(current_user) != models.UserRole.patient.value:
        raise HTTPException(status_code=403, detail="Only patient users can view their recovery overview")

    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient profile not found")

    latest_log = (
        db.query(models.DailyWoundLog)
        .filter(models.DailyWoundLog.patient_id == patient.id)
        .order_by(models.DailyWoundLog.created_at.desc())
        .first()
    )
    metrics = (
        db.query(models.HealingMetric)
        .filter(models.HealingMetric.patient_id == patient.id)
        .order_by(models.HealingMetric.measured_at.desc())
        .limit(20)
        .all()
    )
    appointments = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.patient_id == patient.id,
            models.Appointment.scheduled_start >= datetime.utcnow(),
            models.Appointment.status.in_([models.AppointmentStatus.requested, models.AppointmentStatus.confirmed]),
        )
        .order_by(models.Appointment.scheduled_start.asc())
        .limit(5)
        .all()
    )
    audit.log_action(db, current_user.id, "VIEW_OWN_RECOVERY_OVERVIEW", "Patient", patient.id, request=request)
    return schemas.PatientRecoveryOverviewOut(
        patient=patient,
        latest_daily_log=schemas.DailyWoundLogOut(**recovery.daily_log_to_schema(latest_log)) if latest_log else None,
        healing_metrics=[_metric_out(item) for item in metrics],
        upcoming_appointments=[_appointment_out(item) for item in appointments],
        doctor_consultancy_date=patient.doctor_consultancy_date,
        final_doctor_meet_date=patient.final_doctor_meet_date,
    )
