import uuid
import enum
from datetime import date, datetime

from sqlalchemy import (
    Column, String, Integer, Float, Date, DateTime, ForeignKey, Enum, Text, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.encryption import EncryptedString


def gen_uuid():
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    patient = "patient"
    nurse = "nurse"
    doctor = "doctor"
    admin = "admin"


class RiskClass(str, enum.Enum):
    normal = "Normal"
    mild_concern = "Mild Concern"
    urgent = "Urgent"


class TriageStatus(str, enum.Enum):
    auto_cleared = "auto_cleared"
    pending_review = "pending_review"
    reviewed = "reviewed"
    escalated = "escalated"


class AppointmentStatus(str, enum.Enum):
    requested = "requested"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"
    rescheduled = "rescheduled"


class AppointmentType(str, enum.Enum):
    video = "video"
    in_person = "in_person"
    phone = "phone"


class NotificationType(str, enum.Enum):
    urgent_triage = "urgent_triage"
    new_wound_image = "new_wound_image"
    appointment = "appointment"
    system = "system"


class SessionStatus(str, enum.Enum):
    scheduled = "scheduled"
    live = "live"
    completed = "completed"
    cancelled = "cancelled"


class HealingTrend(str, enum.Enum):
    improving = "improving"
    stable = "stable"
    worsening = "worsening"
    needs_review = "needs_review"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(EncryptedString, nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.patient)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient_profile = relationship(
        "Patient",
        back_populates="user",
        uselist=False,
        foreign_keys="Patient.user_id",
    )
    doctor_profile = relationship("DoctorProfile", back_populates="user", uselist=False)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    surgery_type = Column(String, nullable=True)
    surgery_date = Column(DateTime, nullable=True)
    date_of_birth = Column(EncryptedString, nullable=True)
    phone_number = Column(EncryptedString, nullable=True)
    reference_marker_cm = Column(Float, default=2.0)  # known-size calibration marker
    primary_doctor_id = Column(String, ForeignKey("users.id"), nullable=True)
    next_appointment_date = Column(DateTime, nullable=True)
    doctor_consultancy_date = Column(DateTime, nullable=True)
    final_doctor_meet_date = Column(DateTime, nullable=True)
    recovery_goal = Column(Text, nullable=True)
    current_healing_rate = Column(Float, nullable=True)
    current_healing_trend = Column(String, nullable=True)
    last_daily_upload_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="patient_profile", foreign_keys=[user_id])
    primary_doctor = relationship("User", foreign_keys=[primary_doctor_id])
    images = relationship("WoundImage", back_populates="patient")
    triage_cases = relationship("TriageCase", back_populates="patient")
    doctor_links = relationship("PatientDoctor", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")
    daily_wound_logs = relationship("DailyWoundLog", back_populates="patient")
    healing_metrics = relationship("HealingMetric", back_populates="patient")
    reminders = relationship("PatientReminder", back_populates="patient")
    reports = relationship("SharedRecoveryReport", back_populates="patient")
    voice_logs = relationship("VoiceAssistantLog", back_populates="patient")


class WoundImage(Base):
    __tablename__ = "wound_images"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    s3_key = Column(String, nullable=False)
    s3_bucket = Column(String, nullable=False)
    capture_date = Column(Date, default=date.today)
    content_type = Column(String, nullable=True)
    image_quality_score = Column(Float, nullable=True)
    ai_evaluated = Column(Integer, default=0)
    mask_overlay_key = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="images")
    classification = relationship("Classification", back_populates="image", uselist=False)
    segmentation = relationship("Segmentation", back_populates="image", uselist=False)
    daily_log = relationship("DailyWoundLog", back_populates="image", uselist=False)


class Classification(Base):
    __tablename__ = "classifications"

    id = Column(String, primary_key=True, default=gen_uuid)
    image_id = Column(String, ForeignKey("wound_images.id"), nullable=False)
    risk_class = Column(Enum(RiskClass), nullable=False)
    confidence = Column(Float, nullable=False)
    needs_human_review = Column(Integer, default=0)  # 1 if below confidence threshold
    raw_scores = Column(JSON, nullable=True)  # per-class probability breakdown
    created_at = Column(DateTime, default=datetime.utcnow)

    image = relationship("WoundImage", back_populates="classification")


class Segmentation(Base):
    __tablename__ = "segmentations"

    id = Column(String, primary_key=True, default=gen_uuid)
    image_id = Column(String, ForeignKey("wound_images.id"), nullable=False)
    wound_area_px = Column(Float, nullable=False)
    wound_area_cm2 = Column(Float, nullable=True)
    percent_change_from_previous = Column(Float, nullable=True)
    model_used = Column(String, nullable=True)
    model_confidence = Column(Float, nullable=True)
    prompt_box = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    image = relationship("WoundImage", back_populates="segmentation")


class TriageCase(Base):
    __tablename__ = "triage_cases"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    image_id = Column(String, ForeignKey("wound_images.id"), nullable=True)
    risk_class = Column(Enum(RiskClass), nullable=False)
    final_risk_score = Column(Float, nullable=False)
    status = Column(Enum(TriageStatus), default=TriageStatus.pending_review)
    symptom_data = Column(JSON, nullable=True)  # pain, fever, adherence, voice transcript
    assigned_clinician_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="triage_cases")
    assigned_clinician = relationship("User")


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    specialization = Column(String, nullable=True)
    license_number = Column(String, nullable=True)
    hospital_name = Column(String, nullable=True)
    phone_number = Column(EncryptedString, nullable=True)
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="doctor_profile")
    patient_links = relationship(
        "PatientDoctor",
        primaryjoin="DoctorProfile.user_id==PatientDoctor.doctor_id",
        foreign_keys="PatientDoctor.doctor_id",
        back_populates="doctor",
    )
    appointments = relationship(
        "Appointment",
        primaryjoin="DoctorProfile.user_id==Appointment.doctor_id",
        foreign_keys="Appointment.doctor_id",
        back_populates="doctor",
    )


class PatientDoctor(Base):
    __tablename__ = "patient_doctors"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String, ForeignKey("users.id"), nullable=False)
    relationship_status = Column(String, default="active")
    notes = Column(Text, nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="doctor_links")
    doctor = relationship("DoctorProfile", primaryjoin="PatientDoctor.doctor_id==DoctorProfile.user_id", foreign_keys=[doctor_id], back_populates="patient_links")


class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"

    id = Column(String, primary_key=True, default=gen_uuid)
    doctor_id = Column(String, ForeignKey("users.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # Monday=0
    start_time = Column(String, nullable=False)    # HH:MM
    end_time = Column(String, nullable=False)      # HH:MM
    location = Column(String, nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class PatientReminder(Base):
    __tablename__ = "patient_reminders"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    title = Column(String, nullable=False)
    reminder_type = Column(String, default="care")
    schedule_time = Column(String, nullable=False)  # HH:MM local display time
    schedule_label = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="reminders")


class SharedRecoveryReport(Base):
    __tablename__ = "shared_recovery_reports"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String, ForeignKey("users.id"), nullable=True)
    title = Column(String, nullable=False)
    report_type = Column(String, default="recovery_progress")
    summary = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="reports")


class VoiceAssistantLog(Base):
    __tablename__ = "voice_assistant_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    user_message = Column(Text, nullable=False)
    assistant_response = Column(Text, nullable=False)
    intent = Column(String, nullable=True)
    urgency = Column(String, default="normal")
    triage_case_id = Column(String, ForeignKey("triage_cases.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="voice_logs")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String, ForeignKey("users.id"), nullable=False)
    scheduled_start = Column(DateTime, nullable=False)
    scheduled_end = Column(DateTime, nullable=False)
    appointment_type = Column(Enum(AppointmentType), default=AppointmentType.video)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.requested)
    reason = Column(Text, nullable=True)
    meeting_url = Column(String, nullable=True)
    created_by_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("DoctorProfile", primaryjoin="Appointment.doctor_id==DoctorProfile.user_id", foreign_keys=[doctor_id], back_populates="appointments")


class DoctorNotification(Base):
    __tablename__ = "doctor_notifications"

    id = Column(String, primary_key=True, default=gen_uuid)
    doctor_id = Column(String, ForeignKey("users.id"), nullable=False)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=True)
    triage_case_id = Column(String, ForeignKey("triage_cases.id"), nullable=True)
    appointment_id = Column(String, ForeignKey("appointments.id"), nullable=True)
    notification_type = Column(Enum(NotificationType), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    priority = Column(String, default="normal")
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConsultationSession(Base):
    __tablename__ = "consultation_sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    appointment_id = Column(String, ForeignKey("appointments.id"), nullable=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String, ForeignKey("users.id"), nullable=False)
    session_status = Column(Enum(SessionStatus), default=SessionStatus.scheduled)
    connection_url = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String, ForeignKey("users.id"), nullable=False)
    image_id = Column(String, ForeignKey("wound_images.id"), nullable=True)
    triage_case_id = Column(String, ForeignKey("triage_cases.id"), nullable=True)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyWoundLog(Base):
    __tablename__ = "daily_wound_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    image_id = Column(String, ForeignKey("wound_images.id"), nullable=False)
    log_date = Column(Date, default=date.today, nullable=False)
    pain_level = Column(Integer, nullable=True)
    fever = Column(Integer, nullable=True)
    medication_adherence = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    risk_class = Column(Enum(RiskClass), nullable=True)
    confidence = Column(Float, nullable=True)
    wound_area_cm2 = Column(Float, nullable=True)
    percent_change_from_previous = Column(Float, nullable=True)
    healing_rate = Column(Float, nullable=True)
    healing_trend = Column(Enum(HealingTrend), nullable=True)
    triage_case_id = Column(String, ForeignKey("triage_cases.id"), nullable=True)
    doctor_review_status = Column(String, default="pending")
    reviewed_by_doctor_id = Column(String, ForeignKey("users.id"), nullable=True)
    doctor_review_note = Column(Text, nullable=True)
    doctor_reviewed_at = Column(DateTime, nullable=True)
    is_primary_daily_image = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="daily_wound_logs")
    image = relationship("WoundImage", back_populates="daily_log")


class HealingMetric(Base):
    __tablename__ = "healing_metrics"

    id = Column(String, primary_key=True, default=gen_uuid)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    image_id = Column(String, ForeignKey("wound_images.id"), nullable=True)
    daily_log_id = Column(String, ForeignKey("daily_wound_logs.id"), nullable=True)
    measured_at = Column(DateTime, default=datetime.utcnow)
    wound_area_cm2 = Column(Float, nullable=True)
    previous_wound_area_cm2 = Column(Float, nullable=True)
    comparison_source = Column(String, nullable=True)
    percent_change_from_previous = Column(Float, nullable=True)
    healing_rate = Column(Float, nullable=True)
    healing_trend = Column(Enum(HealingTrend), nullable=True)
    model_summary = Column(JSON, nullable=True)

    patient = relationship("Patient", back_populates="healing_metrics")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)          # e.g. "CLASSIFY_IMAGE", "VIEW_PATIENT_RECORD"
    resource_type = Column(String, nullable=True)     # e.g. "Patient", "WoundImage"
    resource_id = Column(String, nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
