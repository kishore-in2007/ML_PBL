from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app import doctor_services, models, storage
from app.config import settings
from app.ml.classify import classify_image
from app.ml.segment import segment_image
from app.triage import compute_triage


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


def compute_image_quality(image_bytes: bytes) -> float | None:
    try:
        import cv2
        import numpy as np
        from PIL import Image
        import io

        image = Image.open(io.BytesIO(image_bytes)).convert("L")
        gray = np.asarray(image)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        brightness = float(np.mean(gray))
        brightness_score = max(0.0, 1.0 - abs(brightness - 135.0) / 135.0)
        sharpness_score = min(sharpness / 500.0, 1.0)
        return round((brightness_score * 0.4 + sharpness_score * 0.6) * 100.0, 2)
    except Exception:
        return None


def _healing_from_change(percent_change: float | None, risk_class: str) -> tuple[float | None, str]:
    if percent_change is None:
        if risk_class == models.RiskClass.urgent.value:
            return 35.0, models.HealingTrend.needs_review.value
        if risk_class == models.RiskClass.mild_concern.value:
            return 65.0, models.HealingTrend.stable.value
        return 80.0, models.HealingTrend.stable.value

    if percent_change <= -10:
        return min(100.0, 80.0 + abs(percent_change)), models.HealingTrend.improving.value
    if percent_change <= 5:
        return 70.0, models.HealingTrend.stable.value
    if percent_change <= 15:
        return 50.0, models.HealingTrend.needs_review.value
    return 25.0, models.HealingTrend.worsening.value


def previous_segmentation_for_patient(
    db: Session,
    patient_id: str,
    log_date: date,
    exclude_image_id: str | None = None,
):
    yesterday_log = (
        db.query(models.DailyWoundLog)
        .filter(
            models.DailyWoundLog.patient_id == patient_id,
            models.DailyWoundLog.log_date == log_date - timedelta(days=1),
            models.DailyWoundLog.is_primary_daily_image == 1,
        )
        .order_by(models.DailyWoundLog.created_at.desc())
        .first()
    )
    if yesterday_log and yesterday_log.image and yesterday_log.image.segmentation:
        return yesterday_log.image.segmentation, "yesterday"

    query = (
        db.query(models.Segmentation)
        .join(models.WoundImage, models.Segmentation.image_id == models.WoundImage.id)
        .filter(models.WoundImage.patient_id == patient_id)
    )
    if exclude_image_id:
        query = query.filter(models.WoundImage.id != exclude_image_id)
    previous = query.order_by(models.Segmentation.created_at.desc()).first()
    return previous, "latest_previous" if previous else None


def create_daily_wound_evaluation(
    db: Session,
    patient: models.Patient,
    image_bytes: bytes,
    content_type: str,
    symptom_data: dict | None,
    notes: str | None,
    current_user_id: str,
    log_date: date | None = None,
) -> dict:
    log_date = log_date or date.today()
    # Lift the 1-photo-per-day restriction: allow unlimited uploads per day
    existing_primaries = (
        db.query(models.DailyWoundLog)
        .filter(
            models.DailyWoundLog.patient_id == patient.id,
            models.DailyWoundLog.log_date == log_date,
            models.DailyWoundLog.is_primary_daily_image == 1,
        )
        .all()
    )
    for ep in existing_primaries:
        ep.is_primary_daily_image = 0

    s3_key = storage.upload_image_bytes(image_bytes, patient.id, content_type)
    image = models.WoundImage(
        patient_id=patient.id,
        s3_key=s3_key,
        s3_bucket=settings.S3_BUCKET_NAME,
        capture_date=log_date,
        content_type=content_type,
        image_quality_score=compute_image_quality(image_bytes),
        ai_evaluated=1,
    )
    db.add(image)
    db.flush()

    classification_result = classify_image(image_bytes)
    classification = models.Classification(
        image_id=image.id,
        risk_class=classification_result["risk_class"],
        confidence=classification_result["confidence"],
        needs_human_review=1 if classification_result["needs_human_review"] else 0,
        raw_scores=classification_result["raw_scores"],
    )
    db.add(classification)

    previous, comparison_source = previous_segmentation_for_patient(db, patient.id, log_date, exclude_image_id=image.id)
    previous_area_cm2 = previous.wound_area_cm2 if previous else None
    segmentation_result = segment_image(
        image_bytes,
        reference_marker_cm=patient.reference_marker_cm or 2.0,
        previous_area_cm2=previous_area_cm2,
    )
    segmentation = models.Segmentation(
        image_id=image.id,
        wound_area_px=segmentation_result["wound_area_px"],
        wound_area_cm2=segmentation_result["wound_area_cm2"],
        percent_change_from_previous=segmentation_result["percent_change_from_previous"],
        model_used=segmentation_result.get("model_used"),
        model_confidence=segmentation_result.get("model_confidence"),
        prompt_box=segmentation_result.get("prompt_box_xyxy"),
    )
    db.add(segmentation)
    if segmentation_result.get("mask_overlay_png"):
        image.mask_overlay_key = storage.upload_analysis_bytes(
            segmentation_result["mask_overlay_png"],
            patient.id,
            prefix="mask-overlays",
            extension="png",
            content_type="image/png",
        )
    segmentation_summary = {
        key: value
        for key, value in segmentation_result.items()
        if key != "mask_overlay_png"
    }

    symptom_data = symptom_data or {}
    
    # Abnormal delay evaluation
    is_abnormal_delay = False
    delay_reason = "Progressing within normal parameters."
    if previous_area_cm2 is not None and previous_area_cm2 > 0:
        pct = segmentation_result.get("percent_change_from_previous")
        if pct is not None and pct > 12.0:
            is_abnormal_delay = True
            delay_reason = f"Wound area increased by {pct:.1f}% compared to previous record."
        elif pct is not None and pct > 0.0:
            # Slower than expected shrinkage
            is_abnormal_delay = True
            delay_reason = "Wound healing is delayed and taking longer than predicted."

    # Infection risk heuristics from redness/classification/symptoms
    infection_risk = 0.1
    if classification_result.get("risk_class") == models.RiskClass.urgent.value:
        infection_risk = 0.75
    elif classification_result.get("risk_class") == models.RiskClass.mild_concern.value:
        infection_risk = 0.40
    if symptom_data.get("fever") or (symptom_data.get("pain_level") or 0) >= 7:
        infection_risk = min(1.0, infection_risk + 0.25)

    triage_result = compute_triage(
        classification_result["risk_class"],
        classification_result["confidence"],
        classification_result["needs_human_review"],
        symptom_data,
        infection_risk=infection_risk,
        is_abnormal_delay=is_abnormal_delay,
    )
    triage_case = models.TriageCase(
        patient_id=patient.id,
        image_id=image.id,
        risk_class=triage_result["risk_class"],
        final_risk_score=triage_result["final_risk_score"],
        status=triage_result["status"],
        symptom_data=symptom_data,
    )
    db.add(triage_case)
    db.flush()

    healing_rate, healing_trend = _healing_from_change(
        segmentation_result["percent_change_from_previous"],
        classification_result["risk_class"],
    )

    daily_log = models.DailyWoundLog(
        patient_id=patient.id,
        image_id=image.id,
        log_date=log_date,
        pain_level=symptom_data.get("pain_level"),
        fever=1 if symptom_data.get("fever") else 0 if symptom_data.get("fever") is not None else None,
        medication_adherence=(
            1 if symptom_data.get("medication_adherence") else 0
            if symptom_data.get("medication_adherence") is not None
            else None
        ),
        notes=notes,
        risk_class=classification_result["risk_class"],
        confidence=classification_result["confidence"],
        wound_area_cm2=segmentation_result["wound_area_cm2"],
        percent_change_from_previous=segmentation_result["percent_change_from_previous"],
        healing_rate=healing_rate,
        healing_trend=healing_trend,
        triage_case_id=triage_case.id,
        doctor_review_status="pending" if triage_result["status"] != models.TriageStatus.auto_cleared.value else "not_required",
        is_primary_daily_image=1,
    )
    db.add(daily_log)
    db.flush()

    metric = models.HealingMetric(
        patient_id=patient.id,
        image_id=image.id,
        daily_log_id=daily_log.id,
        wound_area_cm2=segmentation_result["wound_area_cm2"],
        previous_wound_area_cm2=previous_area_cm2,
        comparison_source=comparison_source,
        percent_change_from_previous=segmentation_result["percent_change_from_previous"],
        healing_rate=healing_rate,
        healing_trend=healing_trend,
        model_summary={
            "classification": classification_result,
            "segmentation": segmentation_summary,
            "triage": triage_result,
            "infection_risk": round(infection_risk, 3),
            "is_abnormal_delay": is_abnormal_delay,
            "delay_reason": delay_reason,
            "image_quality_score": image.image_quality_score,
            "comparison_source": comparison_source,
        },
    )
    db.add(metric)

    patient.current_healing_rate = healing_rate
    patient.current_healing_trend = healing_trend
    patient.last_daily_upload_at = datetime.utcnow()

    is_emergency = (triage_result["status"] == models.TriageStatus.escalated.value or classification_result["risk_class"] == models.RiskClass.urgent.value or infection_risk >= 0.70)
    
    # Auto-schedule appointment and notify assigned doctors
    for doctor_id in doctor_services.assigned_doctor_ids(db, patient.id):
        priority = "urgent" if is_emergency else "normal"
        
        # If emergency or abnormal delay, automatically coordinate appointment
        if is_emergency or is_abnormal_delay:
            app_reason = (
                f"Emergency Clinical Alert: {classification_result['risk_class']} condition (Infection Risk: {infection_risk*100:.0f}%)"
                if is_emergency
                else f"Abnormal Recovery Delay: {delay_reason}"
            )
            doctor_services.auto_schedule_emergency_or_delayed_appointment(
                db,
                patient_id=patient.id,
                doctor_id=doctor_id,
                reason=app_reason,
                is_emergency=is_emergency,
            )

        doctor_services.create_doctor_notification(
            db,
            doctor_id=doctor_id,
            notification_type=models.NotificationType.new_wound_image.value,
            title="Daily wound photo evaluated & report generated",
            message=f"Risk: {classification_result['risk_class']}; Infection Risk: {infection_risk*100:.0f}%; Healing: {healing_trend}",
            patient_id=patient.id,
            triage_case_id=triage_case.id,
            priority=priority,
        )
    if triage_result["status"] in {
        models.TriageStatus.pending_review.value,
        models.TriageStatus.escalated.value,
    }:
        doctor_services.notify_assigned_doctors_for_triage(db, triage_case)

    db.commit()
    db.refresh(daily_log)
    db.refresh(image)

    return {
        "image": image,
        "classification": classification,
        "segmentation": segmentation,
        "triage_case": triage_case,
        "daily_log": daily_log,
        "metric": metric,
        "comparison_source": comparison_source,
    }


def daily_log_to_schema(log: models.DailyWoundLog):
    return {
        "id": log.id,
        "patient_id": log.patient_id,
        "image_id": log.image_id,
        "log_date": log.log_date,
        "pain_level": log.pain_level,
        "fever": bool(log.fever) if log.fever is not None else None,
        "medication_adherence": bool(log.medication_adherence) if log.medication_adherence is not None else None,
        "notes": log.notes,
        "risk_class": _enum_value(log.risk_class),
        "confidence": log.confidence,
        "wound_area_cm2": log.wound_area_cm2,
        "percent_change_from_previous": log.percent_change_from_previous,
        "healing_rate": log.healing_rate,
        "healing_trend": _enum_value(log.healing_trend),
        "triage_case_id": log.triage_case_id,
        "doctor_review_status": log.doctor_review_status,
        "reviewed_by_doctor_id": log.reviewed_by_doctor_id,
        "doctor_review_note": log.doctor_review_note,
        "doctor_reviewed_at": log.doctor_reviewed_at,
        "is_primary_daily_image": bool(log.is_primary_daily_image),
        "image_url": storage.get_presigned_url(log.image.s3_key) if log.image else None,
        "mask_overlay_url": storage.get_presigned_url(log.image.mask_overlay_key) if log.image and log.image.mask_overlay_key else None,
        "created_at": log.created_at,
    }
