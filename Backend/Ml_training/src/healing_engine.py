"""
Temporal Healing Rate, Abnormal Delay & Clinical Decision Engine.
Calculates:
1. Real-world area estimation from segmentation mask (cm²).
2. Expected vs Actual Healing Velocity based on clinical decay models.
3. Abnormal Healing Delay Detection & Automatic Doctor Appointment Trigger.
4. Patient 3-Tier Mapping (Normal / Medium / Urgent).
5. Comprehensive Daily Doctor Report Generation.
"""

from typing import Dict, Any, Optional
import datetime


class HealingAndTriageEngine:
    """
    Evaluates daily wound recovery trajectory and triggers clinical escalations.
    """
    def __init__(self, pixels_per_cm: float = 40.0, expected_daily_reduction_rate: float = 0.02):
        self.pixels_per_cm = pixels_per_cm
        self.k_rate = expected_daily_reduction_rate  # 2% expected daily reduction

    def calculate_area_cm2(self, mask_numpy) -> float:
        """Converts binary mask pixel count to square centimeters."""
        wound_pixels = float((mask_numpy > 0.5).sum())
        area_cm2 = wound_pixels / (self.pixels_per_cm ** 2)
        return round(area_cm2, 2)

    def analyze_recovery_step(
        self,
        current_area: float,
        previous_area: Optional[float] = None,
        days_elapsed: int = 1,
        severity_class: int = 0,       # 0: Normal, 1: Medium, 2: Urgent
        severity_confidence: float = 0.9,
        infection_risk: float = 0.1,    # 0.0 to 1.0
        reported_symptoms: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive clinical analysis combining vision output, temporal decay, and symptoms.
        """
        symptoms = reported_symptoms or {}
        pain_score = symptoms.get("pain_score", 0)
        has_fever = symptoms.get("has_fever", False)
        pus_or_odor = symptoms.get("pus_or_odor", False)
        
        # 1. Area Change Calculation
        if previous_area is not None and previous_area > 0:
            area_change_pct = ((current_area - previous_area) / previous_area) * 100.0
            # Expected area under normal recovery
            expected_area = round(previous_area * max(0.05, 1.0 - (self.k_rate * max(1, days_elapsed))), 2)
        else:
            area_change_pct = 0.0
            expected_area = current_area
            
        # 2. Abnormal Delay & Infection Check
        is_abnormal_delay = False
        delay_reason = "Healing progressing on schedule."
        
        if previous_area is not None and previous_area > 0:
            if current_area > (expected_area * 1.30):
                is_abnormal_delay = True
                delay_reason = f"Wound is taking longer than predicted. Measured {current_area} cm² vs expected {expected_area} cm²."
            elif area_change_pct > 12.0:
                is_abnormal_delay = True
                delay_reason = f"Wound area expanded by {area_change_pct:.1f}% over the last {days_elapsed} day(s)."

        # 3. Emergency / Severity Classification
        is_emergency = False
        if severity_class == 2:  # Urgent
            is_emergency = True
        elif infection_risk >= 0.65:
            is_emergency = True
        elif pus_or_odor or (has_fever and pain_score >= 7):
            is_emergency = True
            
        # 4. Patient 3-State Display Resolution (Strictly: Normal / Medium / Urgent)
        if is_emergency:
            patient_status = "Urgent"
            patient_advice = "Urgent medical attention required. Your doctor has been notified and an appointment is being coordinated."
        elif is_abnormal_delay or severity_class == 1 or infection_risk >= 0.35 or pain_score >= 5:
            patient_status = "Medium"
            patient_advice = "Healing requires close observation. Doctor review has been scheduled."
        else:
            patient_status = "Normal"
            patient_advice = "Wound is healing well within normal recovery parameters. Continue standard dressing care."

        # 5. Doctor Appointment Action
        requires_appointment = False
        appointment_urgency = "none"
        appointment_reason = ""

        if is_emergency:
            requires_appointment = True
            appointment_urgency = "emergency_priority"
            appointment_reason = f"EMERGENCY: Urgent condition detected (Infection: {infection_risk*100:.1f}%, Area Change: {area_change_pct:+.1f}%)."
        elif is_abnormal_delay:
            requires_appointment = True
            appointment_urgency = "abnormal_delay_checkup"
            appointment_reason = f"ABNORMAL DELAY: {delay_reason}"

        # 6. Detailed Doctor Report
        doctor_report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "clinical_severity": ["Normal", "Medium / Mild Concern", "Urgent / Critical"][severity_class],
            "severity_confidence": f"{severity_confidence * 100:.1f}%",
            "infection_risk_score": f"{infection_risk * 100:.1f}%",
            "measured_wound_area_cm2": current_area,
            "previous_wound_area_cm2": previous_area,
            "expected_wound_area_cm2": expected_area,
            "area_change_percentage": f"{area_change_pct:+.1f}%",
            "abnormal_delay_detected": is_abnormal_delay,
            "delay_notes": delay_reason,
            "symptom_summary": {
                "pain_score": f"{pain_score}/10",
                "has_fever": has_fever,
                "pus_or_discharge": pus_or_odor
            },
            "appointment_action": {
                "booking_triggered": requires_appointment,
                "urgency_level": appointment_urgency,
                "clinical_reason": appointment_reason
            },
            "suggested_clinical_action": (
                "Immediate in-person evaluation & wound debridement/antibiotics." if is_emergency
                else "Schedule clinical review to assess secondary infection or delayed healing." if is_abnormal_delay
                else "Routine observation, maintain current wound dressing schedule."
            )
        }

        return {
            "patient_status": patient_status,
            "patient_advice": patient_advice,
            "current_area_cm2": current_area,
            "expected_area_cm2": expected_area,
            "area_change_pct": area_change_pct,
            "is_abnormal_delay": is_abnormal_delay,
            "is_emergency": is_emergency,
            "infection_risk": infection_risk,
            "requires_appointment": requires_appointment,
            "appointment_urgency": appointment_urgency,
            "appointment_reason": appointment_reason,
            "doctor_report": doctor_report
        }
