from datetime import datetime, time, timedelta

from sqlalchemy.orm import Session

from app import models


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


def assigned_doctor_ids(db: Session, patient_id: str) -> list[str]:
    rows = (
        db.query(models.PatientDoctor)
        .filter(
            models.PatientDoctor.patient_id == patient_id,
            models.PatientDoctor.relationship_status == "active",
        )
        .all()
    )
    return [row.doctor_id for row in rows]


def ensure_doctor_profile(db: Session, user: models.User) -> models.DoctorProfile:
    profile = (
        db.query(models.DoctorProfile)
        .filter(models.DoctorProfile.user_id == user.id)
        .first()
    )
    if profile is None:
        profile = models.DoctorProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def create_doctor_notification(
    db: Session,
    doctor_id: str,
    notification_type: str,
    title: str,
    message: str | None = None,
    patient_id: str | None = None,
    triage_case_id: str | None = None,
    appointment_id: str | None = None,
    priority: str = "normal",
) -> models.DoctorNotification:
    notification = models.DoctorNotification(
        doctor_id=doctor_id,
        patient_id=patient_id,
        triage_case_id=triage_case_id,
        appointment_id=appointment_id,
        notification_type=notification_type,
        title=title,
        message=message,
        priority=priority,
    )
    db.add(notification)
    return notification


def notify_assigned_doctors_for_triage(db: Session, case: models.TriageCase) -> None:
    priority = "urgent" if _enum_value(case.status) == models.TriageStatus.escalated.value else "normal"
    title = "Urgent recovery alert" if priority == "urgent" else "Patient review required"
    message = f"Risk class: {_enum_value(case.risk_class)}; score: {case.final_risk_score}"
    for doctor_id in assigned_doctor_ids(db, case.patient_id):
        create_doctor_notification(
            db,
            doctor_id=doctor_id,
            notification_type=models.NotificationType.urgent_triage.value,
            title=title,
            message=message,
            patient_id=case.patient_id,
            triage_case_id=case.id,
            priority=priority,
        )


def is_patient_assigned_to_doctor(db: Session, patient_id: str, doctor_id: str) -> bool:
    return (
        db.query(models.PatientDoctor)
        .filter(
            models.PatientDoctor.patient_id == patient_id,
            models.PatientDoctor.doctor_id == doctor_id,
            models.PatientDoctor.relationship_status == "active",
        )
        .first()
        is not None
    )


def auto_schedule_emergency_or_delayed_appointment(
    db: Session,
    patient_id: str,
    doctor_id: str,
    reason: str,
    is_emergency: bool = False,
) -> models.Appointment | None:
    # Check if there is already an upcoming appointment in the next 48 hours
    now = datetime.utcnow()
    existing = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.patient_id == patient_id,
            models.Appointment.doctor_id == doctor_id,
            models.Appointment.scheduled_start >= now,
            models.Appointment.scheduled_start <= now + timedelta(days=2),
            models.Appointment.status.in_([models.AppointmentStatus.requested, models.AppointmentStatus.confirmed]),
        )
        .first()
    )
    if existing:
        return existing

    # Schedule next day morning (e.g. 10:00 AM) or next 4 hours if emergency
    if is_emergency:
        start_time = now + timedelta(hours=3)
    else:
        start_time = datetime.combine((now + timedelta(days=1)).date(), time(10, 0))
    end_time = start_time + timedelta(minutes=30)

    appointment = models.Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        scheduled_start=start_time,
        scheduled_end=end_time,
        appointment_type=models.AppointmentType.video,
        status=models.AppointmentStatus.requested,
        reason=reason,
        created_by_user_id=doctor_id,
    )
    db.add(appointment)
    db.flush()

    # Update patient's next appointment date
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if patient:
        patient.next_appointment_date = start_time

    return appointment


def day_bounds(value: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(value.date(), time.min)
    end = datetime.combine(value.date(), time.max)
    return start, end

