"""
Triage & Notification Engine.

Combines CV classification confidence, symptom self-report, and voice-derived
emergency keywords into one final risk score + routing decision, per spec
sections 3 and 7.4 (voice assistant can trigger emergency escalation
regardless of the photo schedule).
"""
from app.config import settings
from app.models import RiskClass, TriageStatus

CLASS_BASE_SCORE = {
    RiskClass.normal.value: 0.15,
    RiskClass.mild_concern.value: 0.5,
    RiskClass.urgent.value: 0.9,
}


def compute_triage(
    risk_class: str | None,
    confidence: float | None,
    needs_human_review: bool,
    symptom_data: dict | None,
    infection_risk: float = 0.0,
    is_abnormal_delay: bool = False,
) -> dict:
    symptom_data = symptom_data or {}

    base_score = CLASS_BASE_SCORE.get(risk_class, 0.3) if risk_class else 0.3

    # Symptom fusion (pain, fever, medication adherence)
    if symptom_data.get("pain_level") is not None:
        base_score += min(symptom_data["pain_level"], 10) / 10 * 0.15
    if symptom_data.get("fever"):
        base_score += 0.15
    if symptom_data.get("medication_adherence") is False:
        base_score += 0.05

    # Infection risk contribution
    if infection_risk > 0.0:
        base_score += infection_risk * 0.25

    # Abnormal healing delay contribution
    if is_abnormal_delay:
        base_score += 0.20

    final_score = min(round(base_score, 3), 1.0)

    # Hard override: voice "emergency" keyword always escalates immediately
    if symptom_data.get("emergency_keywords_detected") or infection_risk >= 0.70:
        return {
            "risk_class": RiskClass.urgent.value,
            "final_risk_score": max(final_score, 0.95),
            "status": TriageStatus.escalated.value,
        }

    # Low-confidence AI predictions never auto-resolve — always human-reviewed
    if needs_human_review or confidence is None or confidence < settings.CONFIDENCE_THRESHOLD:
        status = TriageStatus.pending_review.value
    elif risk_class == RiskClass.normal.value and final_score < 0.30 and not is_abnormal_delay:
        status = TriageStatus.auto_cleared.value
    elif risk_class == RiskClass.urgent.value or final_score >= 0.70:
        status = TriageStatus.escalated.value
    else:
        status = TriageStatus.pending_review.value

    resolved_class = risk_class or RiskClass.normal.value
    return {
        "risk_class": resolved_class,
        "final_risk_score": final_score,
        "status": status,
    }

