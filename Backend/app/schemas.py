from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict, EmailStr


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "patient"


class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: str
    class Config:
        from_attributes = True


class PatientCreate(BaseModel):
    surgery_type: Optional[str] = None
    surgery_date: Optional[datetime] = None
    date_of_birth: Optional[str] = None
    phone_number: Optional[str] = None
    reference_marker_cm: float = 2.0
    next_appointment_date: Optional[datetime] = None
    doctor_consultancy_date: Optional[datetime] = None
    final_doctor_meet_date: Optional[datetime] = None
    recovery_goal: Optional[str] = None


class PatientOut(BaseModel):
    id: str
    user_id: str
    surgery_type: Optional[str] = None
    surgery_date: Optional[datetime] = None
    date_of_birth: Optional[str] = None
    phone_number: Optional[str] = None
    reference_marker_cm: float
    primary_doctor_id: Optional[str] = None
    next_appointment_date: Optional[datetime] = None
    doctor_consultancy_date: Optional[datetime] = None
    final_doctor_meet_date: Optional[datetime] = None
    recovery_goal: Optional[str] = None
    current_healing_rate: Optional[float] = None
    current_healing_trend: Optional[str] = None
    last_daily_upload_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DoctorProfileCreate(BaseModel):
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    hospital_name: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None


class DoctorProfileOut(BaseModel):
    id: str
    user_id: str
    specialization: Optional[str] = None
    license_number: Optional[str] = None
    hospital_name: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AssignPatientRequest(BaseModel):
    patient_id: str
    notes: Optional[str] = None


class AppointmentCreate(BaseModel):
    patient_id: str
    doctor_id: Optional[str] = None
    scheduled_start: datetime
    scheduled_end: datetime
    appointment_type: str = "video"
    reason: Optional[str] = None
    meeting_url: Optional[str] = None


class AppointmentUpdate(BaseModel):
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    appointment_type: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    meeting_url: Optional[str] = None


class AppointmentOut(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    scheduled_start: datetime
    scheduled_end: datetime
    appointment_type: str
    status: str
    reason: Optional[str] = None
    meeting_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DoctorNotificationOut(BaseModel):
    id: str
    doctor_id: str
    patient_id: Optional[str] = None
    triage_case_id: Optional[str] = None
    appointment_id: Optional[str] = None
    notification_type: str
    title: str
    message: Optional[str] = None
    priority: str
    is_read: bool
    created_at: datetime


class ConsultationSessionCreate(BaseModel):
    patient_id: str
    appointment_id: Optional[str] = None
    connection_url: Optional[str] = None


class ConsultationSessionUpdate(BaseModel):
    session_status: Optional[str] = None
    connection_url: Optional[str] = None
    summary: Optional[str] = None


class ConsultationSessionOut(BaseModel):
    id: str
    appointment_id: Optional[str] = None
    patient_id: str
    doctor_id: str
    session_status: str
    connection_url: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    summary: Optional[str] = None
    created_at: datetime


class ClinicalNoteCreate(BaseModel):
    patient_id: str
    image_id: Optional[str] = None
    triage_case_id: Optional[str] = None
    note: str


class ClinicalNoteOut(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    image_id: Optional[str] = None
    triage_case_id: Optional[str] = None
    note: str
    created_at: datetime


class DoctorPatientSummary(BaseModel):
    patient: PatientOut
    latest_risk_class: Optional[str] = None
    latest_confidence: Optional[float] = None
    latest_wound_area_cm2: Optional[float] = None
    healing_rate: Optional[float] = None
    healing_trend: Optional[str] = None
    latest_image_id: Optional[str] = None
    latest_image_url: Optional[str] = None
    open_triage_cases: int = 0
    next_appointment: Optional[AppointmentOut] = None


class DoctorDashboardOut(BaseModel):
    total_patients: int
    active_recovery_cases: int
    todays_appointments: int
    urgent_alerts: int
    pending_reviews: int
    upcoming_appointments: list[AppointmentOut]
    priority_cases: list[TriageOut]
    notifications: list[DoctorNotificationOut]


class WoundImageDetailOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    image_id: str
    patient_id: str
    uploaded_at: datetime
    image_url: str
    risk_class: Optional[str] = None
    confidence: Optional[float] = None
    needs_human_review: Optional[bool] = None
    raw_scores: Optional[dict] = None
    wound_area_px: Optional[float] = None
    wound_area_cm2: Optional[float] = None
    percent_change_from_previous: Optional[float] = None
    segmentation_model_used: Optional[str] = None
    segmentation_model_confidence: Optional[float] = None
    segmentation_prompt_box: Optional[list[int]] = None
    mask_overlay_url: Optional[str] = None


class DailyWoundUploadOut(BaseModel):
    daily_log_id: str
    image_id: str
    image_url: str
    risk_class: str
    confidence: float
    needs_human_review: bool
    wound_area_cm2: Optional[float] = None
    percent_change_from_previous: Optional[float] = None
    healing_rate: Optional[float] = None
    healing_trend: Optional[str] = None
    triage_case_id: Optional[str] = None
    triage_status: Optional[str] = None
    segmentation_model_used: Optional[str] = None
    segmentation_model_confidence: Optional[float] = None
    mask_overlay_url: Optional[str] = None
    comparison_source: Optional[str] = None
    created_at: datetime


class DailyWoundLogOut(BaseModel):
    id: str
    patient_id: str
    image_id: str
    log_date: date
    pain_level: Optional[int] = None
    fever: Optional[bool] = None
    medication_adherence: Optional[bool] = None
    notes: Optional[str] = None
    risk_class: Optional[str] = None
    confidence: Optional[float] = None
    wound_area_cm2: Optional[float] = None
    percent_change_from_previous: Optional[float] = None
    healing_rate: Optional[float] = None
    healing_trend: Optional[str] = None
    triage_case_id: Optional[str] = None
    doctor_review_status: str
    reviewed_by_doctor_id: Optional[str] = None
    doctor_review_note: Optional[str] = None
    doctor_reviewed_at: Optional[datetime] = None
    is_primary_daily_image: bool = True
    image_url: Optional[str] = None
    mask_overlay_url: Optional[str] = None
    created_at: datetime


class HealingMetricOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    patient_id: str
    image_id: Optional[str] = None
    daily_log_id: Optional[str] = None
    measured_at: datetime
    wound_area_cm2: Optional[float] = None
    previous_wound_area_cm2: Optional[float] = None
    comparison_source: Optional[str] = None
    percent_change_from_previous: Optional[float] = None
    healing_rate: Optional[float] = None
    healing_trend: Optional[str] = None
    model_summary: Optional[dict] = None


class PatientRecoveryOverviewOut(BaseModel):
    patient: PatientOut
    latest_daily_log: Optional[DailyWoundLogOut] = None
    healing_metrics: list[HealingMetricOut]
    upcoming_appointments: list[AppointmentOut]
    doctor_consultancy_date: Optional[datetime] = None
    final_doctor_meet_date: Optional[datetime] = None


class PatientReminderCreate(BaseModel):
    title: str
    reminder_type: str = "care"
    schedule_time: str = "08:00"
    schedule_label: Optional[str] = None
    notes: Optional[str] = None
    is_enabled: bool = True


class PatientReminderUpdate(BaseModel):
    title: Optional[str] = None
    reminder_type: Optional[str] = None
    schedule_time: Optional[str] = None
    schedule_label: Optional[str] = None
    notes: Optional[str] = None
    is_enabled: Optional[bool] = None


class PatientReminderOut(BaseModel):
    id: str
    patient_id: str
    title: str
    reminder_type: str
    schedule_time: str
    schedule_label: Optional[str] = None
    notes: Optional[str] = None
    is_enabled: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class CareTeamMemberOut(BaseModel):
    doctor_id: str
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    specialization: Optional[str] = None
    hospital_name: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    relationship_status: Optional[str] = None
    assigned_at: Optional[datetime] = None


class SharedRecoveryReportCreate(BaseModel):
    doctor_id: Optional[str] = None
    title: str = "Recovery Progress Report"
    report_type: str = "recovery_progress"
    summary: Optional[str] = None


class SharedRecoveryReportOut(BaseModel):
    id: str
    patient_id: str
    doctor_id: Optional[str] = None
    title: str
    report_type: str
    summary: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    created_at: datetime


class CareTeamOverviewOut(BaseModel):
    patient: PatientOut
    primary_doctor: Optional[CareTeamMemberOut] = None
    care_team: list[CareTeamMemberOut]
    upcoming_appointments: list[AppointmentOut]
    recent_reports: list[SharedRecoveryReportOut]
    emergency_guidance: str
    clinic_hours: str = "8 AM - 8 PM"


class VoiceAssistantRequest(BaseModel):
    message: str


class VoiceAssistantOut(BaseModel):
    id: str
    patient_id: str
    user_message: str
    assistant_response: str
    intent: Optional[str] = None
    urgency: str
    triage_case_id: Optional[str] = None
    created_at: datetime


class VoiceAssistantHistoryOut(BaseModel):
    messages: list[VoiceAssistantOut]


class VoiceCommandTextRequest(BaseModel):
    message: str
    speak: bool = True
    auto_execute: bool = True


class VoiceCommandOut(BaseModel):
    transcript: str
    assistant_response: str
    intent: str
    urgency: str = "normal"
    command: dict[str, Any]
    result: Optional[dict[str, Any]] = None
    audio_url: Optional[str] = None
    message_log: VoiceAssistantOut


class VoiceCommandCapabilitiesOut(BaseModel):
    commands: list[dict[str, Any]]


class DailyWoundReviewRequest(BaseModel):
    doctor_review_status: str = "reviewed"
    doctor_review_note: Optional[str] = None


class DailyWoundReviewOut(BaseModel):
    id: str
    doctor_review_status: str
    reviewed_by_doctor_id: str
    doctor_review_note: Optional[str] = None
    doctor_reviewed_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Classify ----------
class ClassificationOut(BaseModel):
    image_id: str
    risk_class: str
    confidence: float
    needs_human_review: bool
    raw_scores: dict
    image_url: Optional[str] = None
    class Config:
        from_attributes = True


# ---------- Segment ----------
class SegmentationOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    image_id: str
    wound_area_px: float
    wound_area_cm2: Optional[float]
    percent_change_from_previous: Optional[float]
    model_used: Optional[str] = None
    model_confidence: Optional[float] = None
    prompt_box: Optional[list[int]] = None


# ---------- Triage ----------
class SymptomData(BaseModel):
    pain_level: Optional[int] = None       # 0-10
    fever: Optional[bool] = None
    medication_adherence: Optional[bool] = None
    voice_transcript: Optional[str] = None
    emergency_keywords_detected: Optional[bool] = False


class TriageRequest(BaseModel):
    patient_id: str
    image_id: Optional[str] = None
    symptom_data: Optional[SymptomData] = None


class TriageOut(BaseModel):
    id: str
    patient_id: str
    risk_class: str
    final_risk_score: float
    status: str
    created_at: datetime
    class Config:
        from_attributes = True


# ---------- Patient history ----------
class HistoryItem(BaseModel):
    image_id: str
    uploaded_at: datetime
    risk_class: Optional[str] = None
    confidence: Optional[float] = None
    wound_area_cm2: Optional[float] = None
    percent_change_from_previous: Optional[float] = None
    healing_rate: Optional[float] = None
    healing_trend: Optional[str] = None
    image_url: Optional[str] = None
